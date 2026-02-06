from datetime import datetime, timedelta

import pytest

from planner.solver.kepler import KeplerSolver
from planner.solver.types import KeplerConfig, KeplerInput, KeplerInputSlot


def test_kepler_solver_basic():
    # Create a simple 2-slot scenario
    start = datetime(2025, 1, 1, 12, 0)
    slots = []
    for i in range(2):
        s = start + timedelta(minutes=15 * i)
        e = s + timedelta(minutes=15)
        slots.append(
            KeplerInputSlot(
                start_time=s,
                end_time=e,
                load_kwh=1.0,  # 1 kWh load
                pv_kwh=0.0,
                import_price_sek_kwh=1.0,  # Expensive import
                export_price_sek_kwh=0.0,  # Worthless export
            )
        )

    # Initial battery: 5 kWh (50% of 10kWh)
    input_data = KeplerInput(slots=slots, initial_soc_kwh=5.0)

    config = KeplerConfig(
        capacity_kwh=10.0,
        max_charge_power_kw=5.0,
        max_discharge_power_kw=5.0,
        charge_efficiency=1.0,
        discharge_efficiency=1.0,
        min_soc_percent=0.0,
        max_soc_percent=100.0,
        wear_cost_sek_per_kwh=0.01,  # Small wear cost to prevent free dumping
        target_soc_kwh=0.0,  # Allow depletion
    )

    solver = KeplerSolver()
    result = solver.solve(input_data, config)

    assert result.is_optimal
    assert len(result.slots) == 2

    # Check that it discharged to cover load (since import is expensive)
    # Total load = 2 kWh. Initial battery = 5 kWh.
    # Should discharge 2 kWh.
    total_discharge = sum(s.discharge_kwh for s in result.slots)
    total_import = sum(s.grid_import_kwh for s in result.slots)

    print(f"Total Discharge: {total_discharge}")
    print(f"Total Import: {total_import}")

    assert total_discharge == pytest.approx(2.0, abs=0.01)

    # Check that import is 0
    assert total_import == pytest.approx(0.0, abs=0.01)


def test_kepler_solver_arbitrage():
    # 2 slots: Cheap import, then Expensive export
    start = datetime(2025, 1, 1, 12, 0)
    slots = []

    # Slot 0: Cheap import (0.1 SEK), High export (0.05 SEK) - Charge
    slots.append(
        KeplerInputSlot(
            start_time=start,
            end_time=start + timedelta(minutes=15),
            load_kwh=0.0,
            pv_kwh=0.0,
            import_price_sek_kwh=0.1,
            export_price_sek_kwh=0.05,
        )
    )

    # Slot 1: Expensive import (2.0 SEK), High export (1.5 SEK) - Discharge/Export
    slots.append(
        KeplerInputSlot(
            start_time=start + timedelta(minutes=15),
            end_time=start + timedelta(minutes=30),
            load_kwh=0.0,
            pv_kwh=0.0,
            import_price_sek_kwh=2.0,
            export_price_sek_kwh=1.5,
        )
    )

    input_data = KeplerInput(slots=slots, initial_soc_kwh=0.0)  # Empty battery

    config = KeplerConfig(
        capacity_kwh=10.0,
        max_charge_power_kw=4.0,  # 1 kWh per 15 min
        max_discharge_power_kw=4.0,
        charge_efficiency=1.0,
        discharge_efficiency=1.0,
        min_soc_percent=0.0,
        max_soc_percent=100.0,
        wear_cost_sek_per_kwh=0.0,
    )

    solver = KeplerSolver()
    result = solver.solve(input_data, config)

    assert result.is_optimal

    # Slot 0: Should charge max (1 kWh)
    assert result.slots[0].charge_kwh == pytest.approx(1.0, abs=0.01)


def test_kepler_ev_solar_charging():
    # Scenario: High PV, High Grid Prices. EV should charge from PV.
    start = datetime(2025, 1, 1, 12, 0)
    slots = []
    # 1 hour (4 slots)
    for i in range(4):
        slots.append(
            KeplerInputSlot(
                start_time=start + timedelta(minutes=15 * i),
                end_time=start + timedelta(minutes=15 * (i + 1)),
                load_kwh=1.0,  # 1kWh load
                pv_kwh=10.0,  # 10kWh PV (very sunny)
                import_price_sek_kwh=5.0,  # Very expensive grid
                export_price_sek_kwh=0.0,  # No export value
            )
        )

    input_data = KeplerInput(slots=slots, initial_soc_kwh=5.0)

    config = KeplerConfig(
        capacity_kwh=10.0,
        max_charge_power_kw=5.0,
        max_discharge_power_kw=5.0,
        charge_efficiency=1.0,
        discharge_efficiency=1.0,
        min_soc_percent=0.0,
        max_soc_percent=100.0,
        wear_cost_sek_per_kwh=0.01,
        curtailment_penalty_sek=1.0,  # Encourage using solar
        max_export_power_kw=0.0,  # Force solar into battery/EV
        enable_export=False,
        # EV Settings
        ev_charging_enabled=True,
        ev_plugged_in=True,
        ev_max_power_kw=10.0,  # 2.5kWh per slot
        ev_battery_capacity_kwh=100.0,
        ev_current_soc_percent=50.0,
        ev_target_soc_percent=60.0,  # Need 10kWh total
    )

    solver = KeplerSolver()
    result = solver.solve(input_data, config)

    assert result.is_optimal
    # Total PV = 40kWh. Total Load = 4kWh. Need 10kWh for EV.
    # Total charge into car should be 10kWh.
    total_ev_charge = sum(s.ev_charge_kw * 0.25 for s in result.slots)
    assert total_ev_charge == pytest.approx(10.0, abs=0.1)

    # Grid import should be 0 because we have plenty of solar
    total_import = sum(s.grid_import_kwh for s in result.slots)
    assert total_import == pytest.approx(0.0, abs=0.01)

    # Battery should be charging from solar too
    assert result.slots[0].soc_kwh > 5.0


def test_kepler_ev_no_battery_drain():
    # Scenario: Zero PV, High Grid Prices, Battery Full.
    # EV should NOT charge from battery even if target is not met (soft constraint penalty vs safety constraint).
    start = datetime(2025, 1, 1, 12, 0)
    slots = []
    for i in range(4):
        slots.append(
            KeplerInputSlot(
                start_time=start + timedelta(minutes=15 * i),
                end_time=start + timedelta(minutes=15 * (i + 1)),
                load_kwh=0.0,
                pv_kwh=0.0,
                import_price_sek_kwh=10.0,  # Extremely expensive
                export_price_sek_kwh=0.0,  # No incentive to export
            )
        )

    # Battery is full
    input_data = KeplerInput(slots=slots, initial_soc_kwh=10.0)

    config = KeplerConfig(
        capacity_kwh=10.0,
        max_charge_power_kw=5.0,
        max_discharge_power_kw=5.0,
        charge_efficiency=1.0,
        discharge_efficiency=1.0,
        min_soc_percent=0.0,
        max_soc_percent=100.0,
        target_soc_kwh=10.0,  # Want to keep battery full!
        # EV Settings
        ev_charging_enabled=True,
        ev_plugged_in=True,
        ev_max_power_kw=10.0,
        ev_battery_capacity_kwh=100.0,
        ev_current_soc_percent=10.0,
        ev_target_soc_percent=80.0,  # High urgency
        ev_penalty_emergency=5000.0,  # High penalty for not charging
        wear_cost_sek_per_kwh=0.01,
    )

    solver = KeplerSolver()
    result = solver.solve(input_data, config)

    assert result.is_optimal

    # EV should charge 0 because it can't use battery and grid is too expensive
    # (wait, if ev_penalty_emergency is 5000 it might charge from grid).
    # But it DEFINITELY cannot charge from battery.
    # If EV charges, it MUST import.
    for s in result.slots:
        if s.ev_charge_kw > 0:
            assert s.grid_import_kwh >= s.ev_charge_kw * 0.25 - 0.002

    # And total discharge cannot be more than load (0 in this case)
    total_discharge = sum(s.discharge_kwh for s in result.slots)
    assert total_discharge == pytest.approx(0.0, abs=0.01)
