## 1. Data Plumbing

- [x] 1.1 Build a full forecast DataFrame in `pipeline.py` that extends beyond the price horizon (using `forecast_data` directly, not truncated by price LEFT join), and pass it alongside the price horizon end timestamp to `calculate_safety_floor`
- [x] 1.2 Determine the price horizon end timestamp from the price DataFrame index in `pipeline.py` and pass it to `calculate_safety_floor`

## 2. Core Safety Floor Rewrite

- [x] 2.1 Replace `calculate_deficit_ratio` with a temporal deficit function that computes `sum(max(0, load - pv))` per slot over a given DataFrame slice
- [x] 2.2 Rewrite `calculate_safety_floor` to: (a) compute temporal deficit over the 24h window beyond the price horizon end using extended forecast data, (b) apply risk margin to the deficit, (c) enforce minimum floor per risk level, (d) add weather buffer, (e) cap at `max_safety_buffer_pct`
- [x] 2.3 Add fallback: when extended forecast data is unavailable or insufficient, log a warning and use only available horizon data with minimum floor per risk level as baseline

## 3. Tests

- [x] 3.1 Update existing tests in `test_target_soc_risk.py` to reflect the new temporal deficit logic and verify the safety floor doesn't collapse to min_soc when aggregate PV > Load
- [x] 3.2 Add test: spring scenario with aggregate PV surplus but overnight temporal deficit produces a meaningful safety floor
- [x] 3.3 Add test: risk level 5 (Gambler) still returns min_soc as floor
- [x] 3.4 Add test: missing extended forecast data triggers fallback with warning
- [x] 3.5 Add test: max_safety_buffer_pct cap is respected
- [x] 3.6 Add test: price horizon expansion at 13:00 shifts the look-ahead window correctly

## 4. Validation

- [x] 4.1 Run full planner test suite and fix any regressions
- [x] 4.2 Dry-run planner with current real data and verify safety floor is reasonable (~20-35% for risk 3 spring scenario instead of 14%)
