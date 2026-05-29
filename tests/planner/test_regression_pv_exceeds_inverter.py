"""Regression test: PV forecast exceeds inverter AC capacity causing infeasibility."""
from datetime import datetime, timedelta

from planner.solver.kepler import KeplerSolver
from planner.solver.types import KeplerConfig, KeplerInput, KeplerInputSlot


def test_pv_exceeds_inverter_ac_capacity_returns_optimal():
    """When pv_kwh > inverter_ac_kwh, solver should return Optimal with discharge=0.

    Before fix: LP infeasible (discharge + pv <= inverter_ac becomes discharge <= negative).
    After fix: discharge <= max(0, inverter_ac - pv) = 0, which is satisfiable.
    """
    start = datetime(2025, 6, 1, 12, 0)
    slots = []

    for i in range(4):
        slots.append(
            KeplerInputSlot(
                start_time=start + timedelta(minutes=15 * i),
                end_time=start + timedelta(minutes=15 * (i + 1)),
                load_kwh=0.5,
                pv_kwh=2.1177,  # > 2.0 kWh inverter limit (8.47 kW average)
                import_price_sek_kwh=1.0,
                export_price_sek_kwh=0.4,
            )
        )

    input_data = KeplerInput(slots=slots, initial_soc_kwh=5.0)

    config = KeplerConfig(
        capacity_kwh=10.0,
        max_charge_power_kw=5.0,
        max_discharge_power_kw=5.0,
        charge_efficiency=0.95,
        discharge_efficiency=0.95,
        min_soc_percent=10,
        max_soc_percent=100,
        wear_cost_sek_per_kwh=0.01,
        max_inverter_ac_kw=8.0,  # 8kW * 0.25h = 2.0 kWh per slot
        enable_export=True,
    )

    solver = KeplerSolver()
    result = solver.solve(input_data, config)

    assert result.is_optimal, f"Expected Optimal, got {result.status_msg}"

    for s in result.slots:
        assert s.discharge_kwh <= 0.001, (
            f"Expected discharge=0 when PV exceeds inverter capacity, got {s.discharge_kwh}"
        )
