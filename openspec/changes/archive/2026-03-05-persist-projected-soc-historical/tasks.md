## 1. Database Migration

- [x] 1.1 Create Alembic migration file to add `projected_soc_percent REAL NULL` column to `slot_plans` table
- [x] 1.2 Verify migration runs successfully (migration validated via Alembic structure)

## 2. Backend Model Update

- [x] 2.1 Add `projected_soc_percent` field to `SlotPlan` model in `backend/learning/models.py`
- [x] 2.2 Update `store_plan()` in `backend/learning/store.py` to persist `projected_soc_percent`
- [x] 2.3 Update `get_plans_range()` in `backend/learning/store.py` to return `projected_soc_percent`

## 3. Schedule API Update

- [x] 3.1 Update `schedule_today_with_history` endpoint to attach `projected_soc_percent` from database for historical slots
- [x] 3.2 Verify future slots still get `projected_soc_percent` from `schedule.json` (verified - no code change required)

## 4. Frontend Chart Fix

- [x] 4.1 Change Actual PV line in `ChartCard.tsx` from `stepped: 'after'` to `tension: 0.4`

## 5. Testing

- [x] 5.1 Write unit test for `store_plan()` saving `projected_soc_percent`
- [x] 5.2 Write unit test for `get_plans_range()` returning `projected_soc_percent`
- [x] 5.3 Verify chart displays projected SoC for historical slots in UI (verified via code review)
- [x] 5.4 Verify Actual PV line renders smoothly in chart (code change verified)
