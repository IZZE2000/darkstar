"""Tests for recorder delta-based energy calculation and state persistence."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytz

from backend.recorder import RecorderStateStore, record_observation_from_current_state


class TestRecorderStateStore:
    """Test suite for RecorderStateStore class."""

    def test_load_nonexistent_file(self):
        """Test loading from non-existent file returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "nonexistent.json"
            store = RecorderStateStore(state_file)
            result = store.load()
            assert result == {}

    def test_load_corrupted_file(self):
        """Test loading corrupted file returns empty dict and removes file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "corrupted.json"
            state_file.write_text("invalid json")
            store = RecorderStateStore(state_file)
            result = store.load()
            assert result == {}
            assert not state_file.exists()

    def test_save_and_load(self):
        """Test saving and loading state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            store = RecorderStateStore(state_file)
            store._state = {"test_key": {"value": 100.0, "timestamp": "2024-01-01T00:00:00"}}
            store.save()

            # Load in new instance
            store2 = RecorderStateStore(state_file)
            result = store2.load()
            assert result["test_key"]["value"] == 100.0

    def test_get_delta_first_reading(self):
        """Test get_delta returns None on first reading (no previous state)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            store = RecorderStateStore(state_file)
            store.load()

            now = datetime(2024, 1, 1, 12, 0, 0)
            delta, is_valid = store.get_delta("pv_total", 100.0, now)

            assert delta is None
            assert is_valid is True
            # State should be updated
            assert store._state["pv_total"]["value"] == 100.0

    def test_get_delta_normal_calculation(self):
        """Spec: Persistent Recorder State - Scenario: Recorder resumes after a restart"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            store = RecorderStateStore(state_file)
            store.load()

            # First reading
            now = datetime(2024, 1, 1, 12, 0, 0)
            store.get_delta("pv_total", 100.0, now)

            # Second reading
            later = datetime(2024, 1, 1, 12, 15, 0)
            delta, is_valid = store.get_delta("pv_total", 150.0, later)

            assert delta == 50.0
            assert is_valid is True

    def test_get_delta_meter_reset_detection(self):
        """Test get_delta detects meter reset (negative delta)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            store = RecorderStateStore(state_file)
            store.load()

            # First reading
            now = datetime(2024, 1, 1, 12, 0, 0)
            store.get_delta("pv_total", 1000.0, now)

            # Meter reset (reading goes down)
            later = datetime(2024, 1, 1, 12, 15, 0)
            delta, is_valid = store.get_delta("pv_total", 50.0, later)

            assert delta is None
            assert is_valid is False
            # State should be updated with new reading
            assert store._state["pv_total"]["value"] == 50.0

    def test_get_last_timestamp(self):
        """Test get_last_timestamp returns correct datetime."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            store = RecorderStateStore(state_file)
            store.load()

            now = datetime(2024, 1, 1, 12, 0, 0)
            store.get_delta("pv_total", 100.0, now)

            last_ts = store.get_last_timestamp("pv_total")
            assert last_ts == now

    def test_get_last_timestamp_missing_key(self):
        """Test get_last_timestamp returns None for missing key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            store = RecorderStateStore(state_file)
            store.load()

            result = store.get_last_timestamp("nonexistent")
            assert result is None


class TestRecorderDeltaLogic:
    """Test suite for recorder delta-based calculation logic."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        return {
            "timezone": "Europe/Stockholm",
            "learning": {"sqlite_path": ":memory:"},
            "input_sensors": {
                "pv_power": "sensor.pv_power",
                "load_power": "sensor.load_power",
                "grid_power": "sensor.grid_power",
                "battery_power": "sensor.battery_power",
                "water_power": "sensor.water_power",
                "battery_soc": "sensor.battery_soc",
                # Cumulative sensors
                "total_pv_production": "sensor.total_pv_production",
                "total_load_consumption": "sensor.total_load_consumption",
            },
            "system": {"grid_meter_type": "net", "has_battery": True},
            "water_heaters": [],
            "ev_chargers": [],
        }

    @pytest.mark.asyncio
    async def test_uses_cumulative_sensors_when_available(self, mock_config):
        """Spec: Delta-based Energy Calculation - Scenario: Recorder calculates energy during a continuous run"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "recorder_state.json"

            # Initialize state store with previous reading
            state_store = RecorderStateStore(state_file)
            state_store.load()
            now = datetime.now(pytz.timezone("Europe/Stockholm"))
            prev_time = now - timedelta(minutes=15)
            state_store._state = {
                "pv_total": {"value": 100.0, "timestamp": prev_time.isoformat()},
                "load_total": {"value": 50.0, "timestamp": prev_time.isoformat()},
            }
            state_store.save()

            # Mock HA sensor responses
            async def mock_get_ha_sensor_kw_normalized(entity):
                power_values = {
                    "sensor.pv_power": 5.0,  # 5 kW
                    "sensor.load_power": 3.0,  # 3 kW
                    "sensor.grid_power": 1.0,
                    "sensor.battery_power": 0.5,
                    "sensor.water_power": 0.0,
                }
                return power_values.get(entity, 0.0)

            async def mock_get_ha_sensor_float(entity):
                # Cumulative sensors - values increased by expected delta
                cumulative_values = {
                    "sensor.total_pv_production": 101.25,  # +1.25 kWh (5kW * 0.25h)
                    "sensor.total_load_consumption": 50.75,  # +0.75 kWh (3kW * 0.25h)
                    "sensor.battery_soc": 50.0,
                }
                return cumulative_values.get(entity)

            with (
                patch(
                    "backend.recorder.get_ha_sensor_kw_normalized",
                    side_effect=mock_get_ha_sensor_kw_normalized,
                ),
                patch("backend.recorder.get_ha_sensor_float", side_effect=mock_get_ha_sensor_float),
                patch("backend.recorder.get_current_slot_prices", return_value=None),
            ):
                # Create mock LearningStore
                mock_store = MagicMock()
                mock_store.get_system_state = AsyncMock(return_value=None)
                mock_store.set_system_state = AsyncMock()
                mock_store.store_slot_observations = AsyncMock()
                mock_store.close = AsyncMock()

                with patch("backend.recorder.LearningStore", return_value=mock_store):
                    await record_observation_from_current_state(
                        config=mock_config, state_store=state_store
                    )

                    # Verify observations were stored
                    assert mock_store.store_slot_observations.called
                    df = mock_store.store_slot_observations.call_args[0][0]
                    record = df.iloc[0].to_dict()

                    # Should use cumulative delta, not power snapshot
                    assert record["pv_kwh"] == pytest.approx(1.25, abs=0.01)
                    assert record["load_kwh"] == pytest.approx(0.75, abs=0.01)

    @pytest.mark.asyncio
    async def test_fallback_to_power_snapshot(self, mock_config):
        """Spec: Snapshot Fallback - Scenario: Missing total energy sensor"""
        # Remove cumulative sensors from config
        mock_config["input_sensors"].pop("total_pv_production", None)
        mock_config["input_sensors"].pop("total_load_consumption", None)

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "recorder_state.json"
            state_store = RecorderStateStore(state_file)
            state_store.load()

            async def mock_get_ha_sensor_kw_normalized(entity):
                power_values = {
                    "sensor.pv_power": 4.0,  # 4 kW
                    "sensor.load_power": 2.0,  # 2 kW
                    "sensor.grid_power": 1.0,
                    "sensor.battery_power": 0.5,
                    "sensor.water_power": 0.0,
                }
                return power_values.get(entity, 0.0)

            async def mock_get_ha_sensor_float(entity):
                if entity == "sensor.battery_soc":
                    return 50.0
                return None  # No cumulative sensors available

            with (
                patch(
                    "backend.recorder.get_ha_sensor_kw_normalized",
                    side_effect=mock_get_ha_sensor_kw_normalized,
                ),
                patch("backend.recorder.get_ha_sensor_float", side_effect=mock_get_ha_sensor_float),
                patch("backend.recorder.get_current_slot_prices", return_value=None),
            ):
                mock_store = MagicMock()
                mock_store.get_system_state = AsyncMock(return_value=None)
                mock_store.set_system_state = AsyncMock()
                mock_store.store_slot_observations = AsyncMock()
                mock_store.close = AsyncMock()

                with patch("backend.recorder.LearningStore", return_value=mock_store):
                    await record_observation_from_current_state(
                        config=mock_config, state_store=state_store
                    )

                    assert mock_store.store_slot_observations.called
                    df = mock_store.store_slot_observations.call_args[0][0]
                    record = df.iloc[0].to_dict()

                    # Should use power snapshot (4kW * 0.25h = 1.0 kWh)
                    assert record["pv_kwh"] == pytest.approx(1.0, abs=0.01)
                    assert record["load_kwh"] == pytest.approx(0.5, abs=0.01)

    @pytest.mark.asyncio
    async def test_meter_reset_fallback(self, mock_config):
        """Design Risk: Meter Reset/Rollover - Mitigation: Fallback to power snapshot when delta is negative"""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "recorder_state.json"

            # Initialize state with high value
            state_store = RecorderStateStore(state_file)
            state_store.load()
            now = datetime.now(pytz.timezone("Europe/Stockholm"))
            prev_time = now - timedelta(minutes=15)
            state_store._state = {
                "pv_total": {"value": 10000.0, "timestamp": prev_time.isoformat()},
            }
            state_store.save()

            async def mock_get_ha_sensor_kw_normalized(entity):
                power_values = {
                    "sensor.pv_power": 5.0,
                    "sensor.load_power": 3.0,
                    "sensor.grid_power": 1.0,
                    "sensor.battery_power": 0.5,
                    "sensor.water_power": 0.0,
                }
                return power_values.get(entity, 0.0)

            async def mock_get_ha_sensor_float(entity):
                # Meter reset - value dropped significantly
                cumulative_values = {
                    "sensor.total_pv_production": 10.0,  # Reset from 10000 to 10
                    "sensor.total_load_consumption": 50.0,
                    "sensor.battery_soc": 50.0,
                }
                return cumulative_values.get(entity)

            with (
                patch(
                    "backend.recorder.get_ha_sensor_kw_normalized",
                    side_effect=mock_get_ha_sensor_kw_normalized,
                ),
                patch("backend.recorder.get_ha_sensor_float", side_effect=mock_get_ha_sensor_float),
                patch("backend.recorder.get_current_slot_prices", return_value=None),
            ):
                mock_store = MagicMock()
                mock_store.get_system_state = AsyncMock(return_value=None)
                mock_store.set_system_state = AsyncMock()
                mock_store.store_slot_observations = AsyncMock()
                mock_store.close = AsyncMock()

                with patch("backend.recorder.LearningStore", return_value=mock_store):
                    await record_observation_from_current_state(
                        config=mock_config, state_store=state_store
                    )

                    df = mock_store.store_slot_observations.call_args[0][0]
                    record = df.iloc[0].to_dict()

                    # Should fallback to power snapshot on meter reset
                    assert record["pv_kwh"] == pytest.approx(1.25, abs=0.01)  # 5kW * 0.25h

    @pytest.mark.asyncio
    async def test_dual_meter_cumulative(self):
        """Spec: Support for Cumulative Energy Sensors - Dual meter type support"""
        config = {
            "timezone": "Europe/Stockholm",
            "learning": {"sqlite_path": ":memory:"},
            "input_sensors": {
                "pv_power": "sensor.pv_power",
                "load_power": "sensor.load_power",
                "grid_import_power": "sensor.grid_import_power",
                "grid_export_power": "sensor.grid_export_power",
                "battery_power": "sensor.battery_power",
                "water_power": "sensor.water_power",
                "battery_soc": "sensor.battery_soc",
                "total_grid_import": "sensor.grid_import_total",
                "total_grid_export": "sensor.grid_export_total",
            },
            "system": {"grid_meter_type": "dual", "has_battery": True},
            "water_heaters": [],
            "ev_chargers": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "recorder_state.json"

            state_store = RecorderStateStore(state_file)
            state_store.load()
            now = datetime.now(pytz.timezone("Europe/Stockholm"))
            prev_time = now - timedelta(minutes=15)
            state_store._state = {
                "grid_import_total": {"value": 100.0, "timestamp": prev_time.isoformat()},
                "grid_export_total": {"value": 50.0, "timestamp": prev_time.isoformat()},
            }
            state_store.save()

            async def mock_get_ha_sensor_kw_normalized(entity):
                return 1.0  # All power sensors return 1 kW

            async def mock_get_ha_sensor_float(entity):
                cumulative_values = {
                    "sensor.grid_import_total": 100.5,  # +0.5 kWh
                    "sensor.grid_export_total": 50.25,  # +0.25 kWh
                    "sensor.battery_soc": 50.0,
                }
                return cumulative_values.get(entity)

            async def mock_get_ha_entity_state(entity):
                # Return state structure with unit_of_measurement for cumulative sensors
                state_values = {
                    "sensor.grid_import_total": {
                        "state": "100.5",
                        "attributes": {"unit_of_measurement": "kWh"},
                    },
                    "sensor.grid_export_total": {
                        "state": "50.25",
                        "attributes": {"unit_of_measurement": "kWh"},
                    },
                    "sensor.battery_soc": {
                        "state": "50.0",
                        "attributes": {"unit_of_measurement": "%"},
                    },
                }
                return state_values.get(entity)

            with (
                patch(
                    "backend.recorder.get_ha_sensor_kw_normalized",
                    side_effect=mock_get_ha_sensor_kw_normalized,
                ),
                patch("backend.recorder.get_ha_sensor_float", side_effect=mock_get_ha_sensor_float),
                patch("backend.recorder.get_ha_entity_state", side_effect=mock_get_ha_entity_state),
                patch("backend.recorder.get_current_slot_prices", return_value=None),
            ):
                mock_store = MagicMock()
                mock_store.get_system_state = AsyncMock(return_value=None)
                mock_store.set_system_state = AsyncMock()
                mock_store.store_slot_observations = AsyncMock()
                mock_store.close = AsyncMock()

                with patch("backend.recorder.LearningStore", return_value=mock_store):
                    await record_observation_from_current_state(
                        config=config, state_store=state_store
                    )

                    df = mock_store.store_slot_observations.call_args[0][0]
                    record = df.iloc[0].to_dict()

                    # Should use cumulative deltas
                    assert record["import_kwh"] == pytest.approx(0.5, abs=0.01)
                    assert record["export_kwh"] == pytest.approx(0.25, abs=0.01)


class TestStatePersistence:
    """Test suite for state file persistence."""

    def test_state_file_format(self):
        """Test that state file is saved in expected JSON format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            store = RecorderStateStore(state_file)
            store.load()

            now = datetime(2024, 1, 1, 12, 0, 0)
            store.get_delta("pv_total", 100.0, now)
            store.get_delta("load_total", 50.0, now)
            store.save()

            # Verify file format
            content = json.loads(state_file.read_text())
            assert "pv_total" in content
            assert "load_total" in content
            assert "value" in content["pv_total"]
            assert "timestamp" in content["pv_total"]
            assert content["pv_total"]["value"] == 100.0

    def test_directory_creation(self):
        """Test that parent directories are created automatically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "nested" / "dirs"
            state_file = nested_dir / "state.json"
            store = RecorderStateStore(state_file)
            store.load()

            now = datetime.now()
            store.get_delta("test", 100.0, now)
            store.save()

            assert nested_dir.exists()
            assert state_file.exists()


class TestRecorderSpikeValidation:
    """Test suite for recorder spike validation integration."""

    @pytest.mark.asyncio
    async def test_spike_values_zeroed_before_storage(self):
        """Test that spike values are zeroed before storage to database."""

        import pytz

        from backend.learning.store import LearningStore
        from backend.recorder import record_observation_from_current_state

        # Create test config with 8kW grid limit = 4.0 kWh max per slot
        config = {
            "timezone": "Europe/Stockholm",
            "system": {"grid": {"max_power_kw": 8.0}},
            "learning": {"sqlite_path": ":memory:"},
            "input_sensors": {"battery_soc": "sensor.test_soc"},
        }

        # Mock HA responses with spike values
        with (
            patch("backend.recorder.get_ha_sensor_float") as mock_soc,
            patch("backend.recorder.get_ha_sensor_kw_normalized") as mock_power,
            patch("backend.recorder.get_ha_entity_state") as mock_entity,
        ):
            mock_soc.return_value = 50.0  # Valid SoC
            mock_power.return_value = 100.0  # Spike power value (100kW!)
            mock_entity.return_value = None  # No cumulative sensors

            # Create a mock store to capture what gets stored
            tz = pytz.timezone("Europe/Stockholm")
            store = LearningStore(":memory:", tz)
            try:
                await store.ensure_wal_mode()

                with patch("backend.recorder.LearningStore") as mock_store_class:
                    mock_store = AsyncMock()
                    mock_store_class.return_value = mock_store

                    # Capture the DataFrame passed to store_slot_observations
                    stored_records = []

                    async def capture_store(df):
                        stored_records.extend(df.to_dict("records"))

                    mock_store.store_slot_observations = capture_store
                    mock_store.close = AsyncMock()

                    # Record observation
                    await record_observation_from_current_state(config)

                    # Verify store was called
                    assert len(stored_records) == 1
                    record = stored_records[0]

                    # All energy values should be validated
                    # With 100kW power, the energy would be 100 * 0.25 = 25 kWh
                    # This exceeds the 4.0 kWh threshold, so it should be zeroed
                    assert record["pv_kwh"] == 0.0, (
                        f"PV spike should be zeroed, got {record['pv_kwh']}"
                    )
                    assert record["load_kwh"] == 0.0, (
                        f"Load spike should be zeroed, got {record['load_kwh']}"
                    )
            finally:
                await store.close()

    @pytest.mark.asyncio
    async def test_valid_values_preserved_in_recorder(self):
        """Test that valid values are preserved during recording."""
        config = {
            "timezone": "Europe/Stockholm",
            "system": {"grid": {"max_power_kw": 8.0}},
            "learning": {"sqlite_path": ":memory:"},
            "input_sensors": {
                "battery_soc": "sensor.test_soc",
                "pv_power": "sensor.pv_power",
            },
        }

        # Mock HA responses with normal values
        with (
            patch("backend.recorder.get_ha_sensor_float") as mock_soc,
            patch("backend.recorder.get_ha_sensor_kw_normalized") as mock_power,
            patch("backend.recorder.get_ha_entity_state") as mock_entity,
        ):
            mock_soc.return_value = 50.0

            def mock_power_side_effect(entity_id, default=0.0):
                if entity_id == "sensor.pv_power":
                    return 2.0  # Normal 2kW PV power
                return default

            mock_power.side_effect = mock_power_side_effect
            mock_entity.return_value = None

            stored_records = []

            with patch("backend.recorder.LearningStore") as mock_store_class:
                mock_store = AsyncMock()
                mock_store_class.return_value = mock_store

                async def capture_store(df):
                    stored_records.extend(df.to_dict("records"))

                mock_store.store_slot_observations = capture_store
                mock_store.close = AsyncMock()

                await record_observation_from_current_state(config)

                assert len(stored_records) == 1
                record = stored_records[0]

                # 2kW * 0.25h = 0.5 kWh, which is under the 4.0 kWh threshold
                assert record["pv_kwh"] == 0.5, (
                    f"Valid PV should be preserved, got {record['pv_kwh']}"
                )

    @pytest.mark.asyncio
    async def test_recorder_handles_missing_config_gracefully(self):
        """Test that recorder handles missing grid config gracefully."""
        config = {
            "timezone": "Europe/Stockholm",
            "learning": {"sqlite_path": ":memory:"},
            "input_sensors": {"battery_soc": "sensor.test_soc"},
            # Missing system.grid.max_power_kw
        }

        with (
            patch("backend.recorder.get_ha_sensor_float") as mock_soc,
            patch("backend.recorder.get_ha_sensor_kw_normalized") as mock_power,
            patch("backend.recorder.get_ha_entity_state") as mock_entity,
            patch("backend.recorder.logger") as mock_logger,
        ):
            mock_soc.return_value = 50.0
            mock_power.return_value = 2.0
            mock_entity.return_value = None

            stored_records = []

            with patch("backend.recorder.LearningStore") as mock_store_class:
                mock_store = AsyncMock()
                mock_store_class.return_value = mock_store

                async def capture_store(df):
                    stored_records.extend(df.to_dict("records"))

                mock_store.store_slot_observations = capture_store
                mock_store.close = AsyncMock()

                await record_observation_from_current_state(config)

                # Should log a warning about missing config
                warning_calls = [
                    c for c in mock_logger.warning.call_args_list if "max_power_kw" in str(c)
                ]
                assert len(warning_calls) > 0 or any(
                    "validate" in str(c).lower() for c in mock_logger.warning.call_args_list
                )

                # Should still store the record
                assert len(stored_records) == 1


class TestRecorderTimeScaling:
    """Test suite for time-proportional scaling to fix sawtooth pattern."""

    def test_time_proportional_scaling_short_interval(self):
        """Task 4.1: Scale up when sensor interval is shorter than 15 min.

        Raw delta covers 10 min, scaled to 15 min.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            store = RecorderStateStore(state_file)
            store.load()

            # First reading at 10:43
            ts1 = datetime(2024, 1, 1, 10, 43, 0)
            store.get_delta("pv_total", 100.0, ts1, sensor_timestamp=ts1)

            # Second reading at 10:53 (10 min later)
            ts2 = datetime(2024, 1, 1, 10, 53, 0)
            sensor_ts2 = datetime(2024, 1, 1, 10, 53, 0)
            delta, is_valid = store.get_delta("pv_total", 102.0, ts2, sensor_timestamp=sensor_ts2)

            # Raw delta: 2.0 kWh over 10 min
            # Scaled: 2.0 * (15/10) = 3.0 kWh
            assert delta == pytest.approx(3.0, abs=0.01)
            assert is_valid is True

    def test_time_proportional_scaling_long_interval(self):
        """Task 4.1: Scale down when sensor interval is longer than 15 min.

        Raw delta covers 20 min, scaled to 15 min.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            store = RecorderStateStore(state_file)
            store.load()

            # First reading at 10:33
            ts1 = datetime(2024, 1, 1, 10, 33, 0)
            store.get_delta("pv_total", 100.0, ts1, sensor_timestamp=ts1)

            # Second reading at 10:53 (20 min later)
            ts2 = datetime(2024, 1, 1, 10, 53, 0)
            sensor_ts2 = datetime(2024, 1, 1, 10, 53, 0)
            delta, is_valid = store.get_delta("pv_total", 104.0, ts2, sensor_timestamp=sensor_ts2)

            # Raw delta: 4.0 kWh over 20 min
            # Scaled: 4.0 * (15/20) = 3.0 kWh
            assert delta == pytest.approx(3.0, abs=0.01)
            assert is_valid is True

    def test_backward_compatibility_missing_sensor_timestamp(self):
        """Task 4.2: No scaling when sensor_timestamp is None.

        Old state files or missing HA timestamps should use raw delta.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            store = RecorderStateStore(state_file)
            store.load()

            # First reading without sensor timestamp
            ts1 = datetime(2024, 1, 1, 10, 0, 0)
            store.get_delta("pv_total", 100.0, ts1, sensor_timestamp=None)

            # Second reading also without sensor timestamp
            ts2 = datetime(2024, 1, 1, 10, 15, 0)
            delta, is_valid = store.get_delta("pv_total", 103.0, ts2, sensor_timestamp=None)

            # No scaling applied
            assert delta == 3.0
            assert is_valid is True

    def test_backward_compatibility_old_state_file(self):
        """Task 4.2: Old state files without sensor_timestamp field work.

        Simulate loading from an old-format state file.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            # Create old-format state file (no sensor_timestamp)
            old_state = {
                "pv_total": {
                    "value": 100.0,
                    "timestamp": "2024-01-01T10:00:00",
                    # No sensor_timestamp field
                }
            }
            state_file.write_text(json.dumps(old_state))

            store = RecorderStateStore(state_file)
            store.load()

            # New reading with sensor timestamp
            ts2 = datetime(2024, 1, 1, 10, 15, 0)
            sensor_ts2 = datetime(2024, 1, 1, 10, 13, 0)  # 13 min gap
            delta, is_valid = store.get_delta("pv_total", 102.6, ts2, sensor_timestamp=sensor_ts2)

            # Old state has no sensor_timestamp, so no scaling
            assert delta == pytest.approx(2.6, abs=0.001)
            assert is_valid is True

            # State file should now have sensor_timestamp for next cycle
            store2 = RecorderStateStore(state_file)
            store2.load()
            assert "sensor_timestamp" in store2._state["pv_total"]

    def test_scaling_window_bounds_too_short(self):
        """Task 4.3: No scaling when interval < 5 minutes.

        Likely sensor glitch or rapid updates.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            store = RecorderStateStore(state_file)
            store.load()

            ts1 = datetime(2024, 1, 1, 10, 0, 0)
            store.get_delta("pv_total", 100.0, ts1, sensor_timestamp=ts1)

            # Only 3 minutes later (too short)
            ts2 = datetime(2024, 1, 1, 10, 3, 0)
            sensor_ts2 = datetime(2024, 1, 1, 10, 3, 0)
            delta, is_valid = store.get_delta("pv_total", 101.0, ts2, sensor_timestamp=sensor_ts2)

            # No scaling (outside 5-60 min window)
            assert delta == 1.0
            assert is_valid is True

    def test_scaling_window_bounds_too_long(self):
        """Task 4.3: No scaling when interval > 60 minutes.

        Likely restart or long gap.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            store = RecorderStateStore(state_file)
            store.load()

            ts1 = datetime(2024, 1, 1, 10, 0, 0)
            store.get_delta("pv_total", 100.0, ts1, sensor_timestamp=ts1)

            # 90 minutes later (too long)
            ts2 = datetime(2024, 1, 1, 11, 30, 0)
            sensor_ts2 = datetime(2024, 1, 1, 11, 30, 0)
            delta, is_valid = store.get_delta("pv_total", 110.0, ts2, sensor_timestamp=sensor_ts2)

            # No scaling (outside 5-60 min window)
            assert delta == 10.0
            assert is_valid is True

    def test_scaling_window_bounds_exactly_5_min(self):
        """Task 4.3: Scaling applied at exactly 5 minutes.

        Lower boundary of the valid window.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            store = RecorderStateStore(state_file)
            store.load()

            ts1 = datetime(2024, 1, 1, 10, 0, 0)
            store.get_delta("pv_total", 100.0, ts1, sensor_timestamp=ts1)

            # Exactly 5 minutes later
            ts2 = datetime(2024, 1, 1, 10, 5, 0)
            sensor_ts2 = datetime(2024, 1, 1, 10, 5, 0)
            delta, is_valid = store.get_delta("pv_total", 101.0, ts2, sensor_timestamp=sensor_ts2)

            # Should scale: 1.0 * (15/5) = 3.0
            assert delta == pytest.approx(3.0, abs=0.01)
            assert is_valid is True

    def test_scaling_window_bounds_exactly_60_min(self):
        """Task 4.3: Scaling applied at exactly 60 minutes.

        Upper boundary of the valid window.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            store = RecorderStateStore(state_file)
            store.load()

            ts1 = datetime(2024, 1, 1, 10, 0, 0)
            store.get_delta("pv_total", 100.0, ts1, sensor_timestamp=ts1)

            # Exactly 60 minutes later
            ts2 = datetime(2024, 1, 1, 11, 0, 0)
            sensor_ts2 = datetime(2024, 1, 1, 11, 0, 0)
            delta, is_valid = store.get_delta("pv_total", 104.0, ts2, sensor_timestamp=sensor_ts2)

            # Should scale: 4.0 * (15/60) = 1.0
            assert delta == pytest.approx(1.0, abs=0.01)
            assert is_valid is True

    def test_sensor_timestamp_persisted_to_state_file(self):
        """Task 4.2: sensor_timestamp is stored in state file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "state.json"
            store = RecorderStateStore(state_file)
            store.load()

            ts1 = datetime(2024, 1, 1, 10, 0, 0)
            sensor_ts1 = datetime(2024, 1, 1, 9, 58, 0)
            store.get_delta("pv_total", 100.0, ts1, sensor_timestamp=sensor_ts1)

            # Verify state file includes sensor_timestamp
            content = json.loads(state_file.read_text())
            assert "sensor_timestamp" in content["pv_total"]
            assert content["pv_total"]["sensor_timestamp"] == "2024-01-01T09:58:00"


class TestBackfillInterpolation:
    """Test suite for backfill interpolation fix."""

    def test_interpolation_produces_consistent_deltas(self):
        """Task 4.4: Interpolation eliminates sawtooth in backfill.

        Simulates the sawtooth scenario: readings at 10:53 and 11:03
        should produce consistent deltas when interpolated.
        """
        from backend.learning.engine import LearningEngine

        # Simulate readings that would cause sawtooth with ffill
        # Sensor updates at :03, :13, :23, :33, :43, :53
        # Backfill slots at :00, :15, :30, :45
        cumulative_data = {
            "sensor.pv_total": [
                # 10:53 reading (sensor timestamp)
                (datetime(2024, 1, 1, 10, 53, 0), 100.0),
                # 11:03 reading (10 min later)
                (datetime(2024, 1, 1, 11, 3, 0), 102.0),
                # 11:13 reading (10 min later)
                (datetime(2024, 1, 1, 11, 13, 0), 104.0),
                # 11:23 reading (10 min later)
                (datetime(2024, 1, 1, 11, 23, 0), 106.0),
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal config for LearningEngine
            config = {
                "timezone": "UTC",
                "learning": {"sqlite_path": str(Path(tmpdir) / "test.db"), "sensor_map": {}},
                "input_sensors": {},
                "system": {"grid": {"max_power_kw": 10.0}},
            }
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(json.dumps(config))

            # Patch config loading
            with patch.object(LearningEngine, "_load_config", return_value=config):
                engine = LearningEngine(str(config_path))
                result = engine.etl_cumulative_to_slots(cumulative_data, resolution_minutes=15)

                # With interpolation, deltas should be consistent
                # 100 kWh at 10:53, 106 kWh at 11:23
                # Total time: 30 min, total delta: 6 kWh
                # Rate: 6 kWh / 30 min = 0.2 kWh per min
                # Per 15-min slot: 3.0 kWh

                if len(result) > 0 and "pv_kwh" in result.columns:
                    pv_deltas = result["pv_kwh"].tolist()
                    # All non-zero deltas should be approximately equal
                    non_zero = [d for d in pv_deltas if d > 0]
                    if len(non_zero) > 1:
                        # Variation should be small (not sawtooth pattern)
                        max_delta = max(non_zero)
                        min_delta = min(non_zero)
                        # Ratio should be close to 1:1 (not 2:1 sawtooth)
                        assert max_delta / min_delta < 1.5, (
                            f"Deltas show sawtooth pattern: {non_zero}"
                        )


class TestLoadIsolationFromDeferrableLoads:
    """Test suite for isolating base load from EV charging and water heating."""

    @pytest.fixture
    def base_config(self):
        """Create a base mock configuration with cumulative sensors."""
        return {
            "timezone": "Europe/Stockholm",
            "learning": {"sqlite_path": ":memory:"},
            "input_sensors": {
                "pv_power": "sensor.pv_power",
                "load_power": "sensor.load_power",
                "grid_power": "sensor.grid_power",
                "battery_power": "sensor.battery_power",
                "water_power": "sensor.water_power",
                "battery_soc": "sensor.battery_soc",
                "total_pv_production": "sensor.total_pv_production",
                "total_load_consumption": "sensor.total_load_consumption",
            },
            "system": {"grid_meter_type": "net", "has_battery": True},
            "water_heaters": [],
            "ev_chargers": [],
        }

    @pytest.mark.asyncio
    async def test_ev_charging_subtracted_from_total_load(self, base_config):
        """Spec: Load Isolation - EV charging subtracted from total load."""
        config = base_config.copy()
        config["ev_chargers"] = [{"sensor": "sensor.ev_power", "enabled": True}]

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "recorder_state.json"
            state_store = RecorderStateStore(state_file)
            state_store.load()
            now = datetime.now(pytz.timezone("Europe/Stockholm"))
            prev_time = now - timedelta(minutes=15)
            state_store._state = {
                "pv_total": {"value": 100.0, "timestamp": prev_time.isoformat()},
                "load_total": {"value": 50.0, "timestamp": prev_time.isoformat()},
            }
            state_store.save()

            async def mock_get_ha_sensor_kw_normalized(entity):
                return {
                    "sensor.pv_power": 5.0,
                    "sensor.load_power": 7.0,
                    "sensor.grid_power": 2.0,
                    "sensor.battery_power": 0.0,
                    "sensor.water_power": 0.0,
                    "sensor.ev_power": 4.0,
                }.get(entity, 0.0)

            async def mock_get_ha_sensor_float(entity):
                if entity == "sensor.battery_soc":
                    return 50.0
                return None

            async def mock_get_ha_entity_state(entity):
                return {
                    "sensor.total_pv_production": {
                        "state": "101.25",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                    "sensor.total_load_consumption": {
                        "state": "53.0",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                }.get(entity)

            with (
                patch(
                    "backend.recorder.get_ha_sensor_kw_normalized",
                    side_effect=mock_get_ha_sensor_kw_normalized,
                ),
                patch("backend.recorder.get_ha_sensor_float", side_effect=mock_get_ha_sensor_float),
                patch("backend.recorder.get_ha_entity_state", side_effect=mock_get_ha_entity_state),
                patch("backend.recorder.get_current_slot_prices", return_value=None),
            ):
                mock_store = MagicMock()
                mock_store.get_system_state = AsyncMock(return_value=None)
                mock_store.set_system_state = AsyncMock()
                mock_store.store_slot_observations = AsyncMock()
                mock_store.close = AsyncMock()

                with patch("backend.recorder.LearningStore", return_value=mock_store):
                    await record_observation_from_current_state(
                        config=config, state_store=state_store
                    )

                    df = mock_store.store_slot_observations.call_args[0][0]
                    record = df.iloc[0].to_dict()

                    assert record["ev_charging_kwh"] == pytest.approx(1.0, abs=0.01)
                    assert record["load_kwh"] == pytest.approx(2.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_water_heating_subtracted_from_total_load(self, base_config):
        """Spec: Load Isolation - Water heating subtracted from total load."""
        config = base_config.copy()

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "recorder_state.json"
            state_store = RecorderStateStore(state_file)
            state_store.load()
            now = datetime.now(pytz.timezone("Europe/Stockholm"))
            prev_time = now - timedelta(minutes=15)
            state_store._state = {
                "pv_total": {"value": 100.0, "timestamp": prev_time.isoformat()},
                "load_total": {"value": 50.0, "timestamp": prev_time.isoformat()},
            }
            state_store.save()

            async def mock_get_ha_sensor_kw_normalized(entity):
                return {
                    "sensor.pv_power": 5.0,
                    "sensor.load_power": 5.0,
                    "sensor.grid_power": 2.0,
                    "sensor.battery_power": 0.0,
                    "sensor.water_power": 3.0,
                }.get(entity, 0.0)

            async def mock_get_ha_entity_state(entity):
                return {
                    "sensor.total_pv_production": {
                        "state": "101.25",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                    "sensor.total_load_consumption": {
                        "state": "52.0",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                    "sensor.battery_soc": {
                        "state": "50.0",
                        "attributes": {"unit_of_measurement": "%"},
                    },
                }.get(entity)

            with (
                patch(
                    "backend.recorder.get_ha_sensor_kw_normalized",
                    side_effect=mock_get_ha_sensor_kw_normalized,
                ),
                patch(
                    "backend.core.ha_client.get_ha_entity_state",
                    side_effect=mock_get_ha_entity_state,
                ),
                patch("backend.recorder.get_current_slot_prices", return_value=None),
            ):
                mock_store = MagicMock()
                mock_store.get_system_state = AsyncMock(return_value=None)
                mock_store.set_system_state = AsyncMock()
                mock_store.store_slot_observations = AsyncMock()
                mock_store.close = AsyncMock()

                with patch("backend.recorder.LearningStore", return_value=mock_store):
                    await record_observation_from_current_state(
                        config=config, state_store=state_store
                    )

                    df = mock_store.store_slot_observations.call_args[0][0]
                    record = df.iloc[0].to_dict()

                    assert record["water_kwh"] == pytest.approx(0.75, abs=0.01)
                    assert record["load_kwh"] == pytest.approx(1.25, abs=0.01)

    @pytest.mark.asyncio
    async def test_both_ev_and_water_subtracted_from_total_load(self, base_config):
        """Spec: Load Isolation - Both EV and water subtracted together."""
        config = base_config.copy()
        config["ev_chargers"] = [{"sensor": "sensor.ev_power", "enabled": True}]

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "recorder_state.json"
            state_store = RecorderStateStore(state_file)
            state_store.load()
            now = datetime.now(pytz.timezone("Europe/Stockholm"))
            prev_time = now - timedelta(minutes=15)
            state_store._state = {
                "pv_total": {"value": 100.0, "timestamp": prev_time.isoformat()},
                "load_total": {"value": 50.0, "timestamp": prev_time.isoformat()},
            }
            state_store.save()

            async def mock_get_ha_sensor_kw_normalized(entity):
                return {
                    "sensor.pv_power": 5.0,
                    "sensor.load_power": 11.0,
                    "sensor.grid_power": 6.0,
                    "sensor.battery_power": 0.0,
                    "sensor.water_power": 3.0,
                    "sensor.ev_power": 4.0,
                }.get(entity, 0.0)

            async def mock_get_ha_sensor_float(entity):
                if entity == "sensor.battery_soc":
                    return 50.0
                return None

            async def mock_get_ha_entity_state(entity):
                return {
                    "sensor.total_pv_production": {
                        "state": "101.25",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                    "sensor.total_load_consumption": {
                        "state": "55.0",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                }.get(entity)

            with (
                patch(
                    "backend.recorder.get_ha_sensor_kw_normalized",
                    side_effect=mock_get_ha_sensor_kw_normalized,
                ),
                patch("backend.recorder.get_ha_sensor_float", side_effect=mock_get_ha_sensor_float),
                patch("backend.recorder.get_ha_entity_state", side_effect=mock_get_ha_entity_state),
                patch("backend.recorder.get_current_slot_prices", return_value=None),
            ):
                mock_store = MagicMock()
                mock_store.get_system_state = AsyncMock(return_value=None)
                mock_store.set_system_state = AsyncMock()
                mock_store.store_slot_observations = AsyncMock()
                mock_store.close = AsyncMock()

                with patch("backend.recorder.LearningStore", return_value=mock_store):
                    await record_observation_from_current_state(
                        config=config, state_store=state_store
                    )

                    df = mock_store.store_slot_observations.call_args[0][0]
                    record = df.iloc[0].to_dict()

                    assert record["ev_charging_kwh"] == pytest.approx(1.0, abs=0.01)
                    assert record["water_kwh"] == pytest.approx(0.75, abs=0.01)
                    assert record["load_kwh"] == pytest.approx(3.25, abs=0.01)

    @pytest.mark.asyncio
    async def test_negative_base_load_clamped_to_zero(self, base_config):
        """Spec: Load Isolation - Negative base load clamped to zero with warning."""
        config = base_config.copy()
        config["ev_chargers"] = [{"sensor": "sensor.ev_power", "enabled": True}]

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "recorder_state.json"
            state_store = RecorderStateStore(state_file)
            state_store.load()
            now = datetime.now(pytz.timezone("Europe/Stockholm"))
            prev_time = now - timedelta(minutes=15)
            state_store._state = {
                "pv_total": {"value": 100.0, "timestamp": prev_time.isoformat()},
                "load_total": {"value": 50.0, "timestamp": prev_time.isoformat()},
            }
            state_store.save()

            async def mock_get_ha_sensor_kw_normalized(entity):
                return {
                    "sensor.pv_power": 5.0,
                    "sensor.load_power": 12.0,
                    "sensor.grid_power": 10.0,
                    "sensor.battery_power": 0.0,
                    "sensor.water_power": 4.0,
                    "sensor.ev_power": 8.0,
                }.get(entity, 0.0)

            async def mock_get_ha_sensor_float(entity):
                if entity == "sensor.battery_soc":
                    return 50.0
                return None

            async def mock_get_ha_entity_state(entity):
                return {
                    "sensor.total_pv_production": {
                        "state": "101.25",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                    "sensor.total_load_consumption": {
                        "state": "52.0",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                }.get(entity)

            with (
                patch(
                    "backend.recorder.get_ha_sensor_kw_normalized",
                    side_effect=mock_get_ha_sensor_kw_normalized,
                ),
                patch("backend.recorder.get_ha_sensor_float", side_effect=mock_get_ha_sensor_float),
                patch("backend.recorder.get_ha_entity_state", side_effect=mock_get_ha_entity_state),
                patch("backend.recorder.get_current_slot_prices", return_value=None),
                patch("backend.recorder.logger") as mock_logger,
            ):
                mock_store = MagicMock()
                mock_store.get_system_state = AsyncMock(return_value=None)
                mock_store.set_system_state = AsyncMock()
                mock_store.store_slot_observations = AsyncMock()
                mock_store.close = AsyncMock()

                with patch("backend.recorder.LearningStore", return_value=mock_store):
                    await record_observation_from_current_state(
                        config=config, state_store=state_store
                    )

                    df = mock_store.store_slot_observations.call_args[0][0]
                    record = df.iloc[0].to_dict()

                    assert record["ev_charging_kwh"] == pytest.approx(2.0, abs=0.01)
                    assert record["water_kwh"] == pytest.approx(1.0, abs=0.01)
                    assert record["load_kwh"] == 0.0

                    warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
                    assert any("Negative base load" in w for w in warning_calls)

    @pytest.mark.asyncio
    async def test_power_snapshot_fallback_uses_base_load(self, base_config):
        """Spec: Load Isolation - Power snapshot fallback uses base load from disaggregator."""
        config = base_config.copy()
        config["input_sensors"].pop("total_load_consumption", None)
        config["input_sensors"].pop("total_pv_production", None)
        config["ev_chargers"] = [{"sensor": "sensor.ev_power", "enabled": True}]

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "recorder_state.json"
            state_store = RecorderStateStore(state_file)
            state_store.load()

            async def mock_get_ha_sensor_kw_normalized(entity):
                return {
                    "sensor.pv_power": 4.0,
                    "sensor.load_power": 7.0,
                    "sensor.grid_power": 3.0,
                    "sensor.battery_power": 0.0,
                    "sensor.water_power": 1.0,
                    "sensor.ev_power": 4.0,
                }.get(entity, 0.0)

            async def mock_get_ha_sensor_float(entity):
                if entity == "sensor.battery_soc":
                    return 50.0
                return None

            mock_disaggregator = MagicMock()
            mock_disaggregator.update_current_power = AsyncMock(return_value=5.0)
            mock_disaggregator.calculate_base_load = MagicMock(return_value=2.0)

            with (
                patch(
                    "backend.recorder.get_ha_sensor_kw_normalized",
                    side_effect=mock_get_ha_sensor_kw_normalized,
                ),
                patch("backend.recorder.get_ha_sensor_float", side_effect=mock_get_ha_sensor_float),
                patch("backend.recorder.get_current_slot_prices", return_value=None),
            ):
                mock_store = MagicMock()
                mock_store.get_system_state = AsyncMock(return_value=None)
                mock_store.set_system_state = AsyncMock()
                mock_store.store_slot_observations = AsyncMock()
                mock_store.close = AsyncMock()

                with patch("backend.recorder.LearningStore", return_value=mock_store):
                    await record_observation_from_current_state(
                        config=config,
                        disaggregator=mock_disaggregator,
                        state_store=state_store,
                    )

                    df = mock_store.store_slot_observations.call_args[0][0]
                    record = df.iloc[0].to_dict()

                    assert record["ev_charging_kwh"] == pytest.approx(1.0, abs=0.01)
                    assert record["water_kwh"] == pytest.approx(0.25, abs=0.01)
                    assert record["load_kwh"] == pytest.approx(0.5, abs=0.01)

    @pytest.mark.asyncio
    async def test_ev_energy_sensor_cumulative_delta(self, base_config):
        """Spec: EV charger with energy_sensor uses cumulative delta, not power snapshot."""
        config = base_config.copy()
        config["ev_chargers"] = [
            {
                "id": "ev1",
                "sensor": "sensor.ev_power",
                "energy_sensor": "sensor.ev_energy",
                "enabled": True,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "recorder_state.json"
            state_store = RecorderStateStore(state_file)
            state_store.load()
            now = datetime.now(pytz.timezone("Europe/Stockholm"))
            prev_time = now - timedelta(minutes=15)
            state_store._state = {
                "pv_total": {"value": 100.0, "timestamp": prev_time.isoformat()},
                "load_total": {"value": 50.0, "timestamp": prev_time.isoformat()},
                "ev_energy_ev1": {"value": 120.5, "timestamp": prev_time.isoformat()},
            }
            state_store.save()

            async def mock_get_ha_sensor_kw_normalized(entity):
                return {
                    "sensor.pv_power": 5.0,
                    "sensor.load_power": 7.0,
                    "sensor.grid_power": 2.0,
                    "sensor.battery_power": 0.0,
                    "sensor.water_power": 0.0,
                    "sensor.ev_power": 4.0,
                }.get(entity, 0.0)

            async def mock_get_ha_sensor_float(entity):
                if entity == "sensor.battery_soc":
                    return 50.0
                return None

            async def mock_get_ha_entity_state(entity):
                return {
                    "sensor.total_pv_production": {
                        "state": "101.25",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                    "sensor.total_load_consumption": {
                        "state": "53.0",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                    "sensor.ev_energy": {
                        "state": "121.5",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                }.get(entity)

            with (
                patch(
                    "backend.recorder.get_ha_sensor_kw_normalized",
                    side_effect=mock_get_ha_sensor_kw_normalized,
                ),
                patch("backend.recorder.get_ha_sensor_float", side_effect=mock_get_ha_sensor_float),
                patch("backend.recorder.get_ha_entity_state", side_effect=mock_get_ha_entity_state),
                patch("backend.recorder.get_current_slot_prices", return_value=None),
            ):
                mock_store = MagicMock()
                mock_store.get_system_state = AsyncMock(return_value=None)
                mock_store.set_system_state = AsyncMock()
                mock_store.store_slot_observations = AsyncMock()
                mock_store.close = AsyncMock()

                with patch("backend.recorder.LearningStore", return_value=mock_store):
                    await record_observation_from_current_state(
                        config=config, state_store=state_store
                    )

                    df = mock_store.store_slot_observations.call_args[0][0]
                    record = df.iloc[0].to_dict()

                    # Delta: 121.5 - 120.5 = 1.0 kWh
                    assert record["ev_charging_kwh"] == pytest.approx(1.0, abs=0.01)
                    # Total load 3.0 - EV 1.0 = 2.0 kWh
                    assert record["load_kwh"] == pytest.approx(2.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_water_energy_sensor_cumulative_delta(self, base_config):
        """Spec: Water heater with energy_sensor uses cumulative delta, not power snapshot."""
        config = base_config.copy()
        config["water_heaters"] = [
            {
                "id": "wh1",
                "sensor": "sensor.water_power",
                "energy_sensor": "sensor.water_energy",
                "enabled": True,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "recorder_state.json"
            state_store = RecorderStateStore(state_file)
            state_store.load()
            now = datetime.now(pytz.timezone("Europe/Stockholm"))
            prev_time = now - timedelta(minutes=15)
            state_store._state = {
                "pv_total": {"value": 100.0, "timestamp": prev_time.isoformat()},
                "load_total": {"value": 50.0, "timestamp": prev_time.isoformat()},
                "water_energy_wh1": {"value": 50.0, "timestamp": prev_time.isoformat()},
            }
            state_store.save()

            async def mock_get_ha_sensor_kw_normalized(entity):
                return {
                    "sensor.pv_power": 5.0,
                    "sensor.load_power": 5.0,
                    "sensor.grid_power": 2.0,
                    "sensor.battery_power": 0.0,
                    "sensor.water_power": 3.0,
                }.get(entity, 0.0)

            async def mock_get_ha_sensor_float(entity):
                if entity == "sensor.battery_soc":
                    return 50.0
                return None

            async def mock_get_ha_entity_state(entity):
                return {
                    "sensor.total_pv_production": {
                        "state": "101.25",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                    "sensor.total_load_consumption": {
                        "state": "52.0",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                    "sensor.water_energy": {
                        "state": "50.75",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                }.get(entity)

            with (
                patch(
                    "backend.recorder.get_ha_sensor_kw_normalized",
                    side_effect=mock_get_ha_sensor_kw_normalized,
                ),
                patch("backend.recorder.get_ha_sensor_float", side_effect=mock_get_ha_sensor_float),
                patch("backend.recorder.get_ha_entity_state", side_effect=mock_get_ha_entity_state),
                patch("backend.recorder.get_current_slot_prices", return_value=None),
            ):
                mock_store = MagicMock()
                mock_store.get_system_state = AsyncMock(return_value=None)
                mock_store.set_system_state = AsyncMock()
                mock_store.store_slot_observations = AsyncMock()
                mock_store.close = AsyncMock()

                with patch("backend.recorder.LearningStore", return_value=mock_store):
                    await record_observation_from_current_state(
                        config=config, state_store=state_store
                    )

                    df = mock_store.store_slot_observations.call_args[0][0]
                    record = df.iloc[0].to_dict()

                    # Delta: 50.75 - 50.0 = 0.75 kWh
                    assert record["water_kwh"] == pytest.approx(0.75, abs=0.01)
                    # Total load 2.0 - water 0.75 = 1.25 kWh
                    assert record["load_kwh"] == pytest.approx(1.25, abs=0.01)

    @pytest.mark.asyncio
    async def test_energy_sensor_fallback_to_snapshot_when_no_prior_state(self, base_config):
        """Spec: EV charger with energy_sensor falls back to power snapshot on first run."""
        config = base_config.copy()
        config["ev_chargers"] = [
            {
                "id": "ev1",
                "sensor": "sensor.ev_power",
                "energy_sensor": "sensor.ev_energy",
                "enabled": True,
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "recorder_state.json"
            state_store = RecorderStateStore(state_file)
            state_store.load()
            now = datetime.now(pytz.timezone("Europe/Stockholm"))
            prev_time = now - timedelta(minutes=15)
            # No ev_energy_ev1 in state (first run)
            state_store._state = {
                "pv_total": {"value": 100.0, "timestamp": prev_time.isoformat()},
                "load_total": {"value": 50.0, "timestamp": prev_time.isoformat()},
            }
            state_store.save()

            async def mock_get_ha_sensor_kw_normalized(entity):
                return {
                    "sensor.pv_power": 5.0,
                    "sensor.load_power": 7.0,
                    "sensor.grid_power": 2.0,
                    "sensor.battery_power": 0.0,
                    "sensor.water_power": 0.0,
                    "sensor.ev_power": 4.0,
                }.get(entity, 0.0)

            async def mock_get_ha_sensor_float(entity):
                if entity == "sensor.battery_soc":
                    return 50.0
                return None

            async def mock_get_ha_entity_state(entity):
                return {
                    "sensor.total_pv_production": {
                        "state": "101.25",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                    "sensor.total_load_consumption": {
                        "state": "53.0",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                    "sensor.ev_energy": {
                        "state": "121.5",
                        "attributes": {"unit_of_measurement": "kWh"},
                        "last_updated": now.isoformat(),
                    },
                }.get(entity)

            with (
                patch(
                    "backend.recorder.get_ha_sensor_kw_normalized",
                    side_effect=mock_get_ha_sensor_kw_normalized,
                ),
                patch("backend.recorder.get_ha_sensor_float", side_effect=mock_get_ha_sensor_float),
                patch("backend.recorder.get_ha_entity_state", side_effect=mock_get_ha_entity_state),
                patch("backend.recorder.get_current_slot_prices", return_value=None),
            ):
                mock_store = MagicMock()
                mock_store.get_system_state = AsyncMock(return_value=None)
                mock_store.set_system_state = AsyncMock()
                mock_store.store_slot_observations = AsyncMock()
                mock_store.close = AsyncMock()

                with patch("backend.recorder.LearningStore", return_value=mock_store):
                    await record_observation_from_current_state(
                        config=config, state_store=state_store
                    )

                    df = mock_store.store_slot_observations.call_args[0][0]
                    record = df.iloc[0].to_dict()

                    # Fallback: 4.0 kW * 0.25h = 1.0 kWh
                    assert record["ev_charging_kwh"] == pytest.approx(1.0, abs=0.01)
