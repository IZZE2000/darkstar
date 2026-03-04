"""Tests for analytical pipeline spike filtering (read-time hardening)."""

from datetime import datetime, timedelta

import pandas as pd
import pytest
import pytz

from backend.learning.models import Base


async def init_db_schema(store):
    """Initialize database schema for in-memory test database."""
    async with store.async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class TestAnalystSpikeFiltering:
    """Test suite for Analyst spike filtering in _fetch_observations."""

    @pytest.mark.asyncio
    async def test_fetch_observations_excludes_spike_rows(self):
        """Test that _fetch_observations excludes rows with spike values."""
        from backend.learning.analyst import Analyst

        # Config with 8kW grid limit (4.0 kWh max)
        config = {
            "system": {"grid": {"max_power_kw": 8.0}},
            "learning": {"sqlite_path": ":memory:"},
            "timezone": "Europe/Stockholm",
        }

        tz = pytz.timezone("Europe/Stockholm")
        analyst = Analyst(config)

        # Initialize database schema
        await init_db_schema(analyst.store)

        # Create observations with spike values
        now = datetime.now(tz)
        observations = [
            {
                "slot_start": now,
                "slot_end": now + timedelta(minutes=15),
                "pv_kwh": 2.0,  # Valid
                "load_kwh": 1.5,  # Valid
                "import_kwh": 0.5,
            },
            {
                "slot_start": now + timedelta(minutes=15),
                "slot_end": now + timedelta(minutes=30),
                "pv_kwh": 50.0,  # Spike - exceeds 4.0
                "load_kwh": 10.0,  # Spike - exceeds 4.0
                "import_kwh": 0.5,
            },
            {
                "slot_start": now + timedelta(minutes=30),
                "slot_end": now + timedelta(minutes=45),
                "pv_kwh": 3.0,  # Valid
                "load_kwh": 2.0,  # Valid
                "import_kwh": 0.5,
            },
        ]

        # Store observations
        obs_df = pd.DataFrame(observations)
        await analyst.store.store_slot_observations(obs_df)

        # Fetch observations
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=2)
        result_df = await analyst._fetch_observations(start, end)

        # Should only return 2 rows (excluding the spike row)
        assert len(result_df) == 2
        assert 2.0 in result_df["pv_kwh"].values
        assert 3.0 in result_df["pv_kwh"].values
        assert 50.0 not in result_df["pv_kwh"].values

    @pytest.mark.asyncio
    async def test_fetch_observations_graceful_without_config(self):
        """Test that _fetch_observations works gracefully without grid config."""
        from backend.learning.analyst import Analyst

        # Config without grid config
        config = {
            "learning": {"sqlite_path": ":memory:"},
            "timezone": "Europe/Stockholm",
        }

        tz = pytz.timezone("Europe/Stockholm")
        analyst = Analyst(config)

        # Initialize database schema
        await init_db_schema(analyst.store)

        # Create observations
        now = datetime.now(tz)
        observations = [
            {
                "slot_start": now,
                "slot_end": now + timedelta(minutes=15),
                "pv_kwh": 50.0,  # Would be spike if config present
                "load_kwh": 10.0,
            },
        ]

        obs_df = pd.DataFrame(observations)
        await analyst.store.store_slot_observations(obs_df)

        # Fetch observations (should work without config)
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=2)
        result_df = await analyst._fetch_observations(start, end)

        # Should return all rows when no config (no filtering)
        assert len(result_df) == 1
        assert result_df.iloc[0]["pv_kwh"] == 50.0


class TestLearningStoreSpikeFiltering:
    """Test suite for LearningStore spike filtering in read paths."""

    @pytest.mark.asyncio
    async def test_get_forecast_vs_actual_excludes_spikes(self):
        """Test that get_forecast_vs_actual excludes spike rows."""
        from backend.learning.store import LearningStore

        tz = pytz.timezone("Europe/Stockholm")
        store = LearningStore(":memory:", tz)
        await store.ensure_wal_mode()
        await init_db_schema(store)

        now = datetime.now(tz)

        # Store observations with spike
        observations = [
            {
                "slot_start": now,
                "slot_end": now + timedelta(minutes=15),
                "pv_kwh": 2.0,  # Valid
                "load_kwh": 1.0,
                "import_kwh": 0.5,
            },
            {
                "slot_start": now + timedelta(minutes=15),
                "slot_end": now + timedelta(minutes=30),
                "pv_kwh": 50.0,  # Spike
                "load_kwh": 10.0,
                "import_kwh": 0.5,
            },
        ]
        await store.store_slot_observations(pd.DataFrame(observations))

        # Store forecasts
        forecasts = [
            {
                "slot_start": now.isoformat(),
                "pv_forecast_kwh": 2.0,
                "load_forecast_kwh": 1.0,
                "forecast_version": "aurora",
            },
            {
                "slot_start": (now + timedelta(minutes=15)).isoformat(),
                "pv_forecast_kwh": 2.0,
                "load_forecast_kwh": 1.0,
                "forecast_version": "aurora",
            },
        ]
        await store.store_forecasts(forecasts, "aurora")

        # Get forecast vs actual with max_kwh=4.0
        df = await store.get_forecast_vs_actual(days_back=1, target="pv", max_kwh=4.0)

        # Should only return 1 row (excluding spike)
        assert len(df) == 1
        assert df.iloc[0]["actual"] == 2.0

    @pytest.mark.asyncio
    async def test_get_forecast_vs_actual_no_filtering_without_max_kwh(self):
        """Test that get_forecast_vs_actual includes all rows when max_kwh is None."""
        from backend.learning.store import LearningStore

        tz = pytz.timezone("Europe/Stockholm")
        store = LearningStore(":memory:", tz)
        await store.ensure_wal_mode()
        await init_db_schema(store)

        now = datetime.now(tz)

        # Store observations with spike
        observations = [
            {
                "slot_start": now,
                "slot_end": now + timedelta(minutes=15),
                "pv_kwh": 50.0,  # Spike
                "load_kwh": 10.0,
                "import_kwh": 0.5,
            },
        ]
        await store.store_slot_observations(pd.DataFrame(observations))

        # Store forecast
        forecasts = [
            {
                "slot_start": now.isoformat(),
                "pv_forecast_kwh": 2.0,
                "load_forecast_kwh": 1.0,
                "forecast_version": "aurora",
            },
        ]
        await store.store_forecasts(forecasts, "aurora")

        # Get forecast vs actual without max_kwh
        df = await store.get_forecast_vs_actual(days_back=1, target="pv", max_kwh=None)

        # Should return the spike row
        assert len(df) == 1
        assert df.iloc[0]["actual"] == 50.0

    @pytest.mark.asyncio
    async def test_calculate_metrics_excludes_spikes(self):
        """Test that calculate_metrics excludes spike rows from MAE calculation."""
        from backend.learning.store import LearningStore

        tz = pytz.timezone("Europe/Stockholm")
        store = LearningStore(":memory:", tz)
        await store.ensure_wal_mode()
        await init_db_schema(store)

        now = datetime.now(tz)

        # Store observations with spike
        observations = [
            {
                "slot_start": now,
                "slot_end": now + timedelta(minutes=15),
                "pv_kwh": 2.0,  # Valid
                "load_kwh": 1.0,
                "import_kwh": 0.5,
            },
            {
                "slot_start": now + timedelta(minutes=15),
                "slot_end": now + timedelta(minutes=30),
                "pv_kwh": 100.0,  # Huge spike
                "load_kwh": 50.0,  # Huge spike
                "import_kwh": 0.5,
            },
        ]
        await store.store_slot_observations(pd.DataFrame(observations))

        # Store forecasts
        forecasts = [
            {
                "slot_start": now.isoformat(),
                "pv_forecast_kwh": 2.0,
                "load_forecast_kwh": 1.0,
                "forecast_version": "aurora",
            },
            {
                "slot_start": (now + timedelta(minutes=15)).isoformat(),
                "pv_forecast_kwh": 2.0,
                "load_forecast_kwh": 1.0,
                "forecast_version": "aurora",
            },
        ]
        await store.store_forecasts(forecasts, "aurora")

        # Calculate metrics with max_kwh=4.0
        metrics = await store.calculate_metrics(days_back=1, max_kwh=4.0)

        # MAE should only consider valid rows
        # With spike filtering, the spike row (pv_kwh=100, load_kwh=50) should be excluded
        # leaving only the valid row (pv_kwh=2, load_kwh=1)
        # The exact MAE depends on forecast values, but spikes should be excluded
        assert (
            "mae_pv" not in metrics or metrics.get("mae_pv") is None or metrics.get("mae_pv") <= 2.0
        )
        assert (
            "mae_load" not in metrics
            or metrics.get("mae_load") is None
            or metrics.get("mae_load") <= 2.0
        )

    @pytest.mark.asyncio
    async def test_calculate_metrics_includes_spikes_without_max_kwh(self):
        """Test that calculate_metrics includes spike rows when max_kwh is None."""
        from backend.learning.store import LearningStore

        tz = pytz.timezone("Europe/Stockholm")
        store = LearningStore(":memory:", tz)
        await store.ensure_wal_mode()
        await init_db_schema(store)

        now = datetime.now(tz)

        # Store observations with spike
        observations = [
            {
                "slot_start": now,
                "slot_end": now + timedelta(minutes=15),
                "pv_kwh": 100.0,  # Huge spike
                "load_kwh": 50.0,
                "import_kwh": 0.5,
            },
        ]
        await store.store_slot_observations(pd.DataFrame(observations))

        # Store forecast
        forecasts = [
            {
                "slot_start": now.isoformat(),
                "pv_forecast_kwh": 2.0,
                "load_forecast_kwh": 1.0,
                "forecast_version": "aurora",
            },
        ]
        await store.store_forecasts(forecasts, "aurora")

        # Calculate metrics without max_kwh
        metrics = await store.calculate_metrics(days_back=1, max_kwh=None)

        # MAE should include spike (100.0 - 2.0 = 98.0 error for PV, 50.0 - 1.0 = 49.0 for load)
        # Note: metrics may vary depending on data matching
        assert metrics.get("mae_pv") is not None
        assert metrics.get("mae_pv") >= 98.0  # At least the spike contribution
        assert metrics.get("mae_load") is not None
        assert metrics.get("mae_load") >= 49.0  # At least the spike contribution
