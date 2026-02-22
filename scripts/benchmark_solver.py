#!/usr/bin/env python3
"""
MILP Solver Benchmark - Direct Test
"""

import sys
import time
from pathlib import Path
from typing import Any, cast

sys.path.append(str(Path(__file__).parent.parent.resolve()))

import pulp


def create_simple_milp(n_slots: int = 100) -> Any:
    """Create a simplified version of the Kepler problem."""
    prob: Any = None  # type: ignore[assignment]
    prob = pulp.LpProblem("BenchmarkMILP", pulp.LpMinimize)

    # Variables
    charge: dict[int, Any] = pulp.LpVariable.dicts("charge", range(n_slots), lowBound=0)  # type: ignore[attr-defined]
    discharge: dict[int, Any] = pulp.LpVariable.dicts("discharge", range(n_slots), lowBound=0)  # type: ignore[attr-defined]
    soc: dict[int, Any] = pulp.LpVariable.dicts("soc", range(n_slots + 1), lowBound=0, upBound=20)  # type: ignore[attr-defined]
    water: dict[int, Any] = pulp.LpVariable.dicts("water", range(n_slots), cat="Binary")  # type: ignore[attr-defined]

    # Initial SoC
    prob += soc[0] == 10  # type: ignore[partially-known]

    # Constraints for each slot
    for t in range(n_slots):
        # Battery dynamics
        prob += soc[t + 1] == soc[t] + charge[t] * 0.95 - discharge[t]  # type: ignore[partially-known]
        # Power limits
        prob += charge[t] <= 5  # type: ignore[partially-known]
        prob += discharge[t] <= 5  # type: ignore[partially-known]

    # Water heating constraint
    prob += pulp.lpSum(water) >= 8  # type: ignore[partially-known]

    # Objective: minimize cost
    prob += pulp.lpSum(charge[t] * (1.0 + t * 0.01) - discharge[t] * 0.5 for t in range(n_slots))  # type: ignore[partially-known]

    return prob  # type: ignore[partially-known]


def main() -> None:
    print("=" * 60)
    print("MILP SOLVER BENCHMARK (Direct)")
    print("=" * 60)

    n_slots = 100
    print(f"Creating MILP problem with {n_slots} slots...")

    # Test each solver
    solvers: list[tuple[str, Any]] = [
        ("CBC", pulp.PULP_CBC_CMD(msg=False)),  # type: ignore[attr-defined]
    ]

    # Try GLPK
    try:
        glpk: Any = pulp.GLPK_CMD(msg=False)  # type: ignore[attr-defined]
        solvers.insert(0, cast("tuple[str, Any]", ("GLPK", glpk)))
    except Exception as e:
        print(f"GLPK not available: {e}")

    # Try HiGHS
    try:
        highs: Any = pulp.HiGHS_CMD(msg=False)  # type: ignore[attr-defined]
        solvers.append(cast("tuple[str, Any]", ("HiGHS", highs)))
    except Exception as e:
        print(f"HiGHS not available: {e}")

    for name, solver in solvers:
        print(f"\nTesting {name}...")
        prob = create_simple_milp(n_slots)

        try:
            start = time.time()
            prob.solve(solver)  # type: ignore[attr-defined]
            elapsed = time.time() - start

            status = pulp.LpStatus[prob.status]  # type: ignore[index]
            print(f"  {name}: {elapsed:.2f}s (status={status})")
        except Exception as e:
            print(f"  {name}: FAILED - {e}")

    print("\n" + "=" * 60)
    print("If a solver is much faster, we can switch to it in Kepler.")
    print("=" * 60)


if __name__ == "__main__":
    main()
