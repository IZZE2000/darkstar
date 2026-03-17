## Why

The planner's MILP constraint for EV charging (`ev_energy[t] <= grid_import[t] + pv + epsilon`) only prevents EV energy from exceeding grid+solar, but does NOT prevent battery discharge in the same slot. The solver can schedule discharge to serve house load while EV charges from grid — a plan that looks valid mathematically but gets overridden by the executor's source isolation (which zeros ALL discharge during EV charging). This mismatch causes suboptimal planning: the planner "wastes" discharge capacity in slots where the executor will kill it, leading to higher actual grid import costs than planned.

## What Changes

- Add a Big-M constraint to the Kepler solver that forces `discharge[t] = 0` whenever `ev_charge[t] = 1`, matching the executor's source isolation behavior
- The existing grid-only constraint (`ev_energy <= grid_import + pv`) remains unchanged
- Unit tests to verify the solver cannot plan discharge and EV charging simultaneously

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `planner`: Add requirement that solver must not schedule battery discharge in any slot where EV charging is active

## Impact

- `planner/solver/kepler.py`: New MILP constraint added to the per-slot constraint loop
- `tests/planner/test_kepler_solver.py`: New test case(s) to verify mutual exclusion
- No API, config, or dependency changes
- No executor changes needed (it already enforces this at runtime)
