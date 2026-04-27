"""Tests for price forecast inference with weather-only row support."""

from unittest.mock import patch

import pandas as pd
import pytest
import sqlalchemy
from sqlalchemy import create_engine, select

from backend.learning.models import Base, PriceForecast
from ml.price_forecast import (
    generate_price_forecasts,
    get_d1_price_forecast_fallback,
    get_price_forecasts_from_db,
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


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temp SQLite DB with price_forecasts table."""
    db_path = str(tmp_path / "test.db")
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    yield db_path, engine
    engine.dispose()


def _insert_forecasts(engine, rows: list[dict]):
    """Insert price forecast rows into the DB."""
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    for row in rows:
        session.add(PriceForecast(**row))
    session.commit()
    session.close()


@pytest.mark.asyncio
async def test_dedup_two_runs_returns_unique_slots(tmp_db):
    """Insert 2 forecast runs for same 48 slots, assert exactly 48 unique rows returned."""
    db_path, engine = tmp_db

    slots = [f"2026-04-10T{h:02d}:{m:02d}:00+02:00" for h in range(24) for m in (0, 30)]
    assert len(slots) == 48

    run1 = [
        {
            "slot_start": s,
            "issue_timestamp": "2026-04-09T06:00:00+02:00",
            "days_ahead": 1,
            "spot_p10": 0.4,
            "spot_p50": 0.5,
            "spot_p90": 0.6,
        }
        for s in slots
    ]
    run2 = [
        {
            "slot_start": s,
            "issue_timestamp": "2026-04-09T14:00:00+02:00",
            "days_ahead": 1,
            "spot_p10": 0.45,
            "spot_p50": 0.55,
            "spot_p90": 0.65,
        }
        for s in slots
    ]

    _insert_forecasts(engine, run1 + run2)

    results = await get_price_forecasts_from_db(db_path=db_path, days_ahead=1, limit=96)
    assert len(results) == 48, f"Expected 48, got {len(results)}"

    slot_starts = [r["slot_start"] for r in results]
    assert len(set(slot_starts)) == 48, "Duplicate slot_starts found in results"

    for r in results:
        assert r["issue_timestamp"] == "2026-04-09T14:00:00+02:00"
        assert r["spot_p50"] == 0.55


@pytest.mark.asyncio
async def test_dedup_excludes_weather_only_rows(tmp_db):
    """Insert weather-only rows (null spot_p50) alongside valid forecasts, assert only valid rows returned."""
    db_path, engine = tmp_db

    slots = [f"2026-04-10T{h:02d}:{m:02d}:00+02:00" for h in range(24) for m in (0, 30)]

    valid_rows = [
        {
            "slot_start": s,
            "issue_timestamp": "2026-04-09T14:00:00+02:00",
            "days_ahead": 1,
            "spot_p10": 0.4,
            "spot_p50": 0.5,
            "spot_p90": 0.6,
        }
        for s in slots
    ]
    weather_only_rows = [
        {
            "slot_start": s,
            "issue_timestamp": "2026-04-09T12:00:00+02:00",
            "days_ahead": 1,
            "spot_p10": None,
            "spot_p50": None,
            "spot_p90": None,
            "wind_index": 1.0,
        }
        for s in slots[:24]
    ]

    _insert_forecasts(engine, valid_rows + weather_only_rows)

    results = await get_price_forecasts_from_db(db_path=db_path, days_ahead=1, limit=1000)
    assert len(results) == 48, f"Expected 48, got {len(results)}"

    for r in results:
        assert r["spot_p50"] is not None, f"Null spot_p50 for slot {r['slot_start']}"
        assert r["issue_timestamp"] == "2026-04-09T14:00:00+02:00"


@pytest.mark.asyncio
async def test_dedup_tied_issue_timestamps(tmp_db):
    """Insert duplicate rows with same slot_start, days_ahead, and issue_timestamp — assert exactly one row per slot."""
    db_path, engine = tmp_db

    slots = [f"2026-04-10T{h:02d}:{m:02d}:00+02:00" for h in range(24) for m in (0, 30)]

    rows = []
    for s in slots:
        rows.append(
            {
                "slot_start": s,
                "issue_timestamp": "2026-04-09T14:00:00+02:00",
                "days_ahead": 1,
                "spot_p10": 0.4,
                "spot_p50": 0.5,
                "spot_p90": 0.6,
            }
        )
        rows.append(
            {
                "slot_start": s,
                "issue_timestamp": "2026-04-09T14:00:00+02:00",
                "days_ahead": 1,
                "spot_p10": 0.45,
                "spot_p50": 0.55,
                "spot_p90": 0.65,
            }
        )

    _insert_forecasts(engine, rows)

    results = await get_price_forecasts_from_db(db_path=db_path, days_ahead=1, limit=96)
    assert len(results) == 48, f"Expected 48, got {len(results)}"

    slot_starts = [r["slot_start"] for r in results]
    assert len(set(slot_starts)) == 48, "Duplicate slot_starts found in results"


@pytest.mark.asyncio
async def test_d1_fallback_dedup(tmp_db, price_config):
    """Seed DB with duplicate slot_start entries — assert no duplicate slot_start in fallback return."""
    db_path, engine = tmp_db

    slots = [f"2026-04-10T{h:02d}:{m:02d}:00+02:00" for h in range(24) for m in (0, 30)]

    rows = []
    for s in slots:
        rows.append(
            {
                "slot_start": s,
                "issue_timestamp": "2026-04-09T14:00:00+02:00",
                "days_ahead": 1,
                "spot_p10": 0.4,
                "spot_p50": 0.5,
                "spot_p90": 0.6,
            }
        )
        rows.append(
            {
                "slot_start": s,
                "issue_timestamp": "2026-04-09T14:00:00+02:00",
                "days_ahead": 1,
                "spot_p10": 0.45,
                "spot_p50": 0.55,
                "spot_p90": 0.65,
            }
        )

    _insert_forecasts(engine, rows)

    result = await get_d1_price_forecast_fallback(config=price_config, db_path=db_path)
    assert result is not None
    assert len(result) == 48, f"Expected 48, got {len(result)}"

    slot_starts = [r["slot_start"] for r in result]
    assert len(set(slot_starts)) == 48, "Duplicate slot_starts found in fallback result"
