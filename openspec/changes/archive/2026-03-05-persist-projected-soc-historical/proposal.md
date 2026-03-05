## Why

The `projected_soc_percent` field is currently only written to `schedule.json` for future slots, but never persisted to the `slot_plans` database table. This means historical slots lack the projected SoC data needed for the SoC projection chart to show the full 48-hour span. Additionally, the Actual PV chart line renders with a stepped appearance while the PV Forecast line is smooth, creating visual inconsistency.

## What Changes

- Add `projected_soc_percent` column to `slot_plans` database table
- Persist `projected_soc_percent` to database when storing slot plans
- Attach `projected_soc_percent` from database for historical slots in schedule API
- Fix Actual PV chart line to use smooth rendering (tension: 0.4) instead of stepped

## Capabilities

### New Capabilities

- `projected-soc-persistence`: Persists projected_soc_percent to slot_plans database for historical analysis and chart display

### Modified Capabilities

- `chart-planned-actual-display`: Chart line rendering consistency - Actual PV line should match PV Forecast line style (smooth, not stepped)

## Impact

- **Database**: New column `projected_soc_percent` in `slot_plans` table (Alembic migration)
- **Backend**:
  - `backend/learning/models.py` - SlotPlan model
  - `backend/learning/store.py` - store_plan() and get_plans_range()
  - `backend/api/routers/schedule.py` - historical slot enrichment
- **Frontend**: `frontend/src/components/ChartCard.tsx` - Actual PV line styling
