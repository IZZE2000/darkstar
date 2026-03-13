## Why

The `calculate_safety_floor` function uses an aggregate deficit ratio (`total_load - total_pv`) over the entire horizon, which collapses to zero when total PV exceeds total load. In spring/summer this makes `target_soc` equal to `min_soc` regardless of risk level, because all terms are multiplied by `deficit_ratio = 0.0`. The risk appetite setting becomes meaningless. This causes the MILP solver to drain the battery aggressively (including unprofitable exports) since it has no meaningful end-of-horizon floor to respect. Multiple beta testers hit this simultaneously as spring PV production increased.

## What Changes

- Replace the aggregate deficit ratio calculation in `calculate_safety_floor` with a **temporal (per-slot) deficit** approach: sum `max(0, load - pv)` per slot. This captures the energy the battery must provide when PV is unavailable (evenings, nights, cloudy periods) regardless of aggregate surplus.
- Extend the safety floor calculation to look **beyond the price horizon** using available load/PV forecasts. The safety floor covers the 24h window starting from where the price horizon ends, so the MILP always has a meaningful end-target for what it can't see.
- Add a **minimum floor per risk level** so the safety floor never collapses to `min_soc` even in perfect conditions.
- Keep the existing `max_safety_buffer_pct` cap to prevent runaway in extended bad weather.
- Risk appetite scales the margin on the temporal deficit and sets the minimum floor.

## Capabilities

### New Capabilities
_None_

### Modified Capabilities
- `planner`: The safety floor calculation changes from aggregate deficit to temporal deficit, and extends beyond the price horizon. This changes the end-of-horizon target behavior.

## Impact

- `planner/strategy/s_index.py`: `calculate_safety_floor` and `calculate_deficit_ratio` rewritten
- `planner/pipeline.py`: May need to pass extended forecast data to `calculate_safety_floor`
- Existing tests in `tests/planner/test_target_soc_risk.py` will need updating
- No config changes (uses existing `risk_appetite`, `max_safety_buffer_pct`, `min_soc_percent`)
- No API or breaking changes
