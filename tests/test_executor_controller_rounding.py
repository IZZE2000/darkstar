from executor.controller import Controller, ControllerConfig, InverterConfig, SlotPlan, SystemState
from executor.profiles import (
    InverterProfile,
    ProfileBehavior,
    ProfileCapabilities,
    ProfileEntities,
    ProfileMetadata,
    ProfileModes,
    WorkMode,
)


def test_charge_limit_rounding_grid_specific():
    # Setup profile with 10W grid rounding and 100W standard rounding
    behavior = ProfileBehavior(
        control_unit="W", round_step_w=100.0, grid_charge_round_step_w=10.0, min_charge_w=100.0
    )
    profile = InverterProfile(
        metadata=ProfileMetadata(name="test", version="1.0.0", description=""),
        capabilities=ProfileCapabilities(watts_based_control=True),
        entities=ProfileEntities(),
        modes=ProfileModes(zero_export=WorkMode(value="Zero")),
        behavior=behavior,
    )

    config = ControllerConfig(max_charge_w=5000)
    inverter_config = InverterConfig(control_unit="W")
    controller = Controller(config, inverter_config, profile=profile)

    # 1. Test standard rounding (though in our code is_grid_charge is currently same as charge_kw > 0)
    # Actually, in _calculate_charge_limit:
    # is_grid_charge = slot.charge_kw > 0

    # Test 126W -> should round to 130W (due to 10W step)
    slot = SlotPlan(charge_kw=0.126)  # 126W
    state = SystemState()
    val, write = controller._calculate_charge_limit(slot, state)
    assert val == 130.0

    # Test 124W -> should round to 120W
    slot = SlotPlan(charge_kw=0.124)  # 124W
    val, write = controller._calculate_charge_limit(slot, state)
    assert val == 120.0


def test_charge_limit_rounding_standard():
    # Setup profile with NO grid rounding and 100W standard rounding
    behavior = ProfileBehavior(
        control_unit="W", round_step_w=100.0, grid_charge_round_step_w=None, min_charge_w=100.0
    )
    profile = InverterProfile(
        metadata=ProfileMetadata(name="test", version="1.0.0", description=""),
        capabilities=ProfileCapabilities(watts_based_control=True),
        entities=ProfileEntities(),
        modes=ProfileModes(zero_export=WorkMode(value="Zero")),
        behavior=behavior,
    )

    config = ControllerConfig(max_charge_w=5000)
    inverter_config = InverterConfig(control_unit="W")
    controller = Controller(config, inverter_config, profile=profile)

    # Test 125W -> should round to 100W (due to 100W step)
    slot = SlotPlan(charge_kw=0.125)  # 125W
    state = SystemState()
    val, write = controller._calculate_charge_limit(slot, state)
    assert val == 100.0

    # Test 175W -> should round to 200W
    slot = SlotPlan(charge_kw=0.175)  # 175W
    val, write = controller._calculate_charge_limit(slot, state)
    assert val == 200.0
