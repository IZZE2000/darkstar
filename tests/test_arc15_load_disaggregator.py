"""Tests for ARC15 LoadDisaggregator with new entity-centric format."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.loads.base import LoadType
from backend.loads.service import LoadDisaggregator


class TestARC15EntityArrays:
    """Test LoadDisaggregator with new water_heaters[] and ev_chargers[] arrays."""

    @pytest.fixture
    def mock_config_arc15(self):
        """Config using new entity-centric format (config_version: 2)."""
        return {
            "config_version": 2,
            "water_heaters": [
                {
                    "id": "main_tank",
                    "name": "Main Water Heater",
                    "enabled": True,
                    "power_kw": 3.0,
                    "sensor": "sensor.vvb_power",
                    "type": "binary",
                    "nominal_power_kw": 3.0,
                },
                {
                    "id": "upstairs_tank",
                    "name": "Upstairs Tank",
                    "enabled": False,  # Disabled
                    "power_kw": 3.0,
                    "sensor": "sensor.wh2_power",
                    "type": "binary",
                    "nominal_power_kw": 3.0,
                },
            ],
            "ev_chargers": [
                {
                    "id": "tesla",
                    "name": "Tesla Model 3",
                    "enabled": True,
                    "max_power_kw": 11.0,
                    "battery_capacity_kwh": 82.0,
                    "sensor": "sensor.tesla_power",
                    "type": "variable",
                    "nominal_power_kw": 11.0,
                }
            ],
        }

    @pytest.fixture
    def mock_config_arc15_multiple_ev(self):
        """Config with multiple EV chargers."""
        return {
            "config_version": 2,
            "water_heaters": [],
            "ev_chargers": [
                {
                    "id": "tesla",
                    "name": "Tesla Model 3",
                    "enabled": True,
                    "max_power_kw": 11.0,
                    "sensor": "sensor.tesla_power",
                    "type": "variable",
                    "nominal_power_kw": 11.0,
                },
                {
                    "id": "fiat",
                    "name": "Fiat 500e",
                    "enabled": True,
                    "max_power_kw": 7.4,
                    "sensor": "sensor.fiat_power",
                    "type": "variable",
                    "nominal_power_kw": 7.4,
                },
            ],
        }

    def test_arc15_load_registration(self, mock_config_arc15):
        """Test that loads are correctly registered from ARC15 config."""
        disaggregator = LoadDisaggregator(mock_config_arc15)
        loads = disaggregator.list_active_loads()

        # Should have 2 active loads (main_tank enabled, tesla enabled, upstairs_tank disabled)
        assert len(loads) == 2

        # Check water heater
        wh = disaggregator.get_load_by_id("main_tank")
        assert wh is not None
        assert wh.name == "Main Water Heater"
        assert wh.sensor_key == "sensor.vvb_power"
        assert wh.type == LoadType.BINARY
        assert wh.nominal_power_kw == 3.0

        # Check disabled water heater is not registered
        assert disaggregator.get_load_by_id("upstairs_tank") is None

        # Check EV charger
        ev = disaggregator.get_load_by_id("tesla")
        assert ev is not None
        assert ev.name == "Tesla Model 3"
        assert ev.sensor_key == "sensor.tesla_power"
        assert ev.type == LoadType.VARIABLE
        assert ev.nominal_power_kw == 11.0

    def test_arc15_multiple_ev_chargers(self, mock_config_arc15_multiple_ev):
        """Test registration of multiple EV chargers."""
        disaggregator = LoadDisaggregator(mock_config_arc15_multiple_ev)
        loads = disaggregator.list_active_loads()

        assert len(loads) == 2

        tesla = disaggregator.get_load_by_id("tesla")
        assert tesla.nominal_power_kw == 11.0

        fiat = disaggregator.get_load_by_id("fiat")
        assert fiat.nominal_power_kw == 7.4

    @pytest.mark.asyncio
    async def test_arc15_update_current_power(self, mock_config_arc15):
        """Test fetching power from HA sensors with ARC15 config."""
        disaggregator = LoadDisaggregator(mock_config_arc15)

        with patch("backend.loads.service.get_ha_sensor_float", new_callable=AsyncMock) as mock_get:
            # sensor.vvb_power -> 3000W, sensor.tesla_power -> 5500W
            def mock_sensor(sensor):
                if "vvb" in sensor:
                    return 3000.0
                elif "tesla" in sensor:
                    return 5500.0
                return 0.0

            mock_get.side_effect = mock_sensor

            total_controllable = await disaggregator.update_current_power()

            assert total_controllable == 8.5  # (3000 + 5500) / 1000
            assert disaggregator.get_load_by_id("main_tank").current_power_kw == 3.0
            assert disaggregator.get_load_by_id("tesla").current_power_kw == 5.5


class TestBackwardCompatibility:
    """Test that legacy deferrable_loads format still works."""

    @pytest.fixture
    def mock_config_legacy(self):
        """Legacy config using deferrable_loads (config_version: 1)."""
        return {
            "config_version": 1,
            "deferrable_loads": [
                {
                    "id": "water_heater",
                    "name": "Water Heater",
                    "sensor_key": "water_power_sensor",
                    "type": "binary",
                    "nominal_power_kw": 3.0,
                },
                {
                    "id": "ev_charger",
                    "name": "EV Charger",
                    "sensor_key": "sensor.ev_power",
                    "type": "variable",
                    "nominal_power_kw": 11.0,
                },
            ],
            "input_sensors": {"water_power_sensor": "sensor.water_heater_power"},
        }

    def test_legacy_load_registration(self, mock_config_legacy):
        """Test that legacy deferrable_loads format still works."""
        disaggregator = LoadDisaggregator(mock_config_legacy)
        loads = disaggregator.list_active_loads()

        assert len(loads) == 2

        wh = disaggregator.get_load_by_id("water_heater")
        assert wh is not None
        assert wh.name == "Water Heater"
        assert wh.sensor_key == "sensor.water_heater_power"
        assert wh.type == LoadType.BINARY

        ev = disaggregator.get_load_by_id("ev_charger")
        assert ev.sensor_key == "sensor.ev_power"
        assert ev.type == LoadType.VARIABLE

    def test_mixed_config_prefers_arc15(self):
        """Test that when both formats exist, ARC15 takes precedence."""
        config = {
            "config_version": 2,
            "deferrable_loads": [
                {
                    "id": "legacy_wh",
                    "name": "Legacy Water Heater",
                    "sensor_key": "legacy_sensor",
                    "type": "binary",
                    "nominal_power_kw": 2.0,
                }
            ],
            "input_sensors": {"legacy_sensor": "sensor.legacy"},
            "water_heaters": [
                {
                    "id": "arc15_wh",
                    "name": "ARC15 Water Heater",
                    "enabled": True,
                    "power_kw": 3.0,
                    "sensor": "sensor.arc15_wh",
                    "type": "binary",
                    "nominal_power_kw": 3.0,
                }
            ],
            "ev_chargers": [],
        }

        disaggregator = LoadDisaggregator(config)
        loads = disaggregator.list_active_loads()

        # Should use ARC15 format, not legacy
        assert len(loads) == 1
        assert disaggregator.get_load_by_id("arc15_wh") is not None
        assert disaggregator.get_load_by_id("legacy_wh") is None

    def test_no_loads_configured(self):
        """Test handling of empty load configuration."""
        config = {
            "config_version": 2,
            "water_heaters": [],
            "ev_chargers": [],
        }

        disaggregator = LoadDisaggregator(config)
        loads = disaggregator.list_active_loads()

        assert len(loads) == 0

    def test_missing_sensor_skips_load(self):
        """Test that loads without sensors are skipped."""
        config = {
            "config_version": 2,
            "water_heaters": [
                {
                    "id": "no_sensor_wh",
                    "name": "No Sensor Water Heater",
                    "enabled": True,
                    "power_kw": 3.0,
                    # Missing "sensor" field
                    "type": "binary",
                    "nominal_power_kw": 3.0,
                },
                {
                    "id": "good_wh",
                    "name": "Good Water Heater",
                    "enabled": True,
                    "power_kw": 3.0,
                    "sensor": "sensor.good_wh",
                    "type": "binary",
                    "nominal_power_kw": 3.0,
                },
            ],
            "ev_chargers": [],
        }

        disaggregator = LoadDisaggregator(config)
        loads = disaggregator.list_active_loads()

        # Only the good one should be registered
        assert len(loads) == 1
        assert disaggregator.get_load_by_id("no_sensor_wh") is None
        assert disaggregator.get_load_by_id("good_wh") is not None

    def test_invalid_load_type_defaults_safely(self):
        """Test that invalid load types default to safe values."""
        config = {
            "config_version": 2,
            "water_heaters": [
                {
                    "id": "invalid_type",
                    "name": "Invalid Type",
                    "enabled": True,
                    "power_kw": 3.0,
                    "sensor": "sensor.wh",
                    "type": "invalid_type",  # Invalid type
                    "nominal_power_kw": 3.0,
                }
            ],
            "ev_chargers": [],
        }

        disaggregator = LoadDisaggregator(config)
        load = disaggregator.get_load_by_id("invalid_type")

        assert load is not None
        assert load.type == LoadType.BINARY  # Should default to binary for water heaters
