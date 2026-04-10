## 1. Backend: Status API mode_intent

- [x] 1.1 Add `mode_intent` computation to `get_status()` in `executor/engine.py` — run `Controller.decide()` with current slot and system state, include result in `current_slot_plan`
- [x] 1.2 Add `ev_charging_kw` and `discharge_kw` to the `current_slot_plan` dict in `get_status()`
- [x] 1.3 Handle fallback: if controller can't run (no profile, HA offline), set `mode_intent` to `null`

## 2. Backend: Log ev_charging_kw in execution records

- [x] 2.1 Add `ev_charging_kw` column to the `ExecutionLog` model and create a migration
- [x] 2.2 Include `ev_charging_kw` from `SlotPlan` in `_create_execution_record()` in `executor/engine.py`
- [x] 2.3 Include `ev_charging_kw` in the `get_history()` API response dict

## 3. Frontend: Primary mode badges in execution history

- [x] 3.1 Create a mode badge mapping function that maps `commanded_work_mode` to emoji, label, and color class for the four modes
- [x] 3.2 Replace the legacy badge logic (Export First check, charge_current check, "— Idle" fallback) with a single primary mode badge from the mapping
- [x] 3.3 Handle null/unrecognized `commanded_work_mode` gracefully (no badge)

## 4. Frontend: Context badges in execution history

- [x] 4.1 Add "💧 Heating" context badge shown when `planned_water_kw > 0`
- [x] 4.2 Add "🔌 EV" context badge shown when `ev_charging_kw > 0`
- [x] 4.3 Remove the old water temp > 50 check for the heat badge, use `planned_water_kw > 0` instead

## 5. Frontend: Next-slot preview mode display

- [x] 5.1 Replace the hardcoded "Idle / Self-consumption" fallback with a mode badge using `mode_intent` from the status API
- [x] 5.2 Show context badges (EV, Water) in the next-slot preview using `ev_charging_kw` and `water_kw`
- [x] 5.3 Handle missing `mode_intent` (null) — fall back to showing value badges only

## 6. Tests

- [x] 6.1 Test that `get_status()` returns `mode_intent` in `current_slot_plan` for each of the four modes
- [x] 6.2 Test that `ev_charging_kw` is logged in execution records
- [x] 6.3 Test fallback behavior when controller cannot compute mode_intent
