## Why

The D+1 price forecast fallback (introduced in `price-forecasting-core`) stores every forecast generation as new rows in `price_forecasts` without deduplication. When multiple forecast runs exist for the same time slot (e.g., one from the daily tick and one from training), the planner's D+1 fallback query returns duplicate `slot_start` entries. Pandas `left join` on these duplicated keys causes a combinatorial explosion (duplicates × duplicates), producing a DataFrame with 836 rows instead of ~116. Kepler solves the 260-row input correctly, but the result can't be merged back into the 836-row frame — crashing the planner with `ValueError: Length of values (260) does not match length of index (836)`.

## What Changes

- Fix `get_price_forecasts_from_db()` in `ml/price_forecast.py` to deduplicate by `slot_start`, keeping only the row with the latest `issue_timestamp` per slot
- Add a database migration/cleanup step to purge existing duplicate rows from `price_forecasts`
- Add a unit test that verifies deduplication behavior when multiple forecast runs exist for the same slots

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `price-forecasting`: Add deduplication requirement to D+1 fallback query — the system SHALL return at most one forecast record per `slot_start`, preferring the latest `issue_timestamp`

## Impact

- **`ml/price_forecast.py`**: Query logic in `get_price_forecasts_from_db()` — adds dedup subquery
- **`data/planner_learning.db`**: Existing duplicate rows should be cleaned up for affected installations
- **`planner/pipeline.py`**: Indirectly affected (no code changes, but the fix prevents the crash)
- **Tests**: New test case for deduplication
