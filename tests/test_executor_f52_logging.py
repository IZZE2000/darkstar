from unittest.mock import AsyncMock, MagicMock

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


@pytest.fixture
def mock_ha_client():
    client = MagicMock(spec=HAClient)
    client.get_state_value.return_value = "Initial"
    client.set_select_option.return_value = True
    client.set_number.return_value = True
    client.set_switch.return_value = True
    return client


@pytest.fixture
def executor_config():
    return ExecutorConfig(
        inverter=InverterConfig(
            work_mode="select.work_mode",
            custom_entities={
                "aux_entity": "number.aux_entity",
                "switch_entity": "switch.aux_switch",
            },
        )
    )


@pytest.fixture
def composite_profile():
    return InverterProfile(
        metadata=ProfileMetadata(name="test", version="1.0.0", description="Test"),
        capabilities=ProfileCapabilities(),
        entities=ProfileEntities(),
        modes=ProfileModes(
            charge_from_grid=WorkMode(
                value="ForcedCharge", set_entities={"aux_entity": 100, "switch_entity": True}
            )
        ),
        behavior=ProfileBehavior(requires_mode_settling=False),
    )


@pytest.mark.asyncio
async def test_composite_mode_logging_full_execution(
    mock_ha_client, executor_config, composite_profile
):
    """Test that all entity changes in composite mode are logged."""
    dispatcher = ActionDispatcher(mock_ha_client, executor_config, profile=composite_profile)

    # Mock verify_action to return success
    dispatcher._verify_action = AsyncMock(
        side_effect=[("ForcedCharge", True), (100.0, True), (True, True)]
    )

    results = await dispatcher._set_work_mode("ForcedCharge", is_charging=True)

    assert len(results) == 3
    assert results[0].action_type == "work_mode"
    assert results[0].entity_id == "select.work_mode"

    assert results[1].action_type == "composite_mode"
    assert results[1].entity_id == "number.aux_entity"
    assert results[1].new_value == 100
    assert results[1].skipped is False

    assert results[2].action_type == "composite_mode"
    assert results[2].entity_id == "switch.aux_switch"
    assert results[2].new_value is True
    assert results[2].skipped is False


@pytest.mark.asyncio
async def test_composite_mode_idempotent_skip(mock_ha_client, executor_config, composite_profile):
    """Test that auxiliary entity changes are skipped if already at target AND mode unchanged."""
    # REV F56 Phase 2: Context-aware composite skip - entities are re-asserted on mode transitions
    # State lookup values in order of access:
    # 1. Primary mode (ForcedCharge) - same as target, so mode_changed=False
    # 2. Aux 1 current (100) -> Skip (already at target)
    # 3. Aux 2 current (True) -> Skip (already at target)
    mock_ha_client.get_state_value.side_effect = ["ForcedCharge", "100", "True"]

    dispatcher = ActionDispatcher(mock_ha_client, executor_config, profile=composite_profile)

    # Mock verify_action for all entities (mode unchanged, so aux entities are skipped)
    dispatcher._verify_action = AsyncMock(return_value=("ForcedCharge", True))

    results = await dispatcher._set_work_mode("ForcedCharge", is_charging=True)

    assert len(results) == 3
    assert results[0].action_type == "work_mode"
    assert results[0].skipped is True  # Mode already at target

    assert results[1].action_type == "composite_mode"
    assert results[1].entity_id == "number.aux_entity"
    assert results[1].skipped is True  # Value already at target AND mode unchanged

    assert results[2].action_type == "composite_mode"
    assert results[2].entity_id == "switch.aux_switch"
    assert results[2].skipped is True  # Value already at target AND mode unchanged


@pytest.mark.asyncio
async def test_composite_mode_shadow_mode(mock_ha_client, executor_config, composite_profile):
    """Test that shadow mode is respected for auxiliary entities."""
    dispatcher = ActionDispatcher(
        mock_ha_client, executor_config, profile=composite_profile, shadow_mode=True
    )

    results = await dispatcher._set_work_mode("ForcedCharge", is_charging=True)

    assert len(results) == 3
    for r in results:
        assert r.skipped is True
        assert "[SHADOW]" in r.message

    mock_ha_client.set_select_option.assert_not_called()
    mock_ha_client.set_number.assert_not_called()
    mock_ha_client.set_switch.assert_not_called()
