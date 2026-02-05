from unittest.mock import MagicMock

import pytest

from executor.actions import ActionDispatcher, HAClient
from executor.config import ExecutorConfig, InverterConfig
from executor.profiles import (
    InverterProfile,
    ProfileBehavior,
    ProfileCapabilities,
    ProfileEntities,
    ProfileMetadata,
    ProfileModes,
    WorkMode,
)


@pytest.mark.asyncio
async def test_composite_mode_execution():
    """Test that setting a mode with set_entities triggers multiple actions."""

    # 1. Setup Mock HA Client
    ha_client = MagicMock(spec=HAClient)
    ha_client.set_select_option = MagicMock(return_value=True)
    ha_client.get_state_value = MagicMock(return_value="OldMode")

    # 2. Setup Config
    config = ExecutorConfig(
        inverter=InverterConfig(
            work_mode_entity="select.master_mode",
            custom_entities={"ems_mode": "select.ems_mode", "charge_cmd": "select.charge_cmd"},
        )
    )

    # 3. Setup Profile with Composite Mode
    # "Force Charge" -> Set master mode to "InternalMode" AND set ems_mode="Forced", charge_cmd="Charge"
    profile = InverterProfile(
        metadata=ProfileMetadata(name="test", version="1.0.0", description="Test"),
        capabilities=ProfileCapabilities(),
        entities=ProfileEntities(),
        modes=ProfileModes(
            charge_from_grid=WorkMode(
                value="InternalMode", set_entities={"ems_mode": "Forced", "charge_cmd": "Charge"}
            )
        ),
        behavior=ProfileBehavior(),
    )

    # 4. Create Dispatcher
    dispatcher = ActionDispatcher(ha_client, config, profile=profile)

    # 5. Execute Action
    # We call _set_work_mode directly or via execute. Let's verify _set_work_mode.
    # Note: controller.decision.work_mode would be "InternalMode" (the value)
    result = await dispatcher._set_work_mode("InternalMode")

    # 6. Verify
    assert result.success is True

    # Verify primary mode execution
    ha_client.set_select_option.assert_any_call("select.master_mode", "InternalMode")

    # Verify auxiliary entities execution
    ha_client.set_select_option.assert_any_call("select.ems_mode", "Forced")
    ha_client.set_select_option.assert_any_call("select.charge_cmd", "Charge")
