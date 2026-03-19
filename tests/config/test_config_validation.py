from backend.api.routers.config import _validate_config_for_save


def test_validate_config_executor_entities_required_when_enabled():
    config = {
        "executor": {"enabled": True, "inverter": {}},
        "system": {"has_battery": True},
        "input_sensors": {},
    }
    issues = _validate_config_for_save(config)

    # REV UI23: Missing required entities now return warnings instead of errors
    # to allow incremental configuration across tabs
    warning_messages = [i["message"] for i in issues if i["severity"] == "warning"]
    assert any("work_mode" in m for m in warning_messages)
    assert any("grid_charging_enable" in m for m in warning_messages)
    assert any("battery_soc" in m for m in warning_messages)


def test_validate_config_executor_entities_not_required_when_disabled():
    config = {
        "executor": {"enabled": False, "inverter": {}},
        "system": {"has_battery": True},
        "input_sensors": {},
    }
    issues = _validate_config_for_save(config)

    # Should NOT have errors for missing executor entities if disabled
    # (But might still have battery capacity error if has_battery is True)
    error_messages = [i["message"] for i in issues if i["severity"] == "error"]
    assert not any("executor.inverter.work_mode" in m for m in error_messages)
    assert not any("executor.inverter.grid_charging_enable" in m for m in error_messages)
    # input_sensors.battery_soc might still be considered critical for other things?
    # Current implementation in _validate_config_for_save only checks them if executor is enabled.
    assert not any("input_sensors.battery_soc" in m for m in error_messages)


def test_validate_config_battery_capacity_required():
    config = {
        "executor": {"enabled": False},
        "system": {"has_battery": True},
        "battery": {"capacity_kwh": 0},
    }
    issues = _validate_config_for_save(config)
    assert any(
        "Battery enabled but capacity not configured" in i["message"]
        for i in issues
        if i["severity"] == "error"
    )


def test_validate_config_valid_config_no_issues():
    config = {
        "executor": {
            "enabled": True,
            "inverter": {
                "work_mode": "select.inverter_work_mode",
                "grid_charging_enable": "switch.inverter_grid_charging",
                "soc_target": "number.soc_target",
            },
        },
        "system": {"has_battery": True, "location": {"latitude": 59.3, "longitude": 18.1}},
        "battery": {"capacity_kwh": 10.0},
        "input_sensors": {"battery_soc": "sensor.battery_soc"},
    }
    issues = _validate_config_for_save(config)
    errors = [i for i in issues if i["severity"] == "error"]
    assert len(errors) == 0


def test_validate_config_battery_entities_not_required_if_no_battery():
    config = {
        "executor": {"enabled": True, "inverter": {}},
        "system": {"has_battery": False},
        "input_sensors": {},
        # Provide valid non-battery config to avoid other errors
        "battery": {"capacity_kwh": 0},
    }
    issues = _validate_config_for_save(config)

    # Should NOT have errors for missing battery entities
    error_messages = [i["message"] for i in issues if i["severity"] == "error"]
    assert not any("executor.inverter.work_mode" in m for m in error_messages)
    assert not any("executor.inverter.grid_charging_enable" in m for m in error_messages)
    assert not any("input_sensors.battery_soc" in m for m in error_messages)


def test_validate_config_fronius_success():
    """Verify Fronius config validates without grid_charging_entity."""
    config = {
        "executor": {
            "enabled": True,
            "inverter": {
                "work_mode": "select.mode",
                "max_charge_power": "number.max_charge",
                "max_discharge_power": "number.max_discharge",
                "minimum_reserve": "number.reserve",
                "grid_charge_power": "number.charge_power",
                "soc_target": "input_number.target",
            },
        },
        "system": {
            "has_battery": True,
            "inverter_profile": "fronius",
            "location": {"latitude": 59.3, "longitude": 18.1},
        },
        "input_sensors": {"battery_soc": "sensor.soc"},
        "battery": {"capacity_kwh": 10},
        "water_heating": {},
    }
    issues = _validate_config_for_save(config)
    errors = [i for i in issues if i["severity"] == "error"]
    assert len(errors) == 0, f"Found errors: {errors}"


class TestWaterHeaterValidation:
    """Test water_heaters[] array validation (ARC15)."""

    def test_valid_water_heater_new_format(self):
        config = {
            "config_version": 2,
            "system": {"has_water_heater": True, "has_battery": False, "has_ev_charger": False},
            "water_heaters": [
                {
                    "id": "main_tank",
                    "name": "Main Water Heater",
                    "enabled": True,
                    "power_kw": 3.0,
                    "min_kwh_per_day": 6.0,
                    "sensor": "sensor.vvb_power",
                    "type": "binary",
                }
            ],
        }
        issues = _validate_config_for_save(config)
        water_heater_errors = [
            i for i in issues if i["severity"] == "error" and "water heater" in i["message"].lower()
        ]
        assert len(water_heater_errors) == 0

    def test_water_heater_missing_id(self):
        config = {
            "config_version": 2,
            "system": {"has_water_heater": True, "has_battery": False, "has_ev_charger": False},
            "water_heaters": [{"name": "Main Water Heater", "power_kw": 3.0}],
        }
        issues = _validate_config_for_save(config)
        errors = [i for i in issues if i["severity"] == "error"]
        assert any("missing required field 'id'" in e["message"] for e in errors)

    def test_water_heater_duplicate_id(self):
        config = {
            "config_version": 2,
            "system": {"has_water_heater": True, "has_battery": False, "has_ev_charger": False},
            "water_heaters": [
                {"id": "main_tank", "name": "Water Heater 1", "power_kw": 3.0},
                {"id": "main_tank", "name": "Water Heater 2", "power_kw": 3.0},
            ],
        }
        issues = _validate_config_for_save(config)
        errors = [i for i in issues if i["severity"] == "error"]
        assert any("Duplicate water heater ID" in e["message"] for e in errors)


class TestEVChargerValidation:
    """Test ev_chargers[] array validation (ARC15)."""

    def test_valid_ev_charger_new_format(self):
        config = {
            "config_version": 2,
            "system": {"has_ev_charger": True, "has_battery": False, "has_water_heater": False},
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
        issues = _validate_config_for_save(config)
        ev_errors = [
            i for i in issues if i["severity"] == "error" and "ev charger" in i["message"].lower()
        ]
        assert len(ev_errors) == 0

    def test_ev_departure_time_valid(self):
        for time_str in ["07:00", "23:30", "00:00", "12:59", "7:00"]:
            config = {
                "config_version": 2,
                "system": {"has_ev_charger": True, "has_battery": False, "has_water_heater": False},
                "ev_chargers": [
                    {
                        "id": "tesla",
                        "name": "Tesla",
                        "max_power_kw": 11.0,
                        "battery_capacity_kwh": 82.0,
                    }
                ],
                "ev_departure_time": time_str,
            }
            issues = _validate_config_for_save(config)
            errors = [
                i
                for i in issues
                if i["severity"] == "error" and "departure time" in i["message"].lower()
            ]
            assert len(errors) == 0

    def test_ev_departure_time_invalid(self):
        for time_str in ["25:00", "12:60", "7:00 AM", "invalid"]:
            config = {
                "config_version": 2,
                "system": {"has_ev_charger": True, "has_battery": False, "has_water_heater": False},
                "ev_chargers": [
                    {
                        "id": "tesla",
                        "name": "Tesla",
                        "max_power_kw": 11.0,
                        "battery_capacity_kwh": 82.0,
                    }
                ],
                "ev_departure_time": time_str,
            }
            issues = _validate_config_for_save(config)
            errors = [
                i
                for i in issues
                if i["severity"] == "error" and "departure time" in i["message"].lower()
            ]
            assert len(errors) == 1


class TestBackwardCompatibility:
    """Test backward compatibility (ARC15)."""

    def test_legacy_water_heater_format(self):
        config = {
            "config_version": 1,
            "system": {"has_water_heater": True, "has_battery": False, "has_ev_charger": False},
            "water_heating": {"power_kw": 3.0, "min_kwh_per_day": 6.0},
            "deferrable_loads": [
                {
                    "id": "water_heater",
                    "name": "Water Heater",
                    "type": "binary",
                    "nominal_power_kw": 3.0,
                }
            ],
        }
        issues = _validate_config_for_save(config)
        water_heater_errors = [
            i for i in issues if i["severity"] == "error" and "water heater" in i["message"].lower()
        ]
        assert len(water_heater_errors) == 0


class TestPreWriteValidation:
    """Test pre-write structural validation (F57)."""

    def test_validate_config_for_write_success(self):
        from backend.config_migration import validate_config_for_write

        config = {
            "config_version": 2,
            "system": {},
            "battery": {},
            "executor": {},
            "input_sensors": {},
        }
        assert validate_config_for_write(config) is True

    def test_validate_config_for_write_missing_section(self):
        from backend.config_migration import validate_config_for_write

        config = {"config_version": 2, "system": {}, "executor": {}, "input_sensors": {}}
        assert validate_config_for_write(config) is False

    def test_validate_config_for_write_deprecated_key(self):
        from backend.config_migration import validate_config_for_write

        config = {
            "config_version": 2,
            "system": {},
            "battery": {},
            "executor": {},
            "input_sensors": {},
            "deferrable_loads": [],
        }
        assert validate_config_for_write(config) is False
