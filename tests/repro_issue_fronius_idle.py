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


def test_fronius_self_consumption_logic(executor_config, fronius_profile):
    """
    Reproduction of the "Block Discharge" issue.

    Scenario:
    - Slot Plan: Charge=0, Export=0 (Implies Self-Consumption)
    - SoC Target: 12%
    - Current SoC: 95%

    Expected Behavior:
    - Work Mode: "Auto" (Zero Export / Self Consumption)
    - Should NOT be "Block Discharging"
    """
    controller = Controller(
        config=executor_config.controller,
        inverter_config=executor_config.inverter,
        profile=fronius_profile,
    )

    # Slot with valid self-consumption parameters
    slot = SlotPlan(charge_kw=0.0, export_kw=0.0, soc_target=12, water_kw=0.0)

    state = SystemState(current_soc_percent=95.0, current_load_kw=2.0, current_pv_kw=0.0)

    decision = controller.decide(slot, state)

    print(f"Decision Work Mode: {decision.work_mode}")
    print(f"Decision Reason: {decision.reason}")

    # This assertion is expected to FAIL if the bug exists
    # If bug exists, it will be "Block Discharging"
    assert decision.work_mode == "Auto", (
        f"Expected 'Auto' for self-consumption, got '{decision.work_mode}'"
    )


if __name__ == "__main__":
    # verification helper
    pass
