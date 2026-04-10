## 1. Query Deduplication

- [x] 1.1 Modify `get_price_forecasts_from_db()` in `ml/price_forecast.py` to add a SQLAlchemy subquery that deduplicates by `slot_start`, keeping only the row with the latest `issue_timestamp` per slot
- [x] 1.2 When `days_ahead` is None, the dedup subquery must group by `(slot_start, days_ahead)` — not `slot_start` alone — to avoid collapsing rows from different forecast horizons that share the same `slot_start`

## 2. Database Cleanup

- [x] 2.1 Add a `cleanup_price_forecast_duplicates()` function in `ml/price_forecast.py` that deletes all but the latest `issue_timestamp` row per `(slot_start, days_ahead)` pair
- [x] 2.2 Run the cleanup on the dev PC's `data/planner_learning.db` and verify duplicate count drops to zero
- [x] 2.3 Integrate cleanup into app startup (backend) as a one-time migration for existing installations

## 3. Tests

- [x] 3.1 Add unit test: insert 2 forecast runs for the same 48 slots into a temp SQLite DB, call `get_price_forecasts_from_db()` directly with `days_ahead=1`, assert exactly 48 unique records returned — do NOT mock `get_price_forecasts_from_db` or the SQL dedup logic won't be exercised
- [x] 3.2 Add unit test: insert weather-only rows (null spot_p50) alongside valid forecasts, assert only valid rows returned
- [x] 3.3 Run `./scripts/lint.sh` and fix any failures

## 4. Verification

- [x] 4.1 Trigger a planner run and verify it completes without the `Length of values` error
- [x] 4.2 Verify Kepler result and schedule.json are generated correctly
