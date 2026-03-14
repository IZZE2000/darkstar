"""Tests for recency-weighted training functionality."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytz

from ml.train import (
    TrainingConfig,
    _compute_sample_weights,
    _load_slot_observations,
    _train_regressor,
)


class TestComputeSampleWeights:
    """Test suite for _compute_sample_weights function."""

    def test_exponential_decay_1_day(self):
        """Test that 1-day old sample has weight ≈ 1.0."""
        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)

        # Create DataFrame with 1-day old sample
        df = pd.DataFrame(
            {
                "slot_start": [now - timedelta(days=1)],
                "value": [1.0],
            }
        )
        # slot_start is already timezone-aware from datetime.now(tz)

        weights = _compute_sample_weights(df, half_life_days=30.0)

        assert len(weights) == 1
        assert 0.95 <= weights[0] <= 1.0, f"Expected weight ≈ 1.0 for 1-day old, got {weights[0]}"

    def test_exponential_decay_30_day(self):
        """Test that 30-day old sample has weight ≈ 0.5."""
        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)

        # Create DataFrame with 30-day old sample
        df = pd.DataFrame(
            {
                "slot_start": [now - timedelta(days=30)],
                "value": [1.0],
            }
        )
        # slot_start is already timezone-aware from datetime.now(tz)

        weights = _compute_sample_weights(df, half_life_days=30.0)

        assert len(weights) == 1
        assert 0.48 <= weights[0] <= 0.52, f"Expected weight ≈ 0.5 for 30-day old, got {weights[0]}"

    def test_exponential_decay_180_day(self):
        """Test that 180-day old sample has weight ≈ 0.05."""
        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)

        # Create DataFrame with 180-day old sample
        df = pd.DataFrame(
            {
                "slot_start": [now - timedelta(days=180)],
                "value": [1.0],
            }
        )
        # slot_start is already timezone-aware from datetime.now(tz)

        weights = _compute_sample_weights(df, half_life_days=30.0)

        assert len(weights) == 1
        # 180 days = 6 half-lives, weight = 0.5^6 = 0.015625
        assert 0.01 <= weights[0] <= 0.02, (
            f"Expected weight ≈ 0.016 for 180-day old (6 half-lives), got {weights[0]}"
        )

    def test_multiple_samples_decay_correctly(self):
        """Test that multiple samples have correctly decaying weights."""
        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)

        # Create DataFrame with samples at different ages
        df = pd.DataFrame(
            {
                "slot_start": [
                    now - timedelta(days=1),  # Recent
                    now - timedelta(days=30),  # Half-life
                    now - timedelta(days=60),  # Quarter weight
                ],
                "value": [1.0, 1.0, 1.0],
            }
        )
        # slot_start is already timezone-aware from datetime.now(tz)

        weights = _compute_sample_weights(df, half_life_days=30.0)

        assert len(weights) == 3
        # Recent > Half-life > Old
        assert weights[0] > weights[1] > weights[2]
        assert 0.95 <= weights[0] <= 1.0  # 1 day
        assert 0.48 <= weights[1] <= 0.52  # 30 days
        assert 0.23 <= weights[2] <= 0.27  # 60 days (should be ~0.25)

    def test_empty_dataframe(self):
        """Test that empty DataFrame returns empty weights."""
        df = pd.DataFrame({"slot_start": pd.Series([], dtype="datetime64[ns]")})
        weights = _compute_sample_weights(df, half_life_days=30.0)

        assert len(weights) == 0
        assert isinstance(weights, np.ndarray)

    def test_missing_slot_start_column(self):
        """Test that missing slot_start column returns ones."""
        df = pd.DataFrame({"value": [1.0, 2.0, 3.0]})
        weights = _compute_sample_weights(df, half_life_days=30.0)

        assert len(weights) == 3
        np.testing.assert_array_almost_equal(weights, np.ones(3))

    def test_config_override(self):
        """Test that config can override half_life_days."""
        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)

        df = pd.DataFrame(
            {
                "slot_start": [now - timedelta(days=30)],
                "value": [1.0],
            }
        )
        # slot_start is already timezone-aware from datetime.now(tz)

        # With default 30-day half-life, weight should be ~0.5
        config = TrainingConfig(recency_half_life_days=60.0)
        weights = _compute_sample_weights(df, half_life_days=30.0, config=config)

        # With 60-day half-life, 30-day old should be ~0.707 (not 0.5)
        assert weights[0] > 0.6, f"Expected weight > 0.6 with 60-day half-life, got {weights[0]}"


class TestTrainRegressorWithSampleWeights:
    """Test suite for _train_regressor with sample weights."""

    @patch("ml.train.lgb.LGBMRegressor")
    def test_sample_weights_passed_to_fit(self, mock_lgb_class):
        """Test that sample weights are passed to LightGBM fit()."""
        # Setup mock
        mock_model = MagicMock()
        mock_lgb_class.return_value = mock_model

        # Create sample data
        features = pd.DataFrame(
            {
                "feature1": [1.0, 2.0, 3.0, 4.0, 5.0],
                "feature2": [0.1, 0.2, 0.3, 0.4, 0.5],
            }
        )
        target = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        sample_weight = np.array([1.0, 0.8, 0.6, 0.4, 0.2])

        # Call with sample weights
        _train_regressor(features, target, min_samples=3, sample_weight=sample_weight)

        # Verify fit was called with sample_weight
        mock_model.fit.assert_called_once()
        call_kwargs = mock_model.fit.call_args[1]
        assert "sample_weight" in call_kwargs
        np.testing.assert_array_almost_equal(call_kwargs["sample_weight"], sample_weight)

    @patch("ml.train.lgb.LGBMRegressor")
    def test_no_sample_weights_when_none_provided(self, mock_lgb_class):
        """Test that sample weights are not passed when None."""
        # Setup mock
        mock_model = MagicMock()
        mock_lgb_class.return_value = mock_model

        # Create sample data
        features = pd.DataFrame(
            {
                "feature1": [1.0, 2.0, 3.0, 4.0, 5.0],
                "feature2": [0.1, 0.2, 0.3, 0.4, 0.5],
            }
        )
        target = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])

        # Call without sample weights
        _train_regressor(features, target, min_samples=3, sample_weight=None)

        # Verify fit was called without sample_weight
        mock_model.fit.assert_called_once()
        call_kwargs = mock_model.fit.call_args[1]
        assert "sample_weight" not in call_kwargs

    @patch("ml.train.lgb.LGBMRegressor")
    def test_insufficient_samples_returns_none(self, mock_lgb_class):
        """Test that training is skipped when insufficient samples."""
        features = pd.DataFrame(
            {
                "feature1": [1.0, 2.0],
            }
        )
        target = pd.Series([1.0, 2.0])
        sample_weight = np.array([1.0, 0.5])

        result = _train_regressor(features, target, min_samples=10, sample_weight=sample_weight)

        assert result is None
        mock_lgb_class.assert_not_called()


class TestLoadSlotObservationsNoCap:
    """Test suite for _load_slot_observations without days_back cap."""

    @patch("ml.train.sqlite3.connect")
    @patch("ml.train.pd.read_sql_query")
    @patch("ml.train.get_learning_engine")
    @patch("ml.train.get_max_energy_per_slot")
    def test_loads_all_available_data(
        self, mock_max_kwh, mock_get_engine, mock_read_sql, mock_connect
    ):
        """Test that _load_slot_observations loads all available data without days_back cap."""
        # Setup mock
        mock_engine = MagicMock()
        mock_engine.db_path = ":memory:"
        mock_engine.timezone = pytz.timezone("Europe/Stockholm")
        mock_get_engine.return_value = mock_engine
        mock_max_kwh.return_value = 4.0

        # Create mock data spanning 200 days (more than old 90-day cap)
        tz = pytz.timezone("Europe/Stockholm")
        now = datetime.now(tz)
        dates = [now - timedelta(days=i) for i in range(200, 0, -1)]

        mock_df = pd.DataFrame(
            {
                "slot_start": dates,
                "load_kwh": [1.0] * 200,
                "pv_kwh": [0.5] * 200,
            }
        )
        # dates are already timezone-aware from datetime.now(tz)
        mock_read_sql.return_value = mock_df

        # Load data without start_time (should load all)
        result = _load_slot_observations(mock_engine)

        # Verify all 200 rows were loaded
        assert len(result) == 200
        # Verify query does not have days_back limit
        call_args = mock_read_sql.call_args
        query = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]["sql"]
        assert "days_back" not in query.lower()
        assert "limit" not in query.lower()

    @patch("ml.train.sqlite3.connect")
    @patch("ml.train.pd.read_sql_query")
    @patch("ml.train.get_learning_engine")
    @patch("ml.train.get_max_energy_per_slot")
    def test_respects_time_range_params(
        self, mock_max_kwh, mock_get_engine, mock_read_sql, mock_connect
    ):
        """Test that _load_slot_observations respects explicit time range params."""
        mock_engine = MagicMock()
        mock_engine.db_path = ":memory:"
        mock_engine.timezone = pytz.timezone("Europe/Stockholm")
        mock_get_engine.return_value = mock_engine
        mock_max_kwh.return_value = 4.0

        tz = pytz.timezone("Europe/Stockholm")
        start_time = datetime.now(tz) - timedelta(days=30)
        end_time = datetime.now(tz)

        mock_df = pd.DataFrame(
            {
                "slot_start": [start_time + timedelta(days=i) for i in range(30)],
                "load_kwh": [1.0] * 30,
                "pv_kwh": [0.5] * 30,
            }
        )
        mock_read_sql.return_value = mock_df

        _load_slot_observations(mock_engine, start_time=start_time, end_time=end_time)

        # Verify the query was called with time range parameters
        call_args = mock_read_sql.call_args
        params = call_args[0][2] if len(call_args[0]) > 2 else call_args[1]["params"]
        assert start_time.isoformat() in params or any(
            start_time.isoformat() in str(p) for p in params
        )
        assert end_time.isoformat() in params or any(end_time.isoformat() in str(p) for p in params)
