"""Tests for REV F71: Sungrow Composite Entity Loading & EV Serialization Fix"""

import json

import yaml

from executor.actions import ActionResult
from executor.config import load_executor_config
from executor.history import ExecutionRecord


class TestCustomEntitiesLoading:
    """Test that nested custom_entities loads correctly (REV F71 Bug 1)."""

    def test_nested_custom_entities_loads_correctly(self, tmp_path):
        """Verify that nested custom_entities in YAML is properly unpacked, not stringified."""
        config_file = tmp_path / "config.yaml"

        # Config with properly nested custom_entities (as user's config has)
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

        # Verify custom_entities are properly unpacked (not stringified)
        assert config.inverter.custom_entities.get("ems_mode") == "select.ems_mode"
        assert (
            config.inverter.custom_entities.get("forced_charge_discharge_cmd")
            == "select.battery_forced_charge_discharge"
        )

    def test_nested_custom_entities_with_legacy_keys(self, tmp_path):
        """Verify that legacy keys at root level are also captured (REV F69 migration path)."""
        config_file = tmp_path / "config.yaml"

        # Config with legacy keys at root level (what REV F69 migration handles)
        config_data = {
            "executor": {
                "inverter": {
                    "work_mode": "select.ems_mode",
                    "ems_mode": "select.ems_mode",  # Legacy location
                    "forced_charge_discharge_cmd": "select.battery_forced_charge_discharge",  # Legacy location
                }
            }
        }

        with config_file.open("w") as f:
            yaml.dump(config_data, f)

        config = load_executor_config(str(config_file))

        # Verify both paths work - legacy at root should be caught by catch-all
        assert config.inverter.custom_entities.get("ems_mode") == "select.ems_mode"
        assert (
            config.inverter.custom_entities.get("forced_charge_discharge_cmd")
            == "select.battery_forced_charge_discharge"
        )

    def test_custom_entities_not_stringified(self, tmp_path):
        """Verify that nested dict doesn't get converted to string representation."""
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


class TestEVActionResultSerialization:
    """Test that EV charger execution records serialize to JSON (REV F71 Bug 2)."""

    def test_ev_charge_start_record_serializes(self):
        """Verify EV charge start ExecutionRecord serializes to JSON."""
        record = ExecutionRecord(
            executed_at="2026-02-17T20:23:00+01:00",
            slot_start="2026-02-17T20:15:00+01:00",
            commanded_work_mode="ev_charge_start",
            before_soc_percent=50,
            success=1,
            source="ev_charger",
            duration_ms=150,
            action_results=[
                {
                    "type": "ev_charger_switch",
                    "success": True,
                    "message": "EV charger turned on",
                    "entity_id": "switch.laddare_charging",
                    "previous_value": False,
                    "new_value": True,
                    "verified_value": True,
                    "verification_success": True,
                    "skipped": False,
                    "error_details": None,
                }
            ],
        )

        # Should not raise
        json_str = json.dumps(record.__dict__)
        assert "ev_charge_start" in json_str
        assert "switch.laddare_charging" in json_str

    def test_ev_charge_stop_record_serializes(self):
        """Verify EV charge stop ExecutionRecord serializes to JSON."""
        record = ExecutionRecord(
            executed_at="2026-02-17T20:24:00+01:00",
            slot_start="2026-02-17T20:15:00+01:00",
            commanded_work_mode="ev_charge_stop",
            before_soc_percent=55,
            success=1,
            source="ev_charger",
            duration_ms=120,
            action_results=[
                {
                    "type": "ev_charger_switch",
                    "success": True,
                    "message": "EV charger turned off",
                    "entity_id": "switch.laddare_charging",
                    "previous_value": True,
                    "new_value": False,
                    "verified_value": False,
                    "verification_success": True,
                    "skipped": False,
                    "error_details": None,
                }
            ],
        )

        # Should not raise
        json_str = json.dumps(record.__dict__)
        assert "ev_charge_stop" in json_str

    def test_action_result_as_dict_serializable(self):
        """Verify that ActionResult converted to dict IS JSON serializable."""
        result = ActionResult(
            action_type="ev_charger_switch",
            success=True,
            message="EV charger turned on",
            entity_id="switch.laddare_charging",
            previous_value=False,
            new_value=True,
            verified_value=True,
            verification_success=True,
            skipped=False,
            error_details=None,
        )

        # Convert to dict (as done in engine.py after F71 fix)
        result_dict = {
            "type": result.action_type,
            "success": result.success,
            "message": result.message,
            "entity_id": result.entity_id,
            "previous_value": result.previous_value,
            "new_value": result.new_value,
            "verified_value": result.verified_value,
            "verification_success": result.verification_success,
            "skipped": result.skipped,
            "error_details": result.error_details,
        }

        # Should not raise
        json_str = json.dumps(result_dict)
        assert "ev_charger_switch" in json_str
