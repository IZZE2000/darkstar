from unittest.mock import MagicMock

import pytest

from executor.actions import ActionDispatcher, HAClient
from executor.config import ExecutorConfig
from executor.controller import ControllerDecision
from executor.profiles import EntityDefinition, InverterProfile, ModeAction, ModeDefinition


@pytest.fixture
def mock_ha():
    return MagicMock(spec=HAClient)


@pytest.fixture
def base_config():
    config = ExecutorConfig()
    config.has_battery = True
    config.inverter.work_mode = "select.work_mode"
    config.inverter.max_charge_power = "number.pv_charge_limit"
    config.inverter.grid_charging_enable = "switch.grid_charge"
    config.inverter.grid_charge_power = "number.grid_charge_limit"
    return config


@pytest.fixture
def fronius_profile():
    """Create a v2-style Fronius profile mock."""
    profile = MagicMock(spec=InverterProfile)

    # v2: modes is a dict of ModeDefinition
    charge_mode = ModeDefinition(
        description="Charge from grid",
        actions=[
            ModeAction(entity="work_mode", value="Charge from Grid"),
            ModeAction(entity="grid_charging_enable", value=True),
        ],
    )
    idle_mode = ModeDefinition(
        description="Block discharging",
        actions=[
            ModeAction(entity="work_mode", value="Block Discharging"),
        ],
    )

    profile.modes = {
        "charge": charge_mode,
        "idle": idle_mode,
    }

    profile.metadata = MagicMock()
    profile.metadata.name = "fronius"

    # v2: entities is a dict of EntityDefinition
    profile.entities = {
        "work_mode": EntityDefinition(
            default_entity="select.work_mode",
            domain="select",
            category="system",
            description="Work mode select",
            required=True,
        ),
        "grid_charging_enable": EntityDefinition(
            default_entity="switch.grid_charge",
            domain="switch",
            category="system",
            description="Grid charging switch",
            required=False,
        ),
    }

    profile.behavior = MagicMock()
    profile.behavior.requires_mode_settling = False
    profile.behavior.mode_settling_ms = 0

    return profile


@pytest.mark.asyncio
async def test_action_skipping_in_charge_mode(mock_ha, base_config, fronius_profile):
    """Verify that discharge and export limits are skipped in charge mode."""
    dispatcher = ActionDispatcher(mock_ha, base_config, profile=fronius_profile)

    base_config.inverter.max_discharge_power = "number.discharge_limit"
    base_config.inverter.grid_max_export_power = "number.export_limit"

    mock_ha.set_number.return_value = True
    mock_ha.set_select_option.return_value = True
    mock_ha.set_input_number.return_value = True

    # v2: Use mode_intent
    decision = ControllerDecision(
        mode_intent="charge",
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
    base_config.inverter.max_discharge_power = "number.discharge_limit"

    mock_ha.set_number.return_value = True
    mock_ha.set_select_option.return_value = True
    mock_ha.set_input_number.return_value = True

    # v2: Use mode_intent "idle" instead of work_mode "Block Discharging"
    decision = ControllerDecision(
        mode_intent="idle",
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
