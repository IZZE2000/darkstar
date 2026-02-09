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
            work_mode="select.master_mode",
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
    results = await dispatcher._set_work_mode("InternalMode", is_charging=True)

    # 6. Verify
    assert any(r.action_type == "work_mode" and r.success for r in results)
    assert any(
        r.action_type == "composite_mode" and r.entity_id == "select.ems_mode" for r in results
    )
    assert any(
        r.action_type == "composite_mode" and r.entity_id == "select.charge_cmd" for r in results
    )

    # Verify primary mode execution
    ha_client.set_select_option.assert_any_call("select.master_mode", "InternalMode")

    # Verify auxiliary entities execution
    ha_client.set_select_option.assert_any_call("select.ems_mode", "Forced")
    ha_client.set_select_option.assert_any_call("select.charge_cmd", "Charge")


@pytest.mark.asyncio
async def test_forced_power_sync():
    """Test that power limits are synced to forced_power_entity in forced modes."""

    # 1. Setup Mock HA Client
    ha_client = MagicMock(spec=HAClient)
    ha_client.set_number = MagicMock(return_value=True)
    # Mock get_state_value to return the "InternalMode" which we define as forced
    ha_client.get_state_value = MagicMock(return_value="InternalMode")

    # 2. Setup Config
    config = ExecutorConfig(
        inverter=InverterConfig(
            work_mode="select.master_mode",
            max_charge_power="number.max_charge_power",
            custom_entities={"forced_power_entity": "number.forced_power_limit"},
        )
    )

    # 3. Setup Profile
    profile = InverterProfile(
        metadata=ProfileMetadata(name="test", version="1.0.0", description="Test"),
        capabilities=ProfileCapabilities(),
        entities=ProfileEntities(optional={"forced_power_entity": "forced_power_limit"}),
        modes=ProfileModes(charge_from_grid=WorkMode(value="InternalMode")),
        behavior=ProfileBehavior(),
    )

    # 4. Create Dispatcher
    dispatcher = ActionDispatcher(ha_client, config, profile=profile)

    # 5. Execute Charge Limit Action
    result = await dispatcher._set_charge_limit(2500.0, "W")

    # 6. Verify
    assert result.success is True
    # Verify standard limit
    ha_client.set_number.assert_any_call("number.max_charge_power", 2500.0)
    # Verify sync to forced entity
    ha_client.set_number.assert_any_call("number.forced_power_limit", 2500.0)
