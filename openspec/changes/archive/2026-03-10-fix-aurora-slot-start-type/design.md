## Context

The AURORA ML inference pipeline (`ml/corrector.py`) fetches forecast slot data from `ml/api.py:get_forecast_slots()`. The API returns `slot_start` as an ISO format string (line 153 in api.py), but the corrector code expects it to be a timezone-aware datetime for three purposes:
1. Calling `.astimezone(tz)` on the value (lines 357, 377, 432)
2. Merging with `weather_df` which has a datetime64 index (line 397)
3. Merging with `vacation_mode_flag` DataFrame (line 406-410)

Currently, all three code paths fail with: `AttributeError: 'str' object has no attribute 'astimezone'` or the merge error `You are trying to merge on str and datetime64[us, Europe/Stockholm] columns`.

## Goals / Non-Goals

**Goals:**
- Fix the type mismatch by converting `slot_start` from string to timezone-aware datetime immediately after retrieval
- Ensure all downstream processing (timezone conversion, DataFrame merges) works correctly
- Maintain backward compatibility - the fix makes the code work as originally intended

**Non-Goals:**
- Changing the API contract in `ml/api.py` (it can continue returning strings)
- Modifying the weather data loading or vacation mode logic
- Adding new features or changing ML inference behavior

## Decisions

**Decision: Convert type immediately after retrieval, before guard clause**

Convert `slot_start` from string to `pd.Timestamp` right after the `base_records = await get_forecast_slots(...)` call and before the `if not base_records: return` guard. This ensures:
- Single point of conversion (DRY principle)
- All three code paths benefit from the fix
- Clear location for the fix in the data flow

```python
base_records = await get_forecast_slots(slot_start, horizon_end, forecast_version)

# Convert slot_start strings → timezone-aware Timestamps
for rec in base_records:
    rec["slot_start"] = pd.Timestamp(rec["slot_start"]).tz_convert(tz)

if not base_records:
    return [], "none"
```

**Alternatives considered:**
- Convert in `ml/api.py`: Rejected because it would change the API contract and potentially affect other callers
- Convert at each usage site (3 locations): Rejected because it's repetitive and error-prone
- Convert after the guard: Rejected because it's less clear in the data flow; conversion should happen immediately when data is received

## Risks / Trade-offs

**Risk**: Performance impact of iterating through all records → Mitigation: Negligible - it's a simple O(n) loop over typically small datasets (48 slots for 24h horizon)

**Risk**: Timezone handling could introduce subtle bugs → Mitigation: Using pandas built-in `tz_convert(tz)` ensures proper timezone handling, consistent with existing code patterns

**Trade-off**: String vs datetime memory usage → Datetime objects use slightly more memory, but the impact is minimal for the dataset size and correctness is more important
