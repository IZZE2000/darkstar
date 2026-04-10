## Context

The executor's EV source isolation (REV EVFIX) blocks battery discharge whenever EV charging is scheduled or detected. This is a safety measure to prevent battery→EV energy flow. However, when the wallbox rejects the charge command, the isolation persists silently — blocking discharge for the full slot duration while logging overwritten planned values that hide the real cause.

The execution record currently logs the slot plan AFTER the EV override (line 1222-1232 in `engine.py`), so `planned_discharge_kw` shows 0.0 instead of the original schedule value. The `ev_charging_kw` field exists in the `ExecutionRecord` dataclass and DB model (added in the parallel display-fix change) but is not populated in `_create_execution_record`.

## Goals / Non-Goals

**Goals:**
- Detect when scheduled EV charging produces zero actual power and surface it as an error
- Preserve original planned values in execution history so the planner's intent is visible
- Populate `ev_charging_kw` in execution records
- Add an isolation reason to execution records when source isolation activates

**Non-Goals:**
- Releasing source isolation early when actual EV power is zero (too risky, could cause battery→EV flow if sensor is delayed)
- Adding a new notification toggle for EV — we reuse the existing "On Error" path
- Frontend changes (handled in parallel chat)

## Decisions

### D1: EV failure detection via tick counter

Track consecutive ticks where `scheduled_ev > 0` and `actual_ev < 0.1`. After a configurable threshold (default: 5 ticks = 5 minutes), emit an error via `dispatcher.notify_error()` and mark the execution record as failed.

**Why 5 ticks**: Chargers can take 1-3 minutes to ramp up. 5 minutes gives enough margin while still catching real failures within the same 15-minute slot.

**Alternative considered**: Using a timer instead of tick count. Rejected because tick count is simpler and the executor already ticks every minute, making them equivalent.

**State**: A new instance variable `_ev_zero_power_ticks: int` on the executor, reset to 0 when actual EV power > 0.1 or scheduled EV drops to 0. The error fires once (not every tick) — tracked via a `_ev_failure_notified: bool` flag, reset when the EV slot ends.

### D2: Preserve original slot before EV override

Save a reference to the original `SlotPlan` BEFORE the source isolation creates a new one with `discharge_kw=0`. Pass the original slot to `_create_execution_record` for the planned values, and the modified slot to `make_decision` for the controller.

**Implementation**: Introduce `original_slot` variable before line 1222. The existing `slot` variable gets overwritten by isolation as before. `_create_execution_record` receives `original_slot` for planned fields.

### D3: Isolation reason as override_reason field

When source isolation activates and no actual override is active, populate the `override_reason` field with a descriptive string like `"EV source isolation: 10.0kW scheduled, 0.0kW actual"`. This reuses the existing field rather than adding a new column.

**Why not a new field**: The `override_reason` is already displayed in the frontend's expanded details. Reusing it avoids a DB migration and frontend changes.

**Caveat**: If both a real override AND source isolation are active simultaneously, the real override takes precedence (which is already the case in the controller flow).

### D4: ev_charging_kw population in execution record

Add `ev_charging_kw=original_slot.ev_charging_kw` to `_create_execution_record`. The field already exists in `ExecutionRecord` and the DB model from the parallel change. This is a one-line fix.

## Risks / Trade-offs

- **[Risk] 5-tick threshold too aggressive for slow chargers** → Configurable via a constant, easy to adjust. Most EVSE ramp up within 60 seconds.
- **[Risk] Reusing override_reason for isolation** → Could confuse if both override and isolation are active. Mitigated by the controller's existing precedence logic (overrides take priority over plan-following).
- **[Risk] original_slot reference** → Must ensure the original slot is captured before ANY mutation. The EV isolation block is the only place that mutates the slot, so this is safe.
