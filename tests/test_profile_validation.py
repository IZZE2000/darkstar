from executor.profiles import load_profile


def test_sungrow_validation_missing_composite():
    """Test that Sungrow profile correctly identifies missing composite entities."""
    # Load the actual Sungrow profile
    profile = load_profile("sungrow")

    # Create a config that is missing the composite entities
    # Only standard entities are present
    invalid_config = {
        "executor": {
            "inverter": {
                "work_mode": "select.ems_mode",
                "max_charge_power": "number.max_charge_power",
                "max_discharge_power": "number.max_discharge_power",
                "grid_max_export_power": "number.export_power_limit",
                "grid_max_export_power_switch": "switch.export_power_limit",
                # Missing: ems_mode, forced_charge_discharge_cmd
            }
        }
    }

    missing = profile.get_missing_entities(invalid_config)

    # Should report the missing composite entities
    assert "executor.inverter.ems_mode" in missing
    assert "executor.inverter.forced_charge_discharge_cmd" in missing


def test_sungrow_validation_valid():
    """Test that Sungrow profile passes with full configuration."""
    profile = load_profile("sungrow")

    # Valid config with custom_entities
    valid_config = {
        "executor": {
            "inverter": {
                "work_mode": "select.ems_mode",
                "max_charge_power": "number.max_charge_power",
                "max_discharge_power": "number.max_discharge_power",
                "grid_max_export_power": "number.export_power_limit",
                "grid_max_export_power_switch": "switch.export_power_limit",
                "custom_entities": {
                    "ems_mode": "select.ems_mode",
                    "forced_charge_discharge_cmd": "select.battery_forced_charge_discharge",
                },
            }
        }
    }

    missing = profile.get_missing_entities(valid_config)

    assert len(missing) == 0
