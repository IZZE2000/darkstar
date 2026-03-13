## 1. Remove Target Over Violation Penalty (`kepler.py`)

- [x] 1.1 Remove `target_over_violation` variable definition
- [x] 1.2 Remove the upper-bound constraint `soc[T] <= target_soc_kwh + target_over_violation`
- [x] 1.3 Remove the objective penalty `target_soc_penalty * target_over_violation` from `total_cost`
- [x] 1.4 Remove the guard `if target_soc_kwh > 0:` and its enclosed `total_cost.append(...)` for the over-target penalty only.
  > ⚠️ **Note:** Only remove the inner `if target_soc_kwh > 0` block and its `append`. The outer `if config.target_soc_kwh is not None:` block must remain — it owns the `target_under_violation` constraint and penalty which are correct and must be preserved.

## 2. Restore Export Threshold Configuration (`adapter.py`)

- [x] 2.1 Add `export_threshold_sek_per_kwh=get_val("export_threshold_sek_per_kwh", 0.0),` to the `KeplerConfig` initialization inside `config_to_kepler_config()`

## 3. Fix Water Heating Objective Duplication (`kepler.py`)

- [x] 3.1 In the objective function assembly (`pulp.lpSum(...)`), remove the **second** occurrence of the `water_block_start_penalty_sek` term (the duplicate added under the `# Rev K16 Phase 2: Reliability Penalties` comment)
- [x] 3.2 Remove the **second** occurrence of the water symmetry-breaker tiebreaker term (`water_heat[t] * (t * 1e-5)`) from the same objective block

## 4. Regression Tests

- [x] 4.1 In `tests/planner/test_kepler_solver.py`: Add a test that configures a `target_soc_kwh`, provides surplus solar such that end-of-horizon SoC would naturally exceed the target, and asserts that the solver does **not** export energy at zero or negative price to reduce SoC
- [x] 4.2 In `tests/planner/test_kepler_export.py`: Add a test that calls `config_to_kepler_config()` with an `export_threshold_sek_per_kwh` value set in config, and asserts the resulting `KeplerConfig` carries that value (not 0.0)
- [x] 4.3 In `tests/planner/test_kepler_export.py`: Add a solver-level test that sets `export_threshold` high enough to make a marginal export unprofitable, and asserts the solver does not export in that scenario

## 5. Testing and Validation

- [x] 5.1 Run `uv run python -m pytest tests/planner/test_kepler_solver.py -v`
- [x] 5.2 Run `uv run python -m pytest tests/planner/test_kepler_export.py -v`
- [x] 5.3 Run full suite `uv run python -m pytest -q`
- [x] 5.4 Run linting `uv run ruff check .`

## 6. Dynamic Export Threshold Implementation

- [x] 6.1 In `backend/strategy/engine.py`: Replace the step-function logic (if spread > 1.5 / elif spread < 0.5) with continuous scaling function
  - Define `RISK_BASELINE_SHIFTS` mapping (1→0.15, 2→0.10, 3→0.05, 4→0.02, 5→0.00)
  - Calculate `spread_norm = max(0.0, min(1.0, (spread - 0.3) / 1.7))`
  - Calculate threshold: `0.50 - (0.50 - baseline) * spread_norm`
  - Round to 3 decimal places
  - Replace the two hardcoded `kepler_overrides["export_threshold_sek_per_kwh"] = X` lines with the dynamic result
  - `wear_cost_sek_per_kwh` and `ramping_cost_sek_per_kw` overrides MUST always be applied (they are still spread-dependent) — do not remove them, only the export threshold lines change to use the formula

- [x] 6.2 In `backend/strategy/engine.py`: Read `risk_appetite` from config and pass to threshold calculation
  - Get risk_appetite from `self.config.get("s_index", {}).get("risk_appetite", 3)`
  - Use it to look up the baseline shift

- [x] 6.3 In `tests/planner/test_strategy_engine.py`: Add tests for dynamic threshold
  - Test spread=0.2, risk=3 → threshold = 0.50
  - Test spread=2.5, risk=5 → threshold = 0.00
  - Test spread=1.0, risk=3 → threshold ≈ 0.24
  - Test spread=0.5, risk=3 → threshold ≈ 0.38 (previously would have been 0.0 in the gap)
  - Test that risk appetite only affects floor, not ceiling
  - Test that `wear_cost_sek_per_kwh` and `ramping_cost_sek_per_kw` overrides are still present in the output for both high-spread and low-spread scenarios

- [x] 6.4 Run tests: `uv run python -m pytest tests/planner/test_strategy_engine.py -v`
