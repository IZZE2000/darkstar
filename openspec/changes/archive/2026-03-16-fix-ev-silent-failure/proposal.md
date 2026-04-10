## Why

A Fronius beta tester's EV was scheduled to charge overnight but the wallbox rejected the command. The executor saw `10kW scheduled, 0kW actual` for 37 minutes and never warned anyone. It silently blocked battery discharge (source isolation) based on the scheduled EV, wasted battery hold time, and logged overwritten planned values — making the root cause invisible in both the UI and CSV export.

## What Changes

- **EV charge failure detection**: After N consecutive ticks where scheduled EV power > 0 but actual EV power = 0, the executor raises an error through the existing "On Error" notification path and marks the execution record as failed.
- **Log original planned values**: The execution record logs the slot plan BEFORE EV source isolation overwrites `discharge_kw` to 0, so the history reflects what the planner actually planned.
- **Log `ev_charging_kw` in execution records**: Add the `ev_charging_kw` field to the execution record so downstream consumers (API, frontend, CSV) can see when EV charging was the reason for idle/Block Discharging. (Spec already exists but implementation is missing from the engine's `_create_execution_record`.)
- **EV isolation reason in history**: When source isolation activates, tag the execution record with a reason string (e.g., "EV source isolation: 10.0kW scheduled, 0.0kW actual") so expanded details explain WHY the mode is idle.

## Capabilities

### New Capabilities
- `ev-charge-failure-detection`: Detect when scheduled EV charging produces zero actual power over consecutive ticks and raise an error + notification

### Modified Capabilities
- `executor`: Execution records log original planned values (before EV override), include `ev_charging_kw`, and carry an isolation reason when source isolation is active

## Impact

- `executor/engine.py`: EV failure detection logic, original slot preservation before override, isolation reason tagging
- `executor/history.py`: New field for isolation reason (if not using existing override fields)
- `backend/learning/models.py`: DB column for `ev_charging_kw` if not already present
- Existing "On Error" notification path — no new notification toggle needed
- Frontend execution history (other chat) already expects `ev_charging_kw` and `mode_intent`
