from unittest.mock import MagicMock

import pytest

from executor.actions import ActionDispatcher, HAClient
from executor.config import ExecutorConfig
from executor.controller import ControllerDecision
from executor.profiles import InverterProfile


@pytest.fixture
def mock_ha():
    return MagicMock(spec=HAClient)


@pytest.fixture
def base_config():
    config = ExecutorConfig()
    config.has_battery = True
    config.inverter.work_mode_entity = "select.work_mode"
    config.inverter.max_charging_power_entity = "number.pv_charge_limit"
    config.inverter.grid_charging_entity = "switch.grid_charge"
    config.inverter.custom_entities = {"grid_charge_power_entity": "number.grid_charge_limit"}
    return config


@pytest.fixture
def fronius_profile():
    profile = MagicMock(spec=InverterProfile)

    profile.modes = MagicMock()
    profile.modes.charge_from_grid = MagicMock()
    profile.modes.charge_from_grid.value = "Charge from Grid"
    profile.modes.idle = MagicMock()
    profile.modes.idle.value = "Block Discharging"
    # Ensure other modes aren't accessed or returned as mocks
    profile.modes.export = None
    profile.modes.zero_export = None
    profile.modes.self_consumption = None
    profile.modes.force_discharge = None

    profile.metadata = MagicMock()
    profile.metadata.name = "fronius"

    profile.capabilities = MagicMock()
    profile.capabilities.grid_charging_control = True
    profile.capabilities.separate_grid_charging_switch = False
    profile.capabilities.supports_soc_target = True
    profile.capabilities.supports_grid_export_limit = True

    profile.entities = MagicMock()
    profile.entities.optional = {}
    profile.entities.required = {}

    profile.behavior = MagicMock()
    profile.behavior.requires_mode_settling = False
    profile.behavior.mode_settling_ms = 0

    return profile


@pytest.mark.asyncio
async def test_grid_charge_power_entity_routing(mock_ha, base_config, fronius_profile):
    """Verify that in grid charge mode, we write to the grid-specific entity."""
    dispatcher = ActionDispatcher(mock_ha, base_config, profile=fronius_profile)

    def get_state_se(entity_id):
        if entity_id == "select.work_mode":
            return "Charge from Grid"
        return "off"

    mock_ha.get_state_value.side_effect = get_state_se
    mock_ha.set_number.return_value = True
    mock_ha.set_select_option.return_value = True
    mock_ha.set_input_number.return_value = True

    decision = ControllerDecision(
        work_mode="Charge from Grid",
        grid_charging=True,
        charge_value=2000.0,
        discharge_value=5000.0,
        soc_target=10,
        water_temp=40,
        write_charge_current=True,
        write_discharge_current=True,
        control_unit="W",
    )

    await dispatcher.execute(decision)

    # Verify set_number was called for grid_charge_limit, NOT pv_charge_limit
    mock_ha.set_number.assert_any_call("number.grid_charge_limit", 2000.0)

    # Verify pv_charge_limit was NOT touched for setting power
    for call in mock_ha.set_number.call_args_list:
        assert call.args[0] != "number.pv_charge_limit"


@pytest.mark.asyncio
async def test_action_skipping_in_charge_mode(mock_ha, base_config, fronius_profile):
    """Verify that discharge and export limits are skipped in charge mode."""
    dispatcher = ActionDispatcher(mock_ha, base_config, profile=fronius_profile)

    base_config.inverter.max_discharging_power_entity = "number.discharge_limit"
    base_config.inverter.grid_max_export_power_entity = "number.export_limit"

    mock_ha.set_number.return_value = True
    mock_ha.set_select_option.return_value = True
    mock_ha.set_input_number.return_value = True

    decision = ControllerDecision(
        work_mode="Charge from Grid",
        grid_charging=True,
        charge_value=2000.0,
        discharge_value=5000.0,
        export_power_w=3000.0,
        soc_target=10,
        water_temp=40,
        write_charge_current=True,
        write_discharge_current=True,
        control_unit="W",
    )

    await dispatcher.execute(decision)

    # Verify discharge limit and export limit were NOT set
    for call in mock_ha.set_number.call_args_list:
        assert call.args[0] != "number.discharge_limit"
        assert call.args[0] != "number.export_limit"


@pytest.mark.asyncio
async def test_action_skipping_in_idle_mode(mock_ha, base_config, fronius_profile):
    """Verify that discharge and export limits are skipped in idle/hold mode."""
    dispatcher = ActionDispatcher(mock_ha, base_config, profile=fronius_profile)
    base_config.inverter.max_discharging_power_entity = "number.discharge_limit"

    mock_ha.set_number.return_value = True
    mock_ha.set_select_option.return_value = True
    mock_ha.set_input_number.return_value = True

    decision = ControllerDecision(
        work_mode="Block Discharging",
        grid_charging=False,
        charge_value=0.0,
        discharge_value=5000.0,
        soc_target=10,
        water_temp=40,
        write_charge_current=False,
        write_discharge_current=True,
        control_unit="W",
    )

    await dispatcher.execute(decision)

    # Verify discharge limit NOT set
    for call in mock_ha.set_number.call_args_list:
        assert call.args[0] != "number.discharge_limit"
