## Context

Module 4 delivers the backend for multi-day EV charging: `MultiDayPlanner`, Kepler quota constraints, pipeline wiring, config fields (`deadline`, `target_kwh`), and a read-only API (`GET /api/ev/chargers`). It works — but only via YAML config edits and planner restarts. No user will do that.

Module 5 makes the feature real for users. It needs to solve three problems:
1. **Dashboard controls**: A date picker and target % slider that users interact with daily
2. **Backend write path**: An API that persists user-set deadlines and converts % → kWh
3. **HA sync**: Bidirectional sync with `input_datetime` entities for users who want HA automations

Key existing infrastructure:
- `backend/ha_socket.py`: WebSocket client subscribing to `state_changed` events. Monitors EV charger sensors (power, SoC, plug) indexed per charger. Emits `live_metrics` via Socket.IO.
- `backend/core/ha_client.py`: REST helpers — `get_ha_sensor_float()`, `gather_sensor_reads()`, `get_ha_bool()`.
- `executor/actions.py`: `HAClient.call_service()` with retry — supports `number.set_value`, `select.select_option`, `switch.turn_on/off`. No `input_datetime` support yet.
- `backend/api/routers/ev.py`: Module 4 creates this router with `GET /api/ev/chargers`.
- `data/ev_multi_day_state.json`: Module 4's state file written by the pipeline each run.
- `frontend/src/components/CommandDomains.tsx`: `ResourcesDomain` component showing Solar, Load, Water, EV metrics. EV currently shows only a total kWh number.
- `frontend/src/pages/settings/components/EntityArrayEditor.tsx`: `EVChargerEntity` interface with settings UI for all EV charger fields.

## Goals / Non-Goals

**Goals:**
- Users can set/clear a multi-day departure deadline and target SoC % directly from the dashboard
- The dashboard EV card shows live charging status for both daily and multi-day modes
- Deadline changes in Darkstar sync to HA `input_datetime` entities (and vice versa) for automation integration
- Target percentage is the user-facing unit; kWh conversion happens internally using `battery_capacity_kwh` from settings
- The feature is fully self-service — no config editing, no restarts

**Non-Goals:**
- Recurring schedule logic in Darkstar (handled by HA automations — users create their own "every Friday" automation that sets the `input_datetime` entity)
- Building a custom calendar picker component (use an existing React date picker library)
- Real-time kWh-level granularity in the progress bar (pipeline runs every 30 min; that resolution is fine)
- Modifying Module 4's MultiDayPlanner algorithm or Kepler integration
- Supporting `input_datetime` entity auto-creation in HA (user creates the helper manually)

## Decisions

### 1. Dashboard EV card placement: Tab/section inside Energy Resources

The EV card lives inside the existing `ResourcesDomain` (Energy Resources) component as an expandable section or tab, not a separate top-level card. This keeps the dashboard layout stable and groups all resource metrics together.

**What it shows:**

When `has_ev_charger` is true, the existing EV kWh line in the Energy Resources card becomes clickable/expandable into a richer EV section:

```
┌─ Energy Resources ─────────────────────────────────┐
│  Solar Production    3.2 kWh  ━━━━━━━━░░░ 42%      │
│  House Load          5.1 kWh  ━━━━━━━━━━░ 68%      │
│  Water Heating       1.2 kWh  ⚡                     │
│                                                      │
│  ─── EV Charging ──────────────────────────────────  │
│                                                      │
│  🔌 Tesla Model 3              plugged · 42% SoC    │
│                                                      │
│  Mode: [Every day ▾]   Departure: 07:00             │
│    ─── or when multi-day ───                         │
│  Mode: [Ready by ▾]    Deadline: [Fri Apr 11, 07:00]│
│  Target: [80%━━━━━━━━━━━━━━━━━━━░░░]                │
│                                                      │
│  Progress: 23.1 / 36.9 kWh  ━━━━━━━━━░░░░ 63%      │
│  Today's quota: 12.0 kWh     Status: ✓ On track     │
│                                                      │
│  ┌─────┬─────┬─────┬─────┬─────┐                    │
│  │ Thu │ Fri │ Sat │ Sun │ Mon │  ← mini schedule    │
│  │ 12  │ 5   │ 15  │ --  │ --  │  kWh per day       │
│  │ $$  │ $$$ │ $   │     │     │  relative price     │
│  └─────┴─────┴─────┴─────┴─────┘                    │
│                                                      │
│  [Clear deadline]                                    │
└──────────────────────────────────────────────────────┘
```

**Mode toggle:** A dropdown or segmented control with two options:
- **"Every day"** — existing daily departure mode. Shows departure time (read-only, set in settings). No deadline controls.
- **"Ready by"** — multi-day mode. Shows date picker, target % slider, progress, quota schedule.

When in "Every day" mode, the expanded section just shows the charger's plug/SoC status and today's charging kWh — no deadline or quota fields.

**Multiple chargers:** If multiple EV chargers are configured, the section shows a row per charger with independent controls. Each charger has its own mode toggle, deadline, and target.

**Why not a separate card?** The dashboard already has many cards and the user flagged redundancy. Adding to an existing card is more compact and avoids layout churn. Can be refactored later per the backlog item.

### 2. Write API: POST /api/ev/chargers/{id}/deadline

Module 4 creates the read endpoint. Module 5 adds the write endpoint on the same router.

**Endpoint:** `POST /api/ev/chargers/{id}/deadline`

**Request body:**
```json
{
  "deadline": "2026-04-11T07:00",
  "target_pct": 80
}
```

To clear a deadline:
```json
{
  "deadline": null,
  "target_pct": null
}
```

**What it does:**
1. Validates `target_pct` is 0-100, `deadline` is a valid future ISO datetime (or null to clear)
2. Looks up charger by `id` in config to get `battery_capacity_kwh`
3. Computes `target_kwh = (target_pct / 100) * battery_capacity_kwh`
4. Writes to `data/ev_multi_day_state.json` — updates that charger's `deadline` and `target_kwh` fields
5. If HA sync is configured for this charger, writes the deadline to the HA `input_datetime` entity (fire-and-forget, don't block the response)
6. Returns the updated charger state (same shape as `GET /api/ev/chargers` for that charger)

**Pipeline consumption:** On next planner run (every 30 min or on replug), the pipeline reads `ev_multi_day_state.json` for deadline/target_kwh values. This replaces reading from `config.yaml` for multi-day fields — config is the fallback, state file is the source of truth when present.

**Why a state file, not config writes?** Writing back to `config.yaml` is fragile (YAML formatting, comments, merge conflicts). The state file is transient and disposable — if deleted, behavior falls back to config values. This matches the existing pattern where `schedule.json` holds planner output separate from config.

### 3. HA input_datetime bidirectional sync

**Config addition per charger:**
```yaml
ev_chargers:
  - id: ev_charger_1
    ha_deadline_entity: "input_datetime.ev_departure_tesla"  # optional
```

**Read path (HA → Darkstar):**
1. On backend startup, if `ha_deadline_entity` is configured, read the HA entity's current state via REST (`get_ha_sensor_float` won't work — need a new `get_ha_datetime()` helper that reads the string state and parses it as ISO datetime).
2. Subscribe to `state_changed` events for the entity via the existing websocket listener. When the entity changes in HA (user sets via HA UI or automation), update `ev_multi_day_state.json` with the new deadline.
3. The next planner run picks up the changed deadline automatically.

**Write path (Darkstar → HA):**
1. When the `POST /api/ev/chargers/{id}/deadline` endpoint is called, and `ha_deadline_entity` is configured:
2. Call `input_datetime.set_datetime` via the existing `HAClient.call_service()` pattern:
   ```python
   await ha_client.call_service(
       domain="input_datetime",
       service="set_datetime",
       entity_id="input_datetime.ev_departure_tesla",
       data={"datetime": "2026-04-11 07:00:00"}
   )
   ```
3. This is fire-and-forget — if HA is unreachable, the Darkstar-side deadline still takes effect.

**Conflict resolution:** Last-write-wins. If the user changes the deadline in HA and then in Darkstar (or vice versa), the most recent write wins. No conflict detection — the 30-minute planner cycle means any conflict resolves quickly.

**Adding `input_datetime` to the domain safety guard:** The existing `call_service` in `executor/actions.py` has a domain allowlist. Need to add `input_datetime` as an allowed domain. The service pattern matches exactly: `input_datetime.set_datetime` with `{entity_id, datetime}` payload.

### 4. target_pct to target_kwh conversion

The user sets a **target SoC percentage** (e.g., 80%). The system needs **kWh** for the MultiDayPlanner.

**Conversion:** `target_kwh = (target_pct / 100) * battery_capacity_kwh`

**Where `battery_capacity_kwh` comes from:** The EV charger settings already have this field (`EVChargerEntity.battery_capacity_kwh`). It's set once in settings and rarely changes.

**Where conversion happens:** In the `POST /api/ev/chargers/{id}/deadline` endpoint. The state file stores both `target_pct` (for UI display) and the computed `target_kwh` (for the pipeline). This avoids the pipeline needing to look up config just to do the conversion.

**Remaining kWh calculation:** Module 4's pipeline already computes `remaining_kwh = target_kwh - energy_delivered_kwh` using `slot_observations`. The SoC sensor is not used for this — delivered energy from observations is more accurate than SoC sensor readings (which can be noisy, delayed, or have different calibration). The SoC sensor value is displayed in the UI for user reference only.

### 5. Settings UI additions

Minimal additions to the existing EV charger settings panel in `EntityArrayEditor.tsx`:

- **New field: `ha_deadline_entity`** — A text input (with HA entity picker if available) for the `input_datetime` entity ID. Optional. Labeled something like "HA Departure Entity (optional)".
- **Warning banner:** If multi-day mode is active for a charger (deadline is set) but `ha_deadline_entity` is not configured, show an informational banner: "Tip: Connect a Home Assistant input_datetime helper to set deadlines via HA automations or voice control."

No toggle for multi-day mode in settings — that's controlled from the dashboard via the mode dropdown. Settings just holds the static config (charger hardware, sensors, HA entity IDs).

### 6. Deadline lifecycle and auto-clearing

**Active deadline:** Deadline is set, `remaining_kwh > 0`, deadline is in the future. Normal operation — planner computes quotas, card shows progress.

**Trip complete:** `remaining_kwh <= 0` (car reached target SoC). The deadline auto-clears: state file `deadline` is set to null, HA entity is cleared (set to empty/default). Card shows "Charging complete" briefly, then returns to idle state.

**Deadline missed:** Deadline has passed but `remaining_kwh > 0`. Card shows a warning: "Deadline passed — 12.3 kWh not delivered." Deadline does NOT auto-clear — user must acknowledge by clearing it manually or setting a new one. This prevents silent failures.

**Unplug/replug cycle:** Nothing resets. The user might drive to the store and plug back in — the deadline and progress persist. The planner re-runs on replug (existing `replan_on_plugin` behavior) and recalculates quotas with updated `remaining_kwh`.

**Idle (no deadline):** Card shows charger status (plugged/SoC) and daily departure time. No multi-day controls visible beyond the mode dropdown.

### 7. Data flow summary

```
USER INTERACTIONS:

  Dashboard Card                    HA UI / Automation
  ┌──────────────┐                  ┌──────────────┐
  │ Set deadline  │                  │ Set datetime  │
  │ Set target %  │                  │              │
  │ Clear deadline│                  │              │
  └──────┬───────┘                  └──────┬───────┘
         │                                  │
         ▼                                  ▼
  POST /api/ev/chargers/{id}/deadline    state_changed event
         │                                  │
         ├──── convert % → kWh              │
         │                                  │
         ▼                                  ▼
  ┌──────────────────────────────────────────────┐
  │         data/ev_multi_day_state.json          │
  │  { deadline, target_pct, target_kwh, ... }    │
  └──────────────────────┬───────────────────────┘
                         │
                    (every 30 min)
                         │
                         ▼
  ┌──────────────────────────────────────────────┐
  │              Pipeline (Module 4)              │
  │  Reads state file → MultiDayPlanner →        │
  │  quota → Kepler → schedule                    │
  │  Writes back: remaining_kwh, quota_schedule,  │
  │  status, energy_delivered_kwh                  │
  └──────────────────────┬───────────────────────┘
                         │
                         ▼
  ┌──────────────────────────────────────────────┐
  │         GET /api/ev/chargers (Module 4)       │
  │  Reads state file + live HA sensors →         │
  │  Returns full charger state to frontend       │
  └──────────────────────────────────────────────┘
```

## Risks / Trade-offs

**[Risk] State file as source of truth for deadline** → If `ev_multi_day_state.json` is deleted, deadline is lost and falls back to config values (which may be stale or empty). Mitigation: This is acceptable — the state file is the same pattern as `schedule.json`. Users don't manually edit state files. A future improvement could persist to the DB instead.

**[Risk] HA entity doesn't exist when sync is attempted** → User configures `ha_deadline_entity` but hasn't created the helper in HA yet. Mitigation: `call_service` will fail gracefully (existing retry + error logging). The deadline still works Darkstar-side. The settings warning banner guides the user.

**[Risk] Race between HA state_changed and Darkstar deadline write** → User sets deadline in Darkstar, which writes to HA, which triggers state_changed back to Darkstar. Mitigation: The write-back handler should check if the incoming HA value matches what we just wrote and skip the update if so (debounce). A simple timestamp comparison (ignore state_changed events within 2 seconds of our last write) handles this.

**[Risk] Date picker timezone handling** → The deadline must be in the user's local timezone. The frontend sends an ISO datetime string; the backend parses it using the system's configured `timezone_name`. Mitigation: Use timezone-aware parsing throughout. Display in local time on the frontend.

**[Trade-off] target_pct stored in state file, not config** → The user's target % preference doesn't survive a state file deletion. Acceptable because: (a) the user can re-set it in seconds from the dashboard, (b) persisting to config would require YAML writes, (c) this is transient trip-level data, not permanent config.

**[Trade-off] No real-time quota updates** → The quota schedule updates every 30 minutes (planner cycle). If the user sets a new deadline, the card won't show a quota schedule until the next planner run. Mitigation: The card can show "Quota will be calculated on next planner run" during the gap. Alternatively, trigger an immediate planner re-run when deadline is set — similar to `replan_on_plugin`.

**[Trade-off] Adding `input_datetime` to action domain allowlist** → Extends the executor's allowed HA domains. This is a small security surface expansion but follows the exact same pattern as existing `input_number` support.
