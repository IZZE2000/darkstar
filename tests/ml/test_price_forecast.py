"""Tests for price forecast inference with weather-only row support."""

from unittest.mock import patch

import pandas as pd
import pytest

from ml.price_forecast import (
    generate_price_forecasts,
    get_d1_price_forecast_fallback,
)


@pytest.fixture
def price_config():
    """Test fixture for price forecast config."""
    return {
        "timezone": "Europe/Stockholm",
        "nordpool": {"price_area": "SE4"},
        "price_forecast": {"model_name": "price_model.lgb"},
    }


@pytest.fixture
def db_path():
    """Test fixture for database path."""
    return "data/test_planner_learning.db"


@pytest.mark.asyncio
@patch("ml.price_forecast.get_regional_weather")
@patch("ml.price_forecast.compute_regional_wind_index")
@patch("ml.price_forecast.build_price_features_batch")
@patch("ml.price_forecast._persist_forecasts")
async def test_generate_forecasts_without_model(
    mock_persist, mock_build_features, mock_wind_index, mock_weather, price_config, db_path
):
    """Test that forecast generation works without model files."""
    print("\n--- Testing Forecast Generation Without Model ---")

    # Mock model path to not exist (simulating fresh install)
    with patch("pathlib.Path.exists", return_value=False):
        # Mock weather data
        mock_weather.return_value = {
            "coord1": pd.DataFrame(
                {
                    "temp_c": [5.0] * 96,
                    "cloud_cover_pct": [50.0] * 96,
                    "shortwave_radiation_w_m2": [100.0] * 96,
                }
            )
        }

        # Mock wind index
        mock_wind_index.return_value = pd.Series([1.0] * 96)

        # Mock feature dataframe with all required columns
        index = pd.date_range("2026-03-31", periods=96, freq="15min")
        mock_build_features.return_value = pd.DataFrame(
            {
                "hour": [0] * 96,
                "day_of_week": [0] * 96,
                "month": [3] * 96,
                "is_weekend": [False] * 96,
                "is_holiday": [False] * 96,
                "days_ahead": [1] * 96,
                "price_lag_1d": [0.5] * 96,
                "price_lag_7d": [0.5] * 96,
                "price_lag_24h_avg": [0.5] * 96,
                "wind_index": [1.0] * 96,
                "temperature_c": [5.0] * 96,
                "cloud_cover": [50.0] * 96,
                "radiation_wm2": [100.0] * 96,
            },
            index=index,
        )

        # Run the function
        forecasts = await generate_price_forecasts(
            config=price_config,
            db_path=db_path,
        )

        # Verify results
        assert isinstance(forecasts, list)
        assert len(forecasts) > 0, "Should return forecast records"

        # Verify all forecasts have null spot values
        for forecast in forecasts:
            assert forecast["spot_p10"] is None
            assert forecast["spot_p50"] is None
            assert forecast["spot_p90"] is None

            # Verify weather features are populated
            assert forecast["wind_index"] is not None
            assert forecast["temperature_c"] is not None
            assert forecast["cloud_cover"] is not None
            assert forecast["radiation_wm2"] is not None

        print(f"✓ Generated {len(forecasts)} weather-only forecasts")
        print("✓ All spot columns are None")
        print("✓ Weather feature columns are populated")

        # Verify persistence was called
        mock_persist.assert_called_once()


@pytest.mark.asyncio
@patch("ml.price_forecast.get_price_forecasts_from_db")
async def test_d1_fallback_filters_null_predictions(mock_get_forecasts, price_config, db_path):
    """Test that D+1 fallback filters out null-prediction rows."""
    print("\n--- Testing D+1 Fallback Null Filtering ---")

    # Mock DB returning only weather-only rows (null predictions)
    mock_get_forecasts.return_value = [
        {
            "slot_start": "2026-03-31T00:00:00",
            "days_ahead": 1,
            "spot_p10": None,
            "spot_p50": None,
            "spot_p90": None,
            "wind_index": 1.0,
            "temperature_c": 5.0,
        }
    ] * 96  # 24 hours of 15-minute slots

    result = await get_d1_price_forecast_fallback(
        config=price_config,
        db_path=db_path,
    )

    # Should return None when only weather-only rows exist
    assert result is None
    print("✓ Returns None when only null-prediction rows exist")

    # Now test with mixed rows (some with predictions)
    mixed_forecasts = [
        {
            "slot_start": "2026-03-31T00:00:00",
            "days_ahead": 1,
            "spot_p10": None,
            "spot_p50": None,
            "spot_p90": None,
            "wind_index": 1.0,
        },
        {
            "slot_start": "2026-03-31T00:15:00",
            "days_ahead": 1,
            "spot_p10": 0.4,
            "spot_p50": 0.5,
            "spot_p90": 0.6,
            "wind_index": 1.0,
        },
    ]
    mock_get_forecasts.return_value = mixed_forecasts

    result = await get_d1_price_forecast_fallback(
        config=price_config,
        db_path=db_path,
    )

    # Should return only the valid forecast
    assert result is not None
    assert len(result) == 1
    assert result[0]["spot_p50"] == 0.5
    print("✓ Filters out null rows and returns only valid forecasts")
