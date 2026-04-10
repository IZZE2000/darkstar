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
    assert config.water_heater.temp_normal == 60
    assert config.automation_toggle_entity is None


class TestWaterHeaterDeviceConfig:
    """Task 5.4: per-device water heater config loading."""

    def test_per_device_configs_built_from_array(self, tmp_path):
        """water_heater_devices list is populated from water_heaters[] entries."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "executor": {"enabled": True},  # Required to avoid early return
            "water_heaters": [
                {
                    "id": "wh1",
                    "name": "Main Heater",
                    "enabled": True,
                    "target_entity": "climate.water_heater_1",
                    "power_kw": 3.0,
                },
                {
                    "id": "wh2",
                    "name": "Cabin Heater",
                    "enabled": True,
                    "target_entity": "climate.water_heater_2",
                    "power_kw": 2.0,
                },
            ],
        }
        with config_file.open("w") as f:
            yaml.dump(config_data, f)

        config = load_executor_config(str(config_file))

        assert len(config.water_heater_devices) == 2
        wh1 = config.water_heater_devices[0]
        assert wh1.id == "wh1"
        assert wh1.name == "Main Heater"
        assert wh1.target_entity == "climate.water_heater_1"
        assert wh1.power_kw == 3.0

        wh2 = config.water_heater_devices[1]
        assert wh2.id == "wh2"
        assert wh2.target_entity == "climate.water_heater_2"
        assert wh2.power_kw == 2.0

    def test_heater_without_target_entity_excluded(self, tmp_path):
        """Heaters without target_entity are not included in water_heater_devices."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "executor": {"enabled": True},
            "water_heaters": [
                {
                    "id": "wh1",
                    "enabled": True,
                    "target_entity": "climate.water_heater_1",
                    "power_kw": 3.0,
                },
                {
                    "id": "wh_no_entity",
                    "enabled": True,
                    # No target_entity
                    "power_kw": 2.0,
                },
            ],
        }
        with config_file.open("w") as f:
            yaml.dump(config_data, f)

        config = load_executor_config(str(config_file))

        assert len(config.water_heater_devices) == 1
        assert config.water_heater_devices[0].id == "wh1"

    def test_disabled_heater_excluded(self, tmp_path):
        """Disabled heaters are not included in water_heater_devices."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "executor": {"enabled": True},
            "water_heaters": [
                {
                    "id": "wh1",
                    "enabled": True,
                    "target_entity": "climate.water_heater_1",
                    "power_kw": 3.0,
                },
                {
                    "id": "wh2",
                    "enabled": False,
                    "target_entity": "climate.water_heater_2",
                    "power_kw": 2.0,
                },
            ],
        }
        with config_file.open("w") as f:
            yaml.dump(config_data, f)

        config = load_executor_config(str(config_file))

        assert len(config.water_heater_devices) == 1
        assert config.water_heater_devices[0].id == "wh1"

    def test_global_temps_still_loaded(self, tmp_path):
        """Global water heater temperatures are loaded into water_heater field."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "executor": {
                "water_heater": {
                    "temp_normal": 55,
                    "temp_off": 35,
                    "temp_boost": 70,
                }
            },
            "water_heaters": [
                {
                    "id": "wh1",
                    "enabled": True,
                    "target_entity": "climate.water_heater_1",
                    "power_kw": 3.0,
                }
            ],
        }
        with config_file.open("w") as f:
            yaml.dump(config_data, f)

        config = load_executor_config(str(config_file))

        assert config.water_heater.temp_normal == 55
        assert config.water_heater.temp_off == 35
        assert config.water_heater.temp_boost == 70
        assert len(config.water_heater_devices) == 1

    def test_empty_water_heaters_produces_empty_list(self, tmp_path):
        """No water_heaters array produces empty water_heater_devices list."""
        config_file = tmp_path / "config.yaml"
        config_data = {"executor": {}}
        with config_file.open("w") as f:
            yaml.dump(config_data, f)

        config = load_executor_config(str(config_file))

        assert config.water_heater_devices == []
