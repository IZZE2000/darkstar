## 1. Core Fixes

- [x] 1.1 Fix `get_price_forecasts_from_db` to return exactly one row per `slot_start` (keep latest `issue_timestamp`, cover both the `days_ahead` filter branch and the no-filter branch)
- [x] 1.2 Fix `get_d1_price_forecast_fallback` to deduplicate on `slot_start` before returning, and log a warning if any duplicates were dropped
- [x] 1.3 Fix the result merge loop in `planner/pipeline.py` to use index-aligned assignment instead of `.values`, and log an error if `len(result_df) != len(future_df)`

## 2. Tests

- [x] 2.1 Test `get_price_forecasts_from_db`: insert duplicate rows with the same `slot_start`, `days_ahead`, and `issue_timestamp` — assert exactly one row returned per slot
- [x] 2.2 Test `get_d1_price_forecast_fallback`: seed the DB with duplicate `slot_start` entries — assert no duplicate `slot_start` values in the return value
- [x] 2.3 Test the pipeline result merge: build a `future_df` with duplicate timestamps (mimicking the cartesian-product crash scenario), run the merge, assert no `ValueError` and that matched rows are populated correctly
