## Why

Three bugs introduced in recent refactors degrade planner behaviour:

1. **Force-dumping bug**: The Kepler solver forcefully exports free solar energy at zero or negative prices just to hit the "Safety Floor" target. This is caused by a bidirectional penalty applied to the end-of-horizon SoC target, which turns the Safety Floor into a ceiling — the solver incurs a 200 SEK/kWh fake cost for *holding too much energy*, so it dumps it.

2. **Export threshold bug**: A refactor accidentally removed the mapping for the user's `export_threshold_sek_per_kwh` parameter in `adapter.py`, hard-locking the effective export threshold to `0.0` for all users. This allows the battery to continuously micro-cycle for negligible profits without any protection. Additionally, the StrategyEngine's step-function logic (if spread > 1.5 / elif spread < 0.5) leaves a dangerous gap where moderate volatility (0.5-1.5 SEK spread) falls back to 0.0 threshold, causing unwanted micro-cycling.

3. **Water heating objective duplication bug**: A pre-existing code duplication in `kepler.py`'s objective function causes the `water_block_start_penalty` term and the water scheduling symmetry-breaker to each be added **twice** to the solver's cost function. This silently inflates the solver's water heating costs and distorts scheduling decisions for all users with water heating.

## What Changes

- Remove the `target_over_violation` soft constraint and penalty from the Kepler solver. The solver will be allowed to finish the planning horizon above the Safety Floor without any penalty, allowing it to preserve free solar energy. The `target_under_violation` constraint (the actual floor) is fully preserved.
- Restore the `export_threshold_sek_per_kwh` setting mapping in `adapter.py`, so user configuration again restricts the solver from exporting when the spot price does not clear the threshold.
- Replace the StrategyEngine's step-function export threshold logic with a continuous scaling function based on price volatility (spread) and user's `risk_appetite`. This eliminates the gap where moderate volatility falls back to 0.0 threshold. The new formula scales from 0.50 SEK (low spread) down to a risk-based baseline (high spread: 0.00-0.15 SEK).
- Remove the duplicate objective terms in `kepler.py` for the water heating block-start penalty and symmetry-breaker.
- Add regression tests covering all bug fixes and the new dynamic threshold behavior.

## Capabilities

### New Capabilities
- `strategy`: Dynamic export threshold that continuously scales with price volatility (spread) and user risk appetite, replacing the step-function with dangerous gaps.

### Modified Capabilities
- `planner`: End-of-horizon battery target behavior changes from a bidirectional soft target to a unidirectional minimum floor. Export threshold functionality restored. Water heating objective function corrected.
- `strategy`: Export threshold now calculated using continuous function: 0.50 SEK at low spread, scaling down to risk-based baseline (0.00-0.15 SEK) at high spread. Risk appetite (1-5) shifts the floor, not the ceiling.

## Impact

- `planner/solver/kepler.py`: Remove `target_over_violation` variable, constraint, and objective term. Remove duplicate objective terms for water heating.
- `planner/solver/adapter.py`: Restore `export_threshold_sek_per_kwh` mapping in `config_to_kepler_config()`.
- `backend/strategy/engine.py`: Replace step-function threshold logic with continuous scaling based on price spread and `risk_appetite`.
- `tests/planner/test_kepler_solver.py`: Add regression test for over-target solar surplus scenario.
- `tests/planner/test_kepler_export.py`: Add regression test verifying the export threshold is mapped and respected.
- `tests/strategy/`: Add tests for dynamic export threshold calculation.
- Expected to eliminate beta-tester issues with unwanted low-margin and zero-price battery dumping, fix silently incorrect water heating costs, and prevent micro-cycling during moderate price volatility.
