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


def test_get_missing_entities_with_custom_entities():
    """Test that get_missing_entities correctly finds entities in custom_entities."""
    entities = ProfileEntities(
        required={"work_mode": "select.work_mode", "ems_mode": "select.ems_mode"}
    )
    profile = InverterProfile(
        metadata=ProfileMetadata(name="test", version="1.0.0", description="Test"),
        capabilities=ProfileCapabilities(),
        entities=entities,
        modes=ProfileModes(),
        behavior=ProfileBehavior(),
    )

    # Case 1: Missing both
    config = {"executor": {"inverter": {"work_mode": None}}}
    missing = profile.get_missing_entities(config)
    assert "executor.inverter.work_mode" in missing
    assert "executor.inverter.ems_mode" in missing

    # Case 2: One in root, one in custom_entities
    config = {
        "executor": {
            "inverter": {
                "work_mode": "select.real_work_mode",
                "custom_entities": {"ems_mode": "select.real_ems_mode"},
            }
        }
    }
    missing = profile.get_missing_entities(config)
    assert missing == []


@pytest.mark.asyncio
async def test_apply_composite_entities_failure_reporting():
    """Test that _apply_composite_entities reports failures as ActionResults."""
    ha_client = MagicMock(spec=HAClient)

    # Config missing 'ems_mode' in custom_entities
    config = ExecutorConfig(
        inverter=InverterConfig(
            work_mode="select.work_mode",
            custom_entities={},  # Missing ems_mode
        )
    )

    profile = InverterProfile(
        metadata=ProfileMetadata(name="test", version="1.0.0", description="Test"),
        capabilities=ProfileCapabilities(),
        entities=ProfileEntities(required={"ems_mode": "select.ems_mode"}),
        modes=ProfileModes(
            charge_from_grid=WorkMode(value="Internal", set_entities={"ems_mode": "Forced"})
        ),
        behavior=ProfileBehavior(),
    )

    dispatcher = ActionDispatcher(ha_client, config, profile=profile)

    # Simulate _set_work_mode which calls _apply_composite_entities
    results = await dispatcher._set_work_mode("Internal", is_charging=True)

    # Should have a failure for ems_mode
    failure = next(
        (r for r in results if r.action_type == "composite_mode" and not r.success), None
    )
    assert failure is not None
    assert "not configured" in failure.message
    assert failure.error_details == "Missing composite entity mapping for 'ems_mode'"


def test_list_profiles_includes_entities():
    """Test that list_profiles returns entity metadata for UI."""
    from executor.profiles import list_profiles

    profiles = list_profiles()

    # Check sungrow profile
    sungrow = next((p for p in profiles if p["name"] == "sungrow"), None)
    assert sungrow is not None
    assert "entities" in sungrow
    assert "required" in sungrow["entities"]
    assert "ems_mode" in sungrow["entities"]["required"]
    assert "grid_max_export_power" in sungrow["entities"]["required"]
