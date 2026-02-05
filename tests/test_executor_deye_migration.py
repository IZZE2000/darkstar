"""
Integration tests for Deye Profile Migration.

Verifies that the new profile-based logic produces identical results to the
previous hardcoded logic for Deye/SunSynk inverters.
"""

import pytest

from executor.config import ControllerConfig, InverterConfig, WaterHeaterConfig
from executor.controller import make_decision
from executor.override import SlotPlan, SystemState
from executor.profiles import load_profile


class TestDeyeMigration:
    """Test suite for Deye profile migration and backward compatibility."""

    @pytest.fixture
    def deye_profile(self):
        """Load the real Deye profile."""
        return load_profile("deye", profiles_dir="profiles")

    @pytest.fixture
    def configs(self):
        """Standard Deye-like configurations."""
        ctrl_cfg = ControllerConfig(
            min_charge_a=10.0,
            max_charge_a=185.0,
            round_step_a=5.0,
        )
        inv_cfg = InverterConfig(
            work_mode_export="Export First",
            work_mode_zero_export="Zero Export To CT",
            control_unit="A",
        )
        wh_cfg = WaterHeaterConfig()
        return ctrl_cfg, inv_cfg, wh_cfg

    def test_mode_translation_equivalence(self, deye_profile, configs):
        """Verify that mode translation matches legacy logic."""
        ctrl_cfg, inv_cfg, _wh_cfg = configs

        # Test 1: Export case
        slot_export = SlotPlan(export_kw=5.0, charge_kw=0)
        state = SystemState(current_soc_percent=50.0)  # Fixed field name

        # Legacy decision
        decision_legacy = make_decision(
            slot_export, state, config=ctrl_cfg, inverter_config=inv_cfg
        )

        # Profile decision
        decision_profile = make_decision(
            slot_export, state, config=ctrl_cfg, inverter_config=inv_cfg, profile=deye_profile
        )

        assert decision_profile.work_mode == decision_legacy.work_mode
        assert decision_profile.work_mode == "Export First"
        assert decision_profile.grid_charging is False

        # Test 2: Zero Export case
        slot_zero = SlotPlan(export_kw=0, charge_kw=0)
        decision_legacy = make_decision(slot_zero, state, config=ctrl_cfg, inverter_config=inv_cfg)
        decision_profile = make_decision(
            slot_zero, state, config=ctrl_cfg, inverter_config=inv_cfg, profile=deye_profile
        )

        assert decision_profile.work_mode == decision_legacy.work_mode
        assert decision_profile.work_mode == "Zero Export To CT"
        assert decision_profile.grid_charging is False

    def test_grid_charging_equivalence(self, deye_profile, configs):
        """Verify that grid charging logic remains identical."""
        ctrl_cfg, inv_cfg, _wh_cfg = configs
        state = SystemState(current_soc_percent=20.0)

        # Grid charge case
        slot_charge = SlotPlan(export_kw=0, charge_kw=3.0)

        # Legacy
        decision_legacy = make_decision(
            slot_charge, state, config=ctrl_cfg, inverter_config=inv_cfg
        )

        # Profile
        decision_profile = make_decision(
            slot_charge, state, config=ctrl_cfg, inverter_config=inv_cfg, profile=deye_profile
        )

        assert decision_profile.grid_charging is True
        assert decision_profile.grid_charging == decision_legacy.grid_charging
        # Deye uses Zero Export mode for grid charging
        assert decision_profile.work_mode == "Zero Export To CT"

    def test_behavioral_limits_equivalence(self, deye_profile, configs):
        """Verify that charge/discharge limit calculations match."""
        ctrl_cfg, inv_cfg, _wh_cfg = configs
        state = SystemState(current_soc_percent=20.0)
        slot_charge = SlotPlan(export_kw=0, charge_kw=1.0)  # ~20.8A at 48V

        # Profile decision
        decision_profile = make_decision(
            slot_charge, state, config=ctrl_cfg, inverter_config=inv_cfg, profile=deye_profile
        )

        # Expected: 1000W / 46V = 21.7A -> rounded to 20A (step 5)
        # Note: legacy code uses config.min_voltage_v (46V)
        assert decision_profile.charge_value == 20.0
        assert decision_profile.write_charge_current is True

    def test_fallback_behavior(self, configs):
        """Verify that system falls back to config if profile is None."""
        ctrl_cfg, inv_cfg, _wh_cfg = configs
        state = SystemState(current_soc_percent=50.0)
        slot = SlotPlan(export_kw=5.0)

        # No profile provided
        decision = make_decision(
            slot, state, config=ctrl_cfg, inverter_config=inv_cfg, profile=None
        )

        assert decision.work_mode == "Export First"
        assert decision.control_unit == "A"

    def test_custom_config_override_precedence(self, deye_profile, configs):
        """Verify that config overrides still work as fallback if profile value is missing."""
        ctrl_cfg, inv_cfg, _wh_cfg = configs

        # Create a modified config
        inv_cfg.work_mode_export = "Custom Export"

        slot = SlotPlan(export_kw=5.0)
        state = SystemState(current_soc_percent=50.0)

        # With profile: profile takes precedence if value exists
        decision = make_decision(
            slot, state, config=ctrl_cfg, inverter_config=inv_cfg, profile=deye_profile
        )
        assert decision.work_mode == "Export First"  # From profile

        # Without profile: config takes precedence
        decision_no_profile = make_decision(
            slot, state, config=ctrl_cfg, inverter_config=inv_cfg, profile=None
        )
        assert decision_no_profile.work_mode == "Custom Export"  # From config
