## Context

The S-Index probabilistic calculation in `planner/strategy/s_index.py` uses uncertainty bounds (P10/P90 percentiles) from ML forecasts to calculate risk-adjusted safety margins via sigma-scaling. The calculation requires:

1. **Slot-level data**: For days within the price horizon (from DataFrame columns `load_p90`, `load_p10`, `pv_p90`, `pv_p10`)
2. **Daily aggregates**: For days beyond the price horizon (from `daily_probabilistic` dict)

The `inputs.py` module's `_get_forecast_data_aurora()` function is responsible for fetching both types of data from the Aurora ML database via `get_forecast_slots()`.

**Current State (Broken):**
1. Probabilistic data is nested under `rec["probabilistic"]["pv_p10"]` etc. in the API response, but the code tries `rec.get("pv_p10")` (top-level)
2. The function computes daily aggregates (`daily_pv_p10`, `daily_pv_p90`, `daily_load_p10`, `daily_load_p90`) but never returns them
3. The caller at line 1020 expects `forecast_result.get("daily_probabilistic")` which is always `{}`
4. Result: `calculate_probabilistic_s_index()` receives empty data and fails with `insufficient_data_or_zero_load`

**Constraints:**
- Must maintain backward compatibility with existing code paths
- No changes to the S-Index calculation logic itself
- Minimal changes to `inputs.py` to fix the bugs

## Goals / Non-Goals

**Goals:**
- Fix data access pattern to correctly read nested probabilistic fields from `get_forecast_slots()` response
- Ensure `daily_probabilistic` is returned in the forecast result
- Enable probabilistic S-Index to successfully calculate sigma-scaling factors
- Maintain existing fallback behavior (physical_deficit mode) when data is genuinely unavailable

**Non-Goals:**
- No changes to S-Index calculation algorithms
- No changes to ML model training or forecast generation
- No new database schema changes
- No API endpoint changes

## Decisions

### Decision: Fix nested data access pattern
**Choice**: Access probabilistic data via `rec.get("probabilistic", {}).get("pv_p10")` instead of `rec.get("pv_p10")`

**Rationale**: The `get_forecast_slots()` function in `ml/api.py` returns a structured response where probabilistic data is nested under the `"probabilistic"` key for organization. The current code incorrectly assumes flat structure.

**Alternative considered**: Modify `get_forecast_slots()` to return flat structure. Rejected because:
- Would require changes to multiple consumers
- Nested structure is cleaner and more explicit
- Bug is in the consumer, not the API

### Decision: Add daily_probabilistic to return value
**Choice**: Add `"daily_probabilistic"` key with nested structure matching expected format

**Rationale**: The caller in `inputs.py` line 1020 explicitly looks for this key. The function already computes the values but never includes them in the return dict.

**Format**:
```python
{
    "pv_p10": daily_pv_p10,      # dict[date_str, float]
    "pv_p90": daily_pv_p90,      # dict[date_str, float]
    "load_p10": daily_load_p10,  # dict[date_str, float]
    "load_p90": daily_load_p90,  # dict[date_str, float]
}
```

## Risks / Trade-offs

**[Risk] Incorrect data aggregation** → **Mitigation**: The aggregation logic (summing per-date values) already exists and is correct. Only the data access and return value were broken.

**[Risk] Breaking existing consumers** → **Mitigation**: Adding a new key to the return dict is backward compatible. No existing keys are modified or removed.

**[Risk] Corrections not applied to probabilistic bounds** → **Mitigation**: The fix applies `pv_corr` and `load_corr` to P10/P90 values just like it does for base forecasts, maintaining consistency.

**[Risk] Applying point corrections to uncertainty bounds may be semantically imprecise** → Adding the same correction offset to both P10 and P90 shifts the entire distribution without changing its width. This is pre-existing retained behaviour, not a validated design decision. It is defensible (the correction represents a systematic bias that should shift all percentiles equally) but has not been formally verified. Retained as-is for KISS; revisit if S-Index sigma-scaling produces unexpected results post-fix.

## Migration Plan

1. Deploy fix to `inputs.py`
2. Next planner run will automatically pick up probabilistic data
3. Monitor logs for successful probabilistic S-Index calculation
4. No rollback needed - fallback to physical_deficit still works if issues arise

## Open Questions

None - the bug is well-understood and the fix is straightforward.
