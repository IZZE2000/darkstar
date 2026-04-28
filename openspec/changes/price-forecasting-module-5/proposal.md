## Why

Module 4 builds the backend plumbing for multi-day EV charging (MultiDayPlanner, Kepler quota constraints, pipeline wiring) but exposes it only through static YAML config. No user will edit `config.yaml` to set a departure deadline or kWh target — the feature is effectively invisible. Module 5 adds the complete user-facing layer: a dashboard EV card with date picker and target controls, bidirectional Home Assistant `input_datetime` entity sync, and the conversion from user-friendly target percentage to the kWh values Module 4's backend expects. After Module 5, multi-day EV charging is a fully usable, end-to-end feature.

## What Changes

- Add an **EV Charging tab/section** to the Energy Resources card on the dashboard with interactive controls: date/time picker for departure deadline, target SoC % slider, progress bar (kWh delivered vs remaining), today's quota display, mini day-by-day quota schedule, and on-track/behind status indicator. The card shows for both daily departure mode and multi-day deadline mode.
- Add a **write API endpoint** (`POST /api/ev/chargers/{id}/deadline`) that accepts `{ deadline, target_pct }` from the dashboard, converts `target_pct` to `target_kwh` using the charger's `battery_capacity_kwh` from settings, and persists the deadline. This is consumed by Module 4's existing pipeline on the next planner run.
- Add **bidirectional HA `input_datetime` sync**: Darkstar reads the HA entity value on startup and subscribes to state changes; when the user sets a deadline in the Darkstar UI, it writes back to the HA entity. The HA entity ID is configured per-charger in settings.
- Add **settings UI fields** for multi-day mode: an optional HA deadline entity ID field per charger, with a warning banner if multi-day mode is active but no HA entity is configured (informational, not blocking).
- Convert Module 4's `target_kwh` config field to `target_pct` in the user-facing layer. The system calculates `target_kwh = (target_pct / 100) * battery_capacity_kwh` at runtime. The backend MultiDayPlanner continues to work in kWh internally.
- Auto-clear deadline when it passes AND `remaining_kwh <= 0` (trip complete). Show a "missed deadline" warning when deadline passes but energy target was not met.

## Capabilities

### New Capabilities
- `ev-dashboard-card`: Dashboard EV charging card integrated into the Energy Resources section. Displays charger status, deadline controls, target % picker, charging progress, daily quota schedule, and on-track/behind status for both daily and multi-day modes.
- `ev-deadline-api`: Write API endpoint for setting/clearing EV charger deadlines and target percentages from the frontend. Handles target_pct to target_kwh conversion and persists to the multi-day state file.
- `ha-deadline-sync`: Bidirectional synchronization between Darkstar's EV deadline state and Home Assistant `input_datetime` entities. Reads HA on startup, subscribes to changes, writes back on Darkstar-side updates.

### Modified Capabilities
- `dashboard-ev-display`: The Energy Resources card gains an EV charging tab/section with interactive controls (currently only shows a static kWh total).
- `per-device-ev-scheduling`: EV charger config gains an optional `ha_deadline_entity` field for HA sync. The `target_kwh` field is supplemented by a `target_pct` alternative that is converted at runtime using `battery_capacity_kwh`.

## Impact

- **Frontend** (`frontend/src/`): New EV card component in `CommandDomains.tsx` or a dedicated component. New API client calls for `GET /api/ev/chargers` (Module 4) and `POST /api/ev/chargers/{id}/deadline`. Date picker and slider UI components.
- **Backend API** (`backend/api/routers/ev.py`): New write endpoint added to the router Module 4 creates. Reads `battery_capacity_kwh` from config to convert % → kWh.
- **Backend HA sync** (`backend/core/` or `backend/services/`): New HA `input_datetime` subscriber that listens for state changes via the existing HA websocket connection and updates internal deadline state. Write-back on Darkstar-side changes.
- **Config** (`executor/config.py`): New optional `ha_deadline_entity` (str | None) field per EV charger.
- **State** (`data/ev_multi_day_state.json`): Module 4's state file is extended with fields written by the deadline API (user-set deadline and target_pct that persist across planner restarts).
- **Dependencies**: Requires Module 4 (price-forecasting-module-4) — the read API endpoint and multi-day pipeline. Uses existing HA websocket infrastructure from the executor.
- **No breaking changes**: All additions are optional and additive. Existing EV charging behavior unchanged when multi-day features are not used.
