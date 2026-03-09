## Why

The AURORA ML inference pipeline crashes with a type mismatch error when merging forecast data with weather data. The `slot_start` field returned by `ml/api.py` is a string (ISO format), but `ml/corrector.py` expects it to be a timezone-aware datetime for merging with `weather_df` which has a datetime64 index. This causes a hard crash: "You are trying to merge on str and datetime64[us, Europe/Stockholm] columns for key 'slot_start'".

## What Changes

- Add a single type conversion block in `ml/corrector.py` immediately after retrieving `base_records` from `get_forecast_slots()`
- Convert `slot_start` from ISO string to timezone-aware pandas Timestamp before any downstream processing
- This fix unblocks all three code paths that currently fail when calling `.astimezone()` on the string value

## Capabilities

### New Capabilities

(None - this is a bug fix to existing capability)

### Modified Capabilities

- `aurora-corrector`: Fix type conversion of `slot_start` field to ensure compatibility with datetime-based merges

## Impact

- **ml/corrector.py**: Single file modification adding type conversion (lines ~334-340)
- **No breaking changes**: The fix makes the code work as originally intended
- **Dependencies**: No new dependencies; uses existing pandas import
