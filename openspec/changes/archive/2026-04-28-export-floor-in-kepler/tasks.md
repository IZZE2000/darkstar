## 1. KeplerConfig & Solver

- [x] 1.1 Add `export_floor_soc_percent: float | None = None` to `KeplerConfig` in `planner/solver/types.py`
- [x] 1.2 Add `is_exporting[t]` binary variable, `export_floor_violation[t]` slack, and big-M constraints in `planner/solver/kepler.py` — gated on `enable_export and export_floor_soc_percent is not None`
- [x] 1.3 Add `EXPORT_FLOOR_PENALTY = 1000.0` penalty for `export_floor_violation` in the objective function

## 2. Config & Adapter

- [x] 2.1 Wire `export_floor_soc_percent` from `planner_config.get("export", {}).get("export_floor_soc_percent")` through `planner/solver/adapter.py` to `KeplerConfig`
- [x] 2.2 Add `export_floor_soc_percent: 20` to the `export` section in `config.default.yaml` (alongside `enable_export`)
- [x] 2.3 Add config migration in `backend/config_migration.py` to move `executor.override.low_soc_export_floor` → `export.export_floor_soc_percent`

## 3. Executor Cleanup

- [x] 3.1 Remove `LOW_SOC_EXPORT_PREVENTION` from `OverrideType` enum in `executor/override.py`
- [x] 3.2 Remove priority 8.5 evaluation branch from `OverrideEvaluator.evaluate()` and `low_soc_threshold` from `__init__`
- [x] 3.3 Remove `low_soc_threshold` from `evaluate_overrides()` convenience function
- [x] 3.4 Remove `low_soc_threshold` / `low_soc_export_floor` from executor config construction in `executor/engine.py`
- [x] 3.5 Remove `low_soc_export_floor` and the `override` subsection comment block from `executor.override` in `config.default.yaml` only (user `config.yaml` files are handled by migration in 2.3)
- [x] 3.7 Remove `low_soc_export_floor` from the debugging snapshot configs: `debugging/cmon_config.yaml`, `debugging/config_me.yaml`, `debugging/kristoffer_config.yaml`
- [x] 3.6 Remove `low_soc_export_floor` validation from `backend/api/routers/config.py` and add range validation (0–100) for `export.export_floor_soc_percent`

## 4. Tests

- [x] 4.1 Add solver tests for export-floor constraint: export blocked below floor, allowed above floor, soft violation under extreme price, inactive when disabled
- [x] 4.2 Remove executor override tests for `LOW_SOC_EXPORT_PREVENTION` in `tests/executor/test_executor_override.py`
- [x] 4.3 Run `./scripts/lint.sh` and the full test suite; fix any failures
