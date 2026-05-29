## Why

The executor has a "Low SoC Export Prevention" override (priority 8.5) that blocks planned exports when real-time SoC drops below `low_soc_export_floor` (default 20%). This means Kepler plans exports that drive SoC below the floor, the executor catches it reactively, and the downstream schedule becomes suboptimal because it was built on the assumption those exports would happen. Since the planner replans every 30 minutes, SoC drift is minimal — the planner should simply never schedule exports that would violate this preference.

## What Changes

- Add `export_floor_soc_percent` to `KeplerConfig` (sourced from existing `executor.override.low_soc_export_floor`)
- Add a soft SoC constraint in the Kepler MILP: export is only allowed in slot `t` if `soc[t] >= export_floor_kwh`, enforced via binary variable with high penalty for violations
- Wire the config value through the adapter pipeline (`planner/solver/adapter.py`)
- **Remove** `LOW_SOC_EXPORT_PREVENTION` override type from the executor entirely (override logic, config, tests)
- Remove `low_soc_export_floor` from `executor.override` config section (move to `export` config section)

## Capabilities

### New Capabilities
- `export-floor-constraint`: SoC-gated export constraint in the Kepler MILP solver — export is only allowed when projected SoC is above a configurable floor, enforced as a soft constraint with high penalty

### Modified Capabilities
- `planner`: New `export_floor_soc_percent` field on `KeplerConfig`, new binary variable and constraints in the solver
- `executor`: Remove `LOW_SOC_EXPORT_PREVENTION` override type and associated logic/config

## Impact

- **`planner/solver/types.py`**: Add `export_floor_soc_percent` to `KeplerConfig`
- **`planner/solver/kepler.py`**: Add `is_exporting[t]` binary variable, export-floor SoC constraint, and violation slack variable with penalty
- **`planner/solver/adapter.py`**: Pass `export_floor_soc_percent` from config to `KeplerConfig`
- **`executor/override.py`**: Remove `LOW_SOC_EXPORT_PREVENTION` override branch and `low_soc_threshold` parameter
- **`executor/engine.py`**: Remove `low_soc_threshold` from override config construction
- **`config.default.yaml`**: Move `low_soc_export_floor` from `executor.override` to `planner` section
- **Tests**: Update planner solver tests, remove executor override tests for this case
- **No breaking API changes** — config migration handles the move
