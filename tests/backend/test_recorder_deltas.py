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
                assert record["pv_kwh"] == 0.0, f"PV spike should be zeroed, got {record['pv_kwh']}"
                assert record["load_kwh"] == 0.0, (
                    f"Load spike should be zeroed, got {record['load_kwh']}"
                )

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
