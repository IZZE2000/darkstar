## 1. Solver Fix — Inverter AC Constraint

- [x] 1.1 In `planner/solver/kepler.py:330`, replace `prob += discharge[t] + s.pv_kwh <= inverter_ac_kwh` with `prob += discharge[t] <= max(0.0, inverter_ac_kwh - s.pv_kwh)`
- [x] 1.2 Write a regression test in `tests/planner/` that constructs a slot where `pv_kwh > inverter_ac_kwh` and verifies the solver returns `Optimal` with `discharge = 0`

## 2. Backend — Emit "failed" Phase on Error

- [x] 2.1 In `backend/services/planner_service.py`, add `await self._emit_progress("failed")` in the `except PlannerError` block, immediately before `self._current_phase = None`
- [x] 2.2 Add `await self._emit_progress("failed")` in the `except Exception` block, immediately before `self._current_phase = None`

## 3. Frontend — Show Warnings and Handle Failed Phase

- [x] 3.1 In `frontend/src/components/SystemAlert.tsx`, change the early return guard so it returns null only when there are no issues — not when `health.healthy` is true. Keep the existing `!health` guard. The condition becomes: return null when `!health` OR when `health.issues.length === 0`
- [x] 3.2 In `frontend/src/components/QuickActions.tsx`, add `case 'failed': return 'Failed ✗'` to `getPlannerButtonText()` and `case 'failed': return '0%'` to `getProgressBarWidth()`. In the `planner_progress` WebSocket handler, when `data.phase === 'failed'` clear `plannerProgress` after a short delay (same pattern as the existing `schedule_updated` handler that resets after `complete`)
