import yaml

from executor.config import load_executor_config


def test_nested_custom_entities_loads_correctly(tmp_path):
    """Verify that nested custom_entities in YAML is properly unpacked, not stringified (REV F71)."""
    config_file = tmp_path / "config.yaml"

    config_data = {
        "executor": {
            "inverter": {
                "work_mode": "select.ems_mode",
                "custom_entities": {
                    "ems_mode": "select.ems_mode",
                    "forced_charge_discharge_cmd": "select.battery_forced_charge_discharge",
                },
            }
        }
    }

    with config_file.open("w") as f:
        yaml.dump(config_data, f)

    config = load_executor_config(str(config_file))

    assert config.inverter.custom_entities.get("ems_mode") == "select.ems_mode"
    assert (
        config.inverter.custom_entities.get("forced_charge_discharge_cmd")
        == "select.battery_forced_charge_discharge"
    )


def test_nested_custom_entities_with_legacy_keys(tmp_path):
    """Verify that legacy keys at root level are also captured (REV F69 migration path)."""
    config_file = tmp_path / "config.yaml"

    config_data = {
        "executor": {
            "inverter": {
                "work_mode": "select.ems_mode",
                "ems_mode": "select.ems_mode",
                "forced_charge_discharge_cmd": "select.battery_forced_charge_discharge",
            }
        }
    }

    with config_file.open("w") as f:
        yaml.dump(config_data, f)

    config = load_executor_config(str(config_file))

    assert config.inverter.custom_entities.get("ems_mode") == "select.ems_mode"
    assert (
        config.inverter.custom_entities.get("forced_charge_discharge_cmd")
        == "select.battery_forced_charge_discharge"
    )


def test_custom_entities_not_stringified(tmp_path):
    """Verify that nested dict doesn't get converted to string representation (REV F71)."""
    config_file = tmp_path / "config.yaml"

    config_data = {
        "executor": {
            "inverter": {
                "custom_entities": {
                    "ems_mode": "select.ems_mode",
                }
            }
        }
    }

    with config_file.open("w") as f:
        yaml.dump(config_data, f)

    config = load_executor_config(str(config_file))

    # The value should NOT be a stringified dict representation
    val = config.inverter.custom_entities.get("ems_mode")
    assert val is not None
    assert isinstance(val, str), f"Expected str, got {type(val)}: {val}"
    assert val == "select.ems_mode"


def test_load_executor_config_defaults(tmp_path):
    """Verify that missing entities default to None in the loaded config."""
    config_file = tmp_path / "config.yaml"
    config_data = {"executor": {}}

    with config_file.open("w") as f:
        yaml.dump(config_data, f)

    config = load_executor_config(str(config_file))

    assert config.inverter.work_mode is None
    assert config.inverter.grid_charging_enable is None
    assert config.water_heater.target_entity is None
    assert config.automation_toggle_entity is None
