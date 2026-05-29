## Context

The `price_forecasts` table stores one row per forecast generation per slot. Each forecast run (daily tick ~06:00, and every training cycle) creates a fresh set of rows with the same `slot_start` but different `issue_timestamp`. The D+1 fallback query in `get_price_forecasts_from_db()` fetches the latest 96 rows ordered by `slot_start DESC` — no deduplication. When 2+ runs exist, half the returned slots are duplicated.

These duplicates flow into `_process_nordpool_data()` → `prepare_df()` → `future_df` join → Kepler, causing the planner to crash with a length mismatch.

## Goals / Non-Goals

**Goals:**
- Ensure `get_price_forecasts_from_db()` always returns at most one row per `slot_start`
- Provide a one-time cleanup for existing duplicate data in `price_forecasts`
- Prevent downstream consumers from seeing duplicate `slot_start` entries

**Non-Goals:**
- Changing the forecast storage schema (adding unique constraints)
- Modifying planner's DataFrame merge logic (the fix belongs at the source)
- Addressing the beta user's separate Kepler infeasibility issue

## Decisions

### Decision 1: Deduplicate at query time (not at write time)

**Choice**: Add a SQL dedup subquery in `get_price_forecasts_from_db()` that keeps only the latest `issue_timestamp` per `slot_start`.

**Alternatives considered**:
- _UPSERT on write (INSERT OR REPLACE)_: Would discard weather-only rows from earlier runs that may have different weather snapshots. Also risks losing training data if two runs have different feature values.
- _Delete old rows on write_: Same concern about losing historical weather snapshots used for training.
- _Add UNIQUE constraint on (slot_start, days_ahead)_: Would prevent storing multiple forecast runs entirely, breaking the training pipeline's need for historical (forecast, actual) pairs.

**Rationale**: Deduplicating at read time preserves all historical data for training while ensuring downstream consumers (planner, API) always get one row per slot. The subquery adds negligible overhead (~1000 rows max).

### Decision 2: Cleanup script (not migration)

**Choice**: Provide a standalone cleanup function that can be called from the dev DB or added to a startup hook, rather than a formal Alembic migration.

**Rationale**: The `price_forecasts` table is not managed by Alembic — it's a simple SQLite table in `planner_learning.db`. A cleanup function is sufficient.

## Risks / Trade-offs

- **[Subquery performance on large tables]** → Mitigation: `price_forecasts` is bounded (~1000 rows per days_ahead × 7 horizons ≈ 7K rows). Subquery performance is negligible at this scale.
- **[Existing installations have corrupted data]** → Mitigation: Provide a cleanup function that can be shipped in a startup hook or run manually. For the dev PC, we clean immediately.
