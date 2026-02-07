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
    """Verify that _set_grid_charging skips the switch call for Fronius."""
    dispatcher = ActionDispatcher(mock_ha, executor_config, profile=fronius_profile)

    # Enabled=True should still return success but skip the actual HA call
    result = await dispatcher._set_grid_charging(True)

    assert result.success is True
    assert result.skipped is True
    assert "Handled by work_mode" in result.message
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
