"""Tests for ARC15 config API validation."""

from backend.api.routers.config import _validate_config_for_save


class TestWaterHeaterValidation:
    """Test water_heaters[] array validation."""

    def test_valid_water_heater_new_format(self):
        """Test valid water heater in new ARC15 format."""
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
                    "nominal_power_kw": 3.0,
                }
            ],
        }
        issues = _validate_config_for_save(config)
        # Filter only water heater related errors
        water_heater_errors = [
            i for i in issues if i["severity"] == "error" and "water heater" in i["message"].lower()
        ]
        assert len(water_heater_errors) == 0

    def test_water_heater_missing_id(self):
        """Test water heater without required id field."""
        config = {
            "config_version": 2,
            "system": {"has_water_heater": True, "has_battery": False, "has_ev_charger": False},
            "water_heaters": [
                {
                    "name": "Main Water Heater",
                    "power_kw": 3.0,
                }
            ],
        }
        issues = _validate_config_for_save(config)
        errors = [i for i in issues if i["severity"] == "error"]
        assert any("missing required field 'id'" in e["message"] for e in errors)

    def test_water_heater_duplicate_id(self):
        """Test water heaters with duplicate IDs."""
        config = {
            "config_version": 2,
            "system": {"has_water_heater": True, "has_battery": False, "has_ev_charger": False},
            "water_heaters": [
                {
                    "id": "main_tank",
                    "name": "Water Heater 1",
                    "power_kw": 3.0,
                },
                {
                    "id": "main_tank",  # Duplicate
                    "name": "Water Heater 2",
                    "power_kw": 3.0,
                },
            ],
        }
        issues = _validate_config_for_save(config)
        errors = [i for i in issues if i["severity"] == "error"]
        assert any("Duplicate water heater ID" in e["message"] for e in errors)

    def test_water_heater_invalid_power(self):
        """Test water heater with invalid power value."""
        config = {
            "config_version": 2,
            "system": {"has_water_heater": True, "has_battery": False, "has_ev_charger": False},
            "water_heaters": [
                {
                    "id": "main_tank",
                    "name": "Main Water Heater",
                    "power_kw": 0,  # Invalid
                }
            ],
        }
        issues = _validate_config_for_save(config)
        errors = [i for i in issues if i["severity"] == "error"]
        assert any("invalid power_kw" in e["message"] for e in errors)

    def test_water_heater_disabled_all(self):
        """Test warning when all water heaters are disabled."""
        config = {
            "config_version": 2,
            "system": {"has_water_heater": True, "has_battery": False, "has_ev_charger": False},
            "water_heaters": [
                {
                    "id": "main_tank",
                    "name": "Main Water Heater",
                    "enabled": False,
                    "power_kw": 3.0,
                }
            ],
        }
        issues = _validate_config_for_save(config)
        warnings = [i for i in issues if i["severity"] == "warning"]
        assert any("All water heaters are disabled" in w["message"] for w in warnings)


class TestEVChargerValidation:
    """Test ev_chargers[] array validation."""

    def test_valid_ev_charger_new_format(self):
        """Test valid EV charger in new ARC15 format."""
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
                    "min_soc_percent": 20.0,
                    "target_soc_percent": 80.0,
                    "sensor": "sensor.tesla_power",
                    "type": "variable",
                    "nominal_power_kw": 11.0,
                }
            ],
        }
        issues = _validate_config_for_save(config)
        # Filter only EV charger related errors
        ev_errors = [
            i for i in issues if i["severity"] == "error" and "ev charger" in i["message"].lower()
        ]
        assert len(ev_errors) == 0

    def test_ev_charger_missing_id(self):
        """Test EV charger without required id field."""
        config = {
            "config_version": 2,
            "system": {"has_ev_charger": True, "has_battery": False, "has_water_heater": False},
            "ev_chargers": [
                {
                    "name": "Tesla",
                    "max_power_kw": 11.0,
                }
            ],
        }
        issues = _validate_config_for_save(config)
        errors = [i for i in issues if i["severity"] == "error"]
        assert any("missing required field 'id'" in e["message"] for e in errors)

    def test_ev_charger_duplicate_id(self):
        """Test EV chargers with duplicate IDs."""
        config = {
            "config_version": 2,
            "system": {"has_ev_charger": True, "has_battery": False, "has_water_heater": False},
            "ev_chargers": [
                {
                    "id": "main_ev",
                    "name": "EV 1",
                    "max_power_kw": 11.0,
                },
                {
                    "id": "main_ev",  # Duplicate
                    "name": "EV 2",
                    "max_power_kw": 7.4,
                },
            ],
        }
        issues = _validate_config_for_save(config)
        errors = [i for i in issues if i["severity"] == "error"]
        assert any("Duplicate EV charger ID" in e["message"] for e in errors)

    def test_ev_charger_invalid_capacity(self):
        """Test EV charger with invalid battery capacity."""
        config = {
            "config_version": 2,
            "system": {"has_ev_charger": True, "has_battery": False, "has_water_heater": False},
            "ev_chargers": [
                {
                    "id": "tesla",
                    "name": "Tesla",
                    "max_power_kw": 11.0,
                    "battery_capacity_kwh": 0,  # Invalid
                }
            ],
        }
        issues = _validate_config_for_save(config)
        errors = [i for i in issues if i["severity"] == "error"]
        assert any("invalid battery_capacity_kwh" in e["message"] for e in errors)

    def test_ev_charger_invalid_soc(self):
        """Test EV charger with invalid SoC percentages."""
        config = {
            "config_version": 2,
            "system": {"has_ev_charger": True, "has_battery": False, "has_water_heater": False},
            "ev_chargers": [
                {
                    "id": "tesla",
                    "name": "Tesla",
                    "max_power_kw": 11.0,
                    "battery_capacity_kwh": 82.0,
                    "min_soc_percent": 150,  # Invalid
                }
            ],
        }
        issues = _validate_config_for_save(config)
        warnings = [i for i in issues if i["severity"] == "warning"]
        assert any("invalid min_soc_percent" in w["message"] for w in warnings)


class TestBackwardCompatibility:
    """Test backward compatibility with old format."""

    def test_legacy_water_heater_format(self):
        """Test that legacy water_heating config still works."""
        config = {
            "config_version": 1,
            "system": {"has_water_heater": True, "has_battery": False, "has_ev_charger": False},
            "water_heating": {
                "power_kw": 3.0,
                "min_kwh_per_day": 6.0,
            },
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
        # Check no water heater specific errors in legacy mode
        water_heater_errors = [
            i for i in issues if i["severity"] == "error" and "water heater" in i["message"].lower()
        ]
        assert len(water_heater_errors) == 0

    def test_no_devices_configured(self):
        """Test config with devices disabled."""
        config = {
            "config_version": 2,
            "system": {
                "has_water_heater": False,
                "has_ev_charger": False,
                "has_battery": False,
            },
            "water_heaters": [],
            "ev_chargers": [],
        }
        issues = _validate_config_for_save(config)
        # No water heater or EV validation errors when disabled
        water_ev_errors = [
            i
            for i in issues
            if i["severity"] == "error"
            and ("water heater" in i["message"].lower() or "ev charger" in i["message"].lower())
        ]
        assert len(water_ev_errors) == 0
