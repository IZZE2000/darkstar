## Context

At midnight the Nordpool cache invalidates and the planner fetches fresh prices. Before 13:00 CET no real D+1 prices exist, so `get_nordpool_data` falls back to `get_d1_price_forecast_fallback`, which queries the ML price forecast DB. That DB accumulates duplicate rows — multiple forecast runs writing to the same `(slot_start, days_ahead)` with identical `issue_timestamp` values. The dedup query picks `max(issue_timestamp)` per slot and joins back, but when rows tie on `issue_timestamp` the join returns all tied rows. Those duplicates become duplicate timestamps in `price_df`. `future_df` inherits them. Kepler processes 382 rows (including duplicates), returns 382 result slots with the same duplicate timestamps, and `result_df` also has 382 duplicate-indexed rows. The final `future_df.join(result_df)` produces a cartesian product (382 × ~4 = 1522 rows). Then `result_df[col].values` has 382 elements assigned to a 1522-row index — crash.

The "Cleaned up 2737 duplicate price forecast rows" log entry confirms the DB state. The cleanup job runs, but after the crash.

## Goals / Non-Goals

**Goals:**
- Fix the dedup query so it returns exactly one row per `slot_start` regardless of `issue_timestamp` ties
- Add a dedup guard in the fallback so duplicate timestamps never reach `all_entries`
- Change the result merge in the pipeline from positional `.values` assignment to index-aligned assignment, with a logged error on length mismatch
- All three fixes are independent layers of defence; any one of them alone would prevent the crash

**Non-Goals:**
- Cleaning up existing duplicate rows in the DB (the cleanup job already handles this)
- Changing the ML pipeline to not produce duplicate `issue_timestamp` values (separate concern)
- Altering Kepler's planning horizon or slot count

## Decisions

### 1. Fix dedup query with DISTINCT or Python-side dedup

**Choice:** Apply Python-side deduplication after the query returns, using `{slot_start: row}` dict keyed on `slot_start` and keeping the latest `issue_timestamp`. This is simpler and more robust than rewriting the SQLAlchemy subquery join.

**Why:** The join-on-max pattern is inherently fragile when timestamps tie to the second. A Python dict keyed on `slot_start` is O(n) and guarantees exactly one row per slot regardless of DB state.

**Alternative considered:** Rewrite subquery to use `ROW_NUMBER() OVER (PARTITION BY slot_start ORDER BY issue_timestamp DESC)` and filter to rank=1. Rejected because SQLite's window function support is version-dependent and adds SQL complexity.

### 2. Dedup guard location: fallback function, not `_process_nordpool_data`

**Choice:** Add the dedup guard inside `get_d1_price_forecast_fallback` before returning, not in `_process_nordpool_data`.

**Why:** `_process_nordpool_data` is a general-purpose formatter that doesn't know the origin of its inputs. The fallback is the specific call site that introduces the risk. Deduplicating there is targeted and doesn't change behaviour for the normal Nordpool path.

### 3. Pipeline merge: index-aligned assignment + error log

**Choice:** Change `final_df[col] = result_df[col].values` to `final_df[col] = result_df[col]` and add a single `logger.error` before the loop if `len(result_df) != len(future_df)`.

**Why:** Using the pandas Series directly aligns by index, which is the correct semantics for a join-based merge. The error log surfaces the mismatch for diagnosis without crashing the planner.

**Why not raise an exception:** A partial schedule (NaN slots filled later by `apply_manual_plan`) is better than no schedule. The error log is sufficient signal.

## Risks / Trade-offs

- **DB dedup guard bypasses tie-breaking logic** → the Python dict keeps the last row seen for a given `slot_start`, not necessarily the highest-quality forecast. Acceptable: all tied rows have identical `issue_timestamp` so they were generated in the same run.
- **Index-aligned merge silently produces NaN slots** if the root cause persists after the fix → the added `logger.error` makes this visible; the NaN slots will be overwritten by `apply_manual_plan` defaults where applicable.
- **No regression test for the exact crash path** → the fix should be covered by a unit test that feeds duplicate-timestamped price data and asserts no crash and correct row count.
