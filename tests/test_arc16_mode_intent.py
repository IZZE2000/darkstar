"""
ARC16 Test: Verify mode_intent correctly disambiguates shared mode values.

This test verifies that when multiple modes share the same value string,
the mode_intent field ensures the correct composite entities are applied.
"""

import pytest

from executor.controller import Controller
from executor.override import SlotPlan, SystemState
from executor.profiles import (
    InverterProfile,
    ProfileBehavior,
    ProfileCapabilities,
    ProfileEntities,
    ProfileMetadata,
    ProfileModes,
    WorkMode,
)


@pytest.fixture
def sungrow_like_profile():
    """
    Create a profile that mimics Sungrow's shared value issue:
    - zero_export, self_consumption, and idle all share "Self-consumption mode (default)"
    - Only idle has max_discharge_power: 10 in set_entities
    """
    return InverterProfile(
        metadata=ProfileMetadata(
            name="Test Sungrow-like",
            version="1.0.0",
            description="Test profile with shared mode values",
        ),
        capabilities=ProfileCapabilities(),
        entities=ProfileEntities(),
        modes=ProfileModes(
            export=WorkMode(value="Export mode"),
            zero_export=WorkMode(value="Self-consumption mode (default)"),
            self_consumption=WorkMode(value="Self-consumption mode (default)"),
            charge_from_grid=WorkMode(value="Forced mode"),
            idle=WorkMode(
                value="Self-consumption mode (default)",
                set_entities={"max_discharge_power": 10},
            ),
        ),
        behavior=ProfileBehavior(),
    )


class TestARC16ModeIntent:
    """Test ARC16 mode_intent field correctly disambiguates shared values."""

    def test_idle_mode_sets_mode_intent(self, sungrow_like_profile):
        """When SoC is at/below target, controller should set mode_intent='idle'."""
        from executor.config import ControllerConfig, InverterConfig

        controller = Controller(
            config=ControllerConfig(),
            inverter_config=InverterConfig(),
            profile=sungrow_like_profile,
        )

        # Slot with target SoC = 20
        slot = SlotPlan(
            charge_kw=0,
            discharge_kw=0,
            export_kw=0,
            soc_target=20,
        )

        # Current SoC at target (should trigger idle mode)
        state = SystemState(
            current_soc_percent=20,
        )

        decision = controller.decide(slot, state)

        # ARC16: mode_intent should be "idle" when at/below target
        assert decision.mode_intent == "idle", (
            f"Expected mode_intent='idle' when SoC at target, got '{decision.mode_intent}'"
        )

        # The work_mode value should be the shared value string
        assert decision.work_mode == "Self-consumption mode (default)", (
            f"Expected work_mode='Self-consumption mode (default)', got '{decision.work_mode}'"
        )

    def test_zero_export_mode_sets_mode_intent(self, sungrow_like_profile):
        """When SoC is above target, controller should set mode_intent='zero_export'."""
        from executor.config import ControllerConfig, InverterConfig

        controller = Controller(
            config=ControllerConfig(),
            inverter_config=InverterConfig(),
            profile=sungrow_like_profile,
        )

        slot = SlotPlan(
            charge_kw=0,
            discharge_kw=0,
            export_kw=0,
            soc_target=20,
        )

        # Current SoC above target (should trigger zero_export mode)
        state = SystemState(
            current_soc_percent=50,
        )

        decision = controller.decide(slot, state)

        # ARC16: mode_intent should be "zero_export" when above target
        assert decision.mode_intent == "zero_export", (
            f"Expected mode_intent='zero_export' when SoC above target, got '{decision.mode_intent}'"
        )

    def test_export_mode_sets_mode_intent(self, sungrow_like_profile):
        """When exporting, controller should set mode_intent='export'."""
        from executor.config import ControllerConfig, InverterConfig

        controller = Controller(
            config=ControllerConfig(),
            inverter_config=InverterConfig(),
            profile=sungrow_like_profile,
        )

        # Slot with export planned
        slot = SlotPlan(
            charge_kw=0,
            discharge_kw=0,
            export_kw=5,  # Export planned
            soc_target=20,
        )

        state = SystemState(
            current_soc_percent=50,
        )

        decision = controller.decide(slot, state)

        # ARC16: mode_intent should be "export" when exporting
        assert decision.mode_intent == "export", (
            f"Expected mode_intent='export' when exporting, got '{decision.mode_intent}'"
        )

    def test_charge_mode_sets_mode_intent(self, sungrow_like_profile):
        """When charging from grid, controller should set mode_intent='charge_from_grid'."""
        from executor.config import ControllerConfig, InverterConfig

        controller = Controller(
            config=ControllerConfig(),
            inverter_config=InverterConfig(),
            profile=sungrow_like_profile,
        )

        # Slot with charge planned
        slot = SlotPlan(
            charge_kw=3,  # Charging
            discharge_kw=0,
            export_kw=0,
            soc_target=20,
        )

        state = SystemState(
            current_soc_percent=50,
        )

        decision = controller.decide(slot, state)

        # ARC16: mode_intent should be "charge_from_grid" when charging
        assert decision.mode_intent == "charge_from_grid", (
            f"Expected mode_intent='charge_from_grid' when charging, got '{decision.mode_intent}'"
        )


class TestARC16BackwardCompatibility:
    """Test that mode_intent=None works for legacy flows without profiles."""

    def test_legacy_no_profile_mode_intent_is_none(self):
        """When no profile is used, mode_intent should be None (backward compatibility)."""
        from executor.config import ControllerConfig, InverterConfig

        controller = Controller(
            config=ControllerConfig(),
            inverter_config=InverterConfig(),
            profile=None,  # No profile - legacy mode
        )

        slot = SlotPlan(
            charge_kw=0,
            discharge_kw=0,
            export_kw=0,
            soc_target=20,
        )

        state = SystemState(
            current_soc_percent=50,
        )

        decision = controller.decide(slot, state)

        # ARC16: Without profile, mode_intent should be None for backward compatibility
        assert decision.mode_intent is None, (
            f"Expected mode_intent=None for legacy flow, got '{decision.mode_intent}'"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
