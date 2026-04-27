## Why

At midnight the planner crashes with `ValueError: Length of values (382) does not match length of index (1522)` because the ML price forecast DB contains duplicate rows for the same `slot_start`, which leak through an incomplete deduplication query and cause a cartesian-product join explosion inside the pipeline.

## What Changes

- Fix `get_price_forecasts_from_db`: the current dedup-by-`max(issue_timestamp)` join lets multiple rows through when they share the same `(slot_start, days_ahead, issue_timestamp)` — change to return exactly one row per `slot_start`
- Add a deduplication guard in `get_d1_price_forecast_fallback` so duplicate `slot_start` entries are filtered before they enter `all_entries` in `get_nordpool_data`
- Fix `planner/pipeline.py` line 736: replace `result_df[col].values` (positional) with `result_df[col]` (index-aligned) and log an error if lengths mismatch, so the planner never crashes from this class of data inconsistency again

## Capabilities

### New Capabilities

_(none — this is a bug fix)_

### Modified Capabilities

- `price-forecasting`: `get_price_forecasts_from_db` must guarantee exactly one record per `slot_start` regardless of duplicate `issue_timestamp` values in the DB
- `planner`: the pipeline merge of Kepler output back into `future_df` must be index-aligned, not positional, and must log a diagnostic warning on length mismatch

## Impact

- **`ml/price_forecast.py`** — `get_price_forecasts_from_db` query rewrite; `get_d1_price_forecast_fallback` dedup guard
- **`planner/pipeline.py`** — lines 734-736, result merge loop
- **No breaking changes** — behavior is identical when the DB has no duplicates (the normal case)
- **No config changes**
