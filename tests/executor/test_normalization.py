import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

# Add root to sys.path to import modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from executor.config import _str_or_none, load_executor_config
from inputs import get_ha_sensor_kw_normalized


@pytest.mark.asyncio
async def test_get_ha_sensor_kw_normalized():
    """Verify HA sensor unit normalization (W vs kW)."""
    # Mock data for W
    mock_w = {"state": "1500", "attributes": {"unit_of_measurement": "W"}}
    # Mock data for kW
    mock_kw = {"state": "1.5", "attributes": {"unit_of_measurement": "kW"}}
    # Mock data for no units
    mock_none = {"state": "2.5", "attributes": {}}

    with patch("inputs.get_ha_entity_state") as mock_get:
        # Test W normalization
        mock_get.return_value = mock_w
        val = await get_ha_sensor_kw_normalized("any")
        assert val == 1.5

        # Test kW preservation
        mock_get.return_value = mock_kw
        val = await get_ha_sensor_kw_normalized("any")
        assert val == 1.5

        # Test no unit preservation
        mock_get.return_value = mock_none
        val = await get_ha_sensor_kw_normalized("any")
        assert val == 2.5

        # Test error handling
        mock_get.return_value = {"state": "invalid"}
        val = await get_ha_sensor_kw_normalized("any")
        assert val is None

        mock_get.return_value = None
        val = await get_ha_sensor_kw_normalized("any")
        assert val is None


def test_str_or_none_normalization():
    """Verify that _str_or_none correctly normalizes various input types."""
    assert _str_or_none("sensor.test") == "sensor.test"
    assert _str_or_none("") is None
    assert _str_or_none(" ") is None
    assert _str_or_none(None) is None
    assert _str_or_none(123) == "123"
    assert _str_or_none("\t\n") is None


def test_load_executor_config_normalization(tmp_path):
    """Verify that load_executor_config correctly applies normalization to entity fields."""
    config_file = tmp_path / "config.yaml"

    config_data = {
        "executor": {
            "inverter": {
                "work_mode": "select.my_mode",
                "grid_charging_enable": "",
                "max_charge_current": "  ",
                "max_discharge_current": None,
            },
            "water_heater": {"target_entity": ""},
            "automation_toggle_entity": "input_boolean.automation",
        }
    }

    with config_file.open("w") as f:
        yaml.dump(config_data, f)

    config = load_executor_config(str(config_file))

    assert config.inverter.work_mode == "select.my_mode"
    assert config.inverter.grid_charging_enable is None
    assert config.inverter.max_charge_current is None
    assert config.inverter.max_discharge_current is None
    assert config.water_heater.target_entity is None
    assert config.automation_toggle_entity == "input_boolean.automation"
