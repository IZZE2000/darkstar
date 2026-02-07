import pytest

from executor.config import ExecutorConfig, InverterConfig
from executor.controller import Controller
from executor.override import SlotPlan, SystemState
from executor.profiles import load_profile


@pytest.fixture
def fronius_profile():
    return load_profile("fronius")


@pytest.fixture
def executor_config():
    inverter = InverterConfig(
        work_mode="select.fronius_battery_mode",
        max_charge_power="number.fronius_charge_power",
        max_discharge_power="number.fronius_discharge_power",
        control_unit="W",
    )
    return ExecutorConfig(enabled=True, inverter_profile="fronius", inverter=inverter)


def test_fronius_hold_logic(executor_config, fronius_profile):
    """
    Scenario:
    - Slot Plan: Charge=0, Export=0
    - SoC Target: 95%
    - Current SoC: 95%
    - Load: 2kW

    Expected Behavior:
    - Work Mode: "Block Discharging" (Idle)
    - Reason: Should prevent discharge because we are at/below target.
    """
    controller = Controller(
        config=executor_config.controller,
        inverter_config=executor_config.inverter,
        profile=fronius_profile,
    )

    # Slot with hold parameters (Target matches current)
    slot = SlotPlan(charge_kw=0.0, export_kw=0.0, soc_target=95, water_kw=0.0)

    # State exactly at target
    state = SystemState(current_soc_percent=95.0, current_load_kw=2.0, current_pv_kw=0.0)

    decision = controller.decide(slot, state)

    print(f"Decision Work Mode: {decision.work_mode}")
    print(f"Decision Reason: {decision.reason}")

    # This assertion is expected to FAIL currently (gets "Auto")
    assert decision.work_mode == "Block Discharging", (
        f"Expected 'Block Discharging' for hold at target, got '{decision.work_mode}'"
    )


def test_fronius_hold_logic_below_target(executor_config, fronius_profile):
    """
    Scenario:
    - Slot Plan: Charge=0, Export=0
    - SoC Target: 96%
    - Current SoC: 95%

    Expected Behavior:
    - Work Mode: "Block Discharging" or "Charge from Grid" (if configured?)
    - But with charge_kw=0, we won't active charge. We should at least NOT discharge.
    """
    controller = Controller(
        config=executor_config.controller,
        inverter_config=executor_config.inverter,
        profile=fronius_profile,
    )

    slot = SlotPlan(charge_kw=0.0, export_kw=0.0, soc_target=96, water_kw=0.0)
    state = SystemState(current_soc_percent=95.0, current_load_kw=2.0, current_pv_kw=0.0)

    decision = controller.decide(slot, state)

    # Should definitely block discharge
    assert decision.work_mode == "Block Discharging", (
        f"Expected 'Block Discharging' when below target, got '{decision.work_mode}'"
    )


def test_fronius_self_consumption_allowed(executor_config, fronius_profile):
    """
    verify regression of F47 is avoided.

    Scenario:
    - Slot Plan: Charge=0, Export=0
    - SoC Target: 50%
    - Current SoC: 95%

    Expected Behavior:
    - Work Mode: "Auto" (Self Consumption allowed because we have excess SoC)
    """
    controller = Controller(
        config=executor_config.controller,
        inverter_config=executor_config.inverter,
        profile=fronius_profile,
    )

    slot = SlotPlan(charge_kw=0.0, export_kw=0.0, soc_target=50, water_kw=0.0)
    state = SystemState(current_soc_percent=95.0, current_load_kw=2.0, current_pv_kw=0.0)

    decision = controller.decide(slot, state)

    assert decision.work_mode == "Auto", (
        f"Expected 'Auto' when above target, got '{decision.work_mode}'"
    )
