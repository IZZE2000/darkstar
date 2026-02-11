from unittest.mock import MagicMock

import pytest

from executor.actions import ActionDispatcher, HAClient
from executor.config import ExecutorConfig, InverterConfig
from executor.controller import Controller
from executor.override import SlotPlan, SystemState
from executor.profiles import load_profile


@pytest.fixture
def fronius_profile():
    return load_profile("fronius")


@pytest.fixture
def mock_ha():
    client = MagicMock(spec=HAClient)
    client.get_state_value.return_value = "Auto"
    return client


@pytest.fixture
def executor_config():
    inverter = InverterConfig(
        work_mode="select.fronius_battery_mode",
        max_charge_power="number.fronius_charge_power",
        max_discharge_power="number.fronius_discharge_power",
        control_unit="W",
    )
    return ExecutorConfig(enabled=True, inverter_profile="fronius", inverter=inverter)


def test_fronius_profile_parsing(fronius_profile):
    """Verify that fronius.yaml is parsed correctly with expected capabilities."""
    assert fronius_profile.metadata.name == "fronius"
    assert fronius_profile.capabilities.watts_based_control is True
    assert fronius_profile.capabilities.separate_grid_charging_switch is False
    assert fronius_profile.behavior.control_unit == "W"
    assert fronius_profile.modes.export.value == "Discharge to Grid"
    assert fronius_profile.modes.charge_from_grid.requires_grid_charging is True


@pytest.mark.asyncio
async def test_fronius_grid_charging_skipped(mock_ha, executor_config, fronius_profile):
    """Verify that _set_grid_charging returns None for Fronius (mode-based charging)."""
    dispatcher = ActionDispatcher(mock_ha, executor_config, profile=fronius_profile)

    # For Fronius (no separate grid charging switch), should return None (silent skip)
    result = await dispatcher._set_grid_charging(True)

    assert result is None, "Fronius should return None for grid_charging (mode-based)"
    # Verify HA set_switch was NEVER called
    mock_ha.set_switch.assert_not_called()


def test_fronius_controller_decisions(executor_config, fronius_profile):
    """Verify that Controller makes correct mode decisions for Fronius."""
    controller = Controller(
        config=executor_config.controller,
        inverter_config=executor_config.inverter,
        profile=fronius_profile,
    )

    # Case 1: Grid Charging Planned
    slot = SlotPlan(charge_kw=3.0, export_kw=0.0, soc_target=80)
    state = SystemState(current_soc_percent=50.0)
    decision = controller.decide(slot, state)

    assert decision.work_mode == "Charge from Grid"
    assert decision.grid_charging is True  # Because requires_grid_charging is True in profile
    assert decision.charge_value == 3000.0
    assert decision.control_unit == "W"

    # Case 2: Export Planned
    slot = SlotPlan(charge_kw=0.0, export_kw=5.0, soc_target=10)
    decision = controller.decide(slot, state)

    assert decision.work_mode == "Discharge to Grid"
    assert decision.discharge_value == executor_config.controller.max_discharge_w


@pytest.mark.asyncio
async def test_fronius_watt_limit_execution(mock_ha, executor_config, fronius_profile):
    """Verify that _set_charge_limit uses Watts for Fronius."""
    dispatcher = ActionDispatcher(mock_ha, executor_config, profile=fronius_profile)

    await dispatcher._set_charge_limit(2500.0, "W")

    # Verify HA set_number was called with Watts entity
    mock_ha.set_number.assert_called_with("number.fronius_charge_power", 2500.0)


@pytest.mark.asyncio
async def test_fronius_auto_mode_skips_extraneous_entities(
    mock_ha, executor_config, fronius_profile
):
    """REV F53/F54: Verify Auto mode only writes work_mode, skipping grid_charging, discharge_limit, max_export_power, and soc_target.

    Note: Fronius does NOT support soc_target (uses minimum_reserve instead), so it's silently skipped per F54 Phase 3.
    """
    from executor.controller import ControllerDecision

    # REV F54: Fronius profile has supports_soc_target=false, so soc_target returns None (silent skip)
    # We intentionally DON'T add soc_target entity to test the silent skip behavior

    # Mock current state - return different value from target so work_mode gets executed
    def mock_get_state_value(entity_id):
        # The entity_id is the full HA entity path (e.g., "select.fronius_battery_mode")
        # Return "Discharge to Grid" for work_mode entity to trigger a change to "Auto"
        if entity_id == executor_config.inverter.work_mode:
            return "Discharge to Grid"
        return "Auto"

    mock_ha.get_state_value.side_effect = mock_get_state_value
    mock_ha.set_select_option.return_value = True
    mock_ha.set_input_number.return_value = True

    dispatcher = ActionDispatcher(mock_ha, executor_config, profile=fronius_profile)

    # Create a decision for Auto mode (self_consumption)
    decision = ControllerDecision(
        work_mode="Auto",  # Fronius self_consumption and zero_export both use "Auto"
        grid_charging=False,
        charge_value=0,
        discharge_value=100,
        soc_target=50,  # This will be silently skipped because Fronius doesn't support soc_target
        water_temp=40,
        export_power_w=5000.0,
        write_charge_current=False,
        write_discharge_current=True,  # Would normally write, but should be skipped in Auto mode
    )

    results = await dispatcher.execute(decision)

    # Collect action types that were executed (not skipped)
    executed_actions = [r.action_type for r in results if r and not r.skipped]
    skipped_actions = [r.action_type for r in results if r and r.skipped]

    # In Auto mode, only work_mode should be executed
    assert "work_mode" in executed_actions, (
        f"work_mode should be executed in Auto mode. Results: {[(r.action_type, r.skipped, r.message) for r in results]}"
    )

    # REV F54: soc_target returns None for profiles that don't support it (silent skip)
    # It won't appear in results at all (not even as skipped)
    soc_target_results = [r for r in results if r and r.action_type == "soc_target"]
    assert len(soc_target_results) == 0, (
        "soc_target should be silently skipped (returns None) for Fronius (supports_soc_target=false)"
    )

    # These should be skipped in Auto mode per profile flags
    assert "grid_charging" in skipped_actions or "grid_charging" not in executed_actions, (
        "grid_charging should be skipped in Auto mode (separate_grid_charging_switch=false)"
    )
    assert "discharge_limit" in skipped_actions or "discharge_limit" not in executed_actions, (
        "discharge_limit should be skipped in Auto mode (skip_discharge_limit=true)"
    )
    assert "max_export_power" in skipped_actions or "max_export_power" not in executed_actions, (
        "max_export_power should be skipped in Auto mode (skip_export_power=true)"
    )

    # Verify the HA calls that should NOT be made in Auto mode
    mock_ha.set_switch.assert_not_called()  # grid_charging
    # discharge_limit and max_export_power would call set_number, but should be skipped


def test_fronius_reason_uses_profile_descriptions(executor_config, fronius_profile):
    """REV F53: Verify that controller decision reasons use profile mode descriptions instead of hardcoded labels."""
    controller = Controller(
        config=executor_config.controller,
        inverter_config=executor_config.inverter,
        profile=fronius_profile,
    )

    # Case 1: Idle mode (zero_export) - should use profile description
    # When no activities planned, controller uses zero_export mode
    slot = SlotPlan(charge_kw=0.0, export_kw=0.0, soc_target=50)
    state = SystemState(current_soc_percent=80.0)
    decision = controller.decide(slot, state)

    assert decision.work_mode == "Auto"  # zero_export mode value
    # The reason should contain the zero_export profile description, not hardcoded "Zero-Export"
    assert fronius_profile.modes.zero_export.description in decision.reason, (
        f"Expected profile description '{fronius_profile.modes.zero_export.description}' in reason, got: {decision.reason}"
    )
    assert "Zero-Export" not in decision.reason, (
        f"Reason should NOT contain hardcoded 'Zero-Export', got: {decision.reason}"
    )

    # Case 2: Export mode - should use profile description
    slot = SlotPlan(charge_kw=0.0, export_kw=5.0, soc_target=50)
    decision = controller.decide(slot, state)

    assert decision.work_mode == "Discharge to Grid"
    # The reason should contain the profile description
    assert fronius_profile.modes.export.description in decision.reason, (
        f"Expected profile description '{fronius_profile.modes.export.description}' in reason, got: {decision.reason}"
    )
