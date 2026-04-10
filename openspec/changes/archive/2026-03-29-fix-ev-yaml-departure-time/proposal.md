## Why

EV departure time (e.g. `16:00`) is written to `config.yaml` unquoted by the backend (ruamel.yaml, YAML 1.2). The executor reads it with PyYAML (YAML 1.1), which interprets `16:00` as the base-60 integer `960`. This causes the planner's deadline parser to fail silently (returns `None`), removing the EV charging deadline constraint entirely. The solver then schedules charging at the cheapest time across the full horizon — which, when tomorrow's prices arrive, means overnight instead of before the user's departure. Beta testers report charging plans jumping to "tomorrow" unexpectedly.

## What Changes

- Switch `executor/config.py` from `import yaml` (PyYAML/YAML 1.1) to `ruamel.yaml` (YAML 1.2), aligning it with the rest of the codebase. This prevents `16:00` from being misread as `960`.
- Add a defensive integer-to-HH:MM converter in `executor/config.py` for `departure_time`, so existing configs with corrupted values (`960`, `1020`) are handled gracefully.
- Add a defensive integer-to-HH:MM fallback in `planner/pipeline.py`'s `calculate_ev_deadline()`, so a numeric departure_time never silently becomes `None`.
- Change the departure time placeholder text in the frontend from `"07:00"` to `"e.g. 07:00"` so it's clearly an example, not pre-filled data.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `per-device-ev-scheduling`: Departure time parsing must handle both string `"HH:MM"` and integer (minutes-since-midnight) formats without silent failure.

## Impact

- `executor/config.py` — YAML loader import change + departure_time parsing
- `planner/pipeline.py` — `calculate_ev_deadline()` defensive fallback
- `frontend/src/pages/settings/components/EntityArrayEditor.tsx` — placeholder text
- No API changes, no config schema changes, no breaking changes
