## Prerequisites

Module 4 (`price-forecasting-module-4`) MUST be fully implemented before starting this module. Module 4 provides:
- `backend/api/routers/ev.py` with `GET /api/ev/chargers` endpoint
- `data/ev_multi_day_state.json` state file written by the pipeline
- `MultiDayPlanner`, Kepler quota constraint, and pipeline wiring in `planner/pipeline.py`
- `deadline` and `target_kwh` fields on `EVChargerDeviceConfig` in `executor/config.py`

## State File Schema

All tasks referencing `data/ev_multi_day_state.json` SHALL use this exact JSON structure:

```json
{
  "last_updated": "2026-04-10T14:30:00+02:00",
  "chargers": {
    "ev_charger_1": {
      "deadline": "2026-04-11T07:00:00+02:00",
      "target_pct": 80,
      "target_kwh": 65.6,
      "remaining_kwh": 36.9,
      "energy_delivered_kwh": 28.7,
      "daily_quota_kwh": 12.0,
      "days_remaining": 3,
      "quota_schedule": [
        { "date": "2026-04-09", "quota_kwh": 12.0, "avg_price_sek": 0.45 },
        { "date": "2026-04-10", "quota_kwh": 18.0, "avg_price_sek": 0.28 },
        { "date": "2026-04-11", "quota_kwh": 6.9, "avg_price_sek": 0.52 }
      ],
      "status": "on_track",
      "source": "api"
    }
  }
}
```

Fields written by the **write API** (task group 2): `deadline`, `target_pct`, `target_kwh`, `source` (set to `"api"` or `"ha"`).
Fields written by the **pipeline** (Module 4 + task group 3): `remaining_kwh`, `energy_delivered_kwh`, `daily_quota_kwh`, `days_remaining`, `quota_schedule`, `status`.
The `last_updated` field is set on every write.

The pipeline MUST preserve API-written fields when it writes its own fields (read-modify-write pattern).

## 1. Config Extension

- [ ] 1.1 Add `ha_deadline_entity` (str | None, default None) and `target_pct` (float | None, default None) fields to the `EVChargerDeviceConfig` dataclass in `executor/config.py`. Parse `ha_deadline_entity` via the existing `_str_or_none()` helper. Validate: if `target_pct` is set, it must be 0-100 (log warning and set to None otherwise); if `target_pct` is set without `battery_capacity_kwh`, log warning "Cannot compute target_kwh: battery_capacity_kwh not set" and set `target_pct` to None.
- [ ] 1.2 Add `ha_deadline_entity` and `target_pct` example entries (commented out) to `config.yaml` and `config.default.yaml` under the first `ev_chargers` entry:
  ```yaml
  # ha_deadline_entity: "input_datetime.ev_departure"  # Optional: HA entity for deadline sync
  # target_pct: 80  # Optional: target SoC % for multi-day charging (requires battery_capacity_kwh)
  ```
- [ ] 1.3 Add `ha_deadline_entity?: string`, `target_pct?: number`, `deadline?: string`, and `target_kwh?: number` fields to the `EVChargerEntity` TypeScript interface in `frontend/src/pages/settings/components/EntityArrayEditor.tsx`.
- [ ] 1.4 Add a "HA Deadline Entity (optional)" text input field to the EV charger settings form in `EntityArrayEditor.tsx`, below the existing `switch_entity` field. Use the same input styling pattern as `switch_entity` (Tailwind `.input` class). Only visible when the charger entry is expanded.
- [ ] 1.5 Write unit tests in `tests/ev/test_ev_config.py` covering: `ha_deadline_entity` parsing (valid string, empty string → None, missing → None), `target_pct` parsing (valid float, out of range → warning + None, missing `battery_capacity_kwh` → warning + None).

## 2. Deadline Write API

**Depends on:** Group 1 (config fields), Module 4 (`backend/api/routers/ev.py` exists with GET endpoint).

- [ ] 2.1 Add `POST /api/ev/chargers/{id}/deadline` endpoint to the existing `backend/api/routers/ev.py` (created by Module 4). Use a Pydantic model for the request body:
  ```python
  class SetDeadlineRequest(BaseModel):
      deadline: str | None = None   # ISO 8601 datetime or null
      target_pct: float | None = None  # 0-100 or null
  ```
  Validation rules: `target_pct` must be 0-100 if provided; `deadline` must parse as a valid future datetime if provided; `target_pct` without `deadline` returns HTTP 422 "target_pct requires a deadline"; unknown charger `{id}` returns HTTP 404 "Charger not found".
- [ ] 2.2 Implement target_pct → target_kwh conversion in the endpoint. Look up the charger by `{id}` in the loaded executor config (access via the existing config loading pattern in `backend/api/routers/executor.py`). Read `battery_capacity_kwh` from the charger config. Compute `target_kwh = (target_pct / 100) * battery_capacity_kwh`. If `battery_capacity_kwh` is None or 0, return HTTP 422 "battery_capacity_kwh not configured for this charger".
- [ ] 2.3 Implement state file read/write. Create a helper module `backend/core/ev_state.py` with two functions:
  ```python
  def read_ev_state(state_path: Path = Path("data/ev_multi_day_state.json")) -> dict:
      """Read state file, return empty structure if missing/corrupt."""

  def write_ev_state(state: dict, state_path: Path = Path("data/ev_multi_day_state.json")) -> None:
      """Atomic write: write to .tmp file then os.replace() to target path."""
  ```
  The endpoint uses these to read the current state, update the charger entry with `deadline`, `target_pct`, `target_kwh`, and `source: "api"`, update `last_updated`, and write back.
- [ ] 2.4 After persisting to state file, if the charger has `ha_deadline_entity` configured in executor config, fire-and-forget the HA write. Import `HAClient` from `executor/actions.py` and call:
  ```python
  asyncio.create_task(
      ha_client.call_service("input_datetime", "set_datetime",
          entity_id=charger_config.ha_deadline_entity,
          data={"datetime": deadline_str})
  )
  ```
  Wrap in try/except, log warning on failure. Do NOT await — the HTTP response returns immediately. When clearing (deadline=null), call with an empty/default datetime value.
- [ ] 2.5 Return the updated charger state in the response body. Read the state file + merge with live HA sensor data (reuse the same merging logic from Module 4's GET endpoint). Return a single charger object matching the `GET /api/ev/chargers` response shape for that charger.
- [ ] 2.6 Write API tests in `tests/backend/test_ev_deadline_api.py` covering: set deadline + target_pct happy path (verify state file written, verify response shape), clear deadline (null values), invalid charger ID (404), past deadline (422), target_pct=150 (422), target_pct without deadline (422), missing battery_capacity_kwh (422), state file created on first write when file doesn't exist, state file preserves existing fields for other chargers.

## 3. Pipeline State File Integration

**Depends on:** Group 2 (state file helpers and schema), Module 4 (pipeline multi-day logic exists).

- [ ] 3.1 Modify the pipeline's multi-day deadline reading in `planner/pipeline.py`. At the start of the EV section (where Module 4 reads `deadline` and `target_kwh` from config), add a state file read: call `read_ev_state()` from `backend/core/ev_state.py`. For each charger, if the state file has a non-null `deadline` for that charger ID, use the state file values (`deadline`, `target_kwh`) instead of config values. If the state file has no entry or null deadline, fall back to config. Log at debug level which source was used.
- [ ] 3.2 After Module 4's pipeline computes `remaining_kwh`, `daily_quota_kwh`, `quota_schedule`, and `days_remaining` for each multi-day charger, write these fields back to the state file using `write_ev_state()`. Preserve API-written fields (`deadline`, `target_pct`, `target_kwh`, `source`) — do a read-modify-write. Update `last_updated`.
- [ ] 3.3 Implement auto-clear logic in the pipeline: after computing `remaining_kwh`, if `remaining_kwh <= 0` AND the charger has an active deadline, set `deadline`, `target_pct`, and `target_kwh` to null and `status` to `"complete"` in the state file. If `ha_deadline_entity` is configured, fire-and-forget clear the HA entity (same pattern as task 2.4).
- [ ] 3.4 Implement missed deadline detection in the pipeline: after computing `remaining_kwh`, if `datetime.now() > deadline` AND `remaining_kwh > 0`, set `status: "missed"` in the state file. Do NOT clear the deadline.
- [ ] 3.5 Write integration tests in `tests/planner/test_pipeline_ev_state.py` covering: pipeline reads deadline from state file (overrides config), pipeline writes computed fields back to state file (preserves API fields), auto-clear when remaining_kwh=0, missed deadline detection, state file missing (graceful fallback to config).

## 4. HA Bidirectional Sync

**Depends on:** Group 2 (state file helpers), Group 1 (ha_deadline_entity config field).

- [ ] 4.1 Add a `get_ha_datetime(entity_id: str) -> datetime | None` async helper in `backend/core/ha_client.py`. Use the same `httpx.AsyncClient` pattern as existing `get_ha_sensor_float()`. Read the entity state string and parse it as datetime. Handle these formats in order:
  - `"2026-04-11T07:00:00+02:00"` (ISO 8601 with timezone)
  - `"2026-04-11T07:00:00"` (ISO 8601 without timezone → apply system timezone)
  - `"2026-04-11 07:00:00"` (HA default space-separated → apply system timezone)
  Return None with warning log for: `"unknown"`, `"unavailable"`, empty string, time-only values like `"07:00:00"`, or any other unparseable value.
- [ ] 4.2 Add `"input_datetime"` to the allowed domain set in `executor/actions.py`. Locate the domain safety guard (the explicit allowlist around line 349-388 that checks against `sensor`, `binary_sensor` etc.). Add `"input_datetime"` to the writable domains set alongside `"input_number"`, `"input_select"`, etc.
- [ ] 4.3 Implement HA entity subscription in `backend/ha_socket.py`. In the `_build_monitored_entities()` method (around lines 84-192), for each EV charger that has `ha_deadline_entity` configured, add the entity to the monitored map with key `ev_deadline_{idx}` (following the existing `ev_plug_{idx}` pattern). In the state_changed handler section, add a handler for `ev_deadline_{idx}` keys that:
  1. Parses the new state as datetime (same formats as 4.1)
  2. Reads the state file via `read_ev_state()`
  3. Updates the charger's deadline (and computes target_kwh from existing target_pct, defaulting to 80% if no target_pct exists)
  4. Writes back via `write_ev_state()`
  5. Emits a `ev_deadline_changed` Socket.IO event with `{ charger_id, deadline }` for the frontend
- [ ] 4.4 Implement debounce logic in the handler from 4.3. Add a module-level dict `_last_darkstar_write: dict[str, float]` mapping charger_id → timestamp. In task 2.4's fire-and-forget HA write, record the current time in this dict. In the state_changed handler, check if `time.time() - _last_darkstar_write.get(charger_id, 0) < 5.0` — if yes, skip the update (log at debug level "Ignoring HA echo for {charger_id}").
- [ ] 4.5 Implement startup sync in the `_on_connected()` method of `HAWebSocketClient` in `backend/ha_socket.py` (this runs after authentication and initial state fetch, around line 227-230). For each charger with `ha_deadline_entity`: call `get_ha_datetime()` to read the current HA value. Then read the state file. If the state file has no deadline for that charger and HA has a valid datetime, write the HA value to the state file (with default `target_pct: 80`). If the state file already has a deadline, fire-and-forget write the state file value back to HA to resync.
- [ ] 4.6 Write unit tests in `tests/backend/test_ha_deadline_sync.py` covering: `get_ha_datetime()` with each format variant (HA default, ISO, ISO+tz, time-only → None, "unknown" → None), domain allowlist includes `input_datetime`, state_changed handler updates state file, debounce skips echo events within 5s, debounce allows genuine changes after 5s, startup sync HA→state file when state file empty, startup sync state file→HA when state file has deadline.

## 5. Dashboard EV Card — Frontend

**Depends on:** Group 2 (POST API), Module 4 (GET API). Can be developed in parallel with groups 3-4 if the GET/POST API shapes are mocked.

- [ ] 5.1 Add TypeScript types and API client functions in `frontend/src/lib/api.ts`. Add types matching the `GET /api/ev/chargers` response (use the state file schema above as reference for field names). Add:
  ```typescript
  ev: {
    chargers: () => getJSON<EVChargersResponse>('/api/ev/chargers'),
    setDeadline: (id: string, body: { deadline: string | null, target_pct: number | null }) =>
      postJSON<EVChargerState>(`/api/ev/chargers/${id}/deadline`, body),
  }
  ```
- [ ] 5.2 Create a new file `frontend/src/components/EVChargingCard.tsx`. This is the per-charger expandable section. Props interface:
  ```typescript
  interface EVChargingCardProps {
    charger: EVChargerState  // from API types in 5.1
    onDeadlineChange: (id: string, deadline: string | null, targetPct: number | null) => void
  }
  ```
  Render: charger name, plug status icon (use `Plug` or `PlugZap` from lucide-react), SoC percentage badge. Use Tailwind classes following `ResourcesDomain` patterns (e.g., `text-sm text-muted`, `bg-accent/10`, etc.).
- [ ] 5.3 Implement the mode dropdown in `EVChargingCard`. Use a native `<select>` element styled with the Tailwind `.input` class (same as other inputs in the project). Two options: value `"daily"` label "Every day", value `"multi_day"` label "Ready by". Derive initial value from `charger.mode`. When switching to "daily" from "multi_day" and a deadline is active, show a `window.confirm()` dialog: "This will clear your active deadline. Continue?" — if confirmed, call `onDeadlineChange(id, null, null)`.
- [ ] 5.4 Implement the deadline date/time picker. Use native HTML inputs (the project uses native `<input type="date">` already in `CommandDomains.tsx` GridDomain):
  ```tsx
  <input type="date" className="input text-sm" min={todayStr} value={dateStr} onChange={...} />
  <input type="time" className="input text-sm" value={timeStr} onChange={...} />
  ```
  Combine date + time into ISO 8601 string. On change, call `onDeadlineChange(id, isoString, currentTargetPct)`. Only render when mode is "multi_day".
- [ ] 5.5 Implement the target percentage slider. Use a native `<input type="range" min={0} max={100} step={5}>` with a numeric label showing the current value and "%". Default to 80 when no target is set. Debounce API calls by 500ms (use a `setTimeout`/`clearTimeout` pattern). Only call `onDeadlineChange()` when a deadline is already set. Render below the deadline picker.
- [ ] 5.6 Implement the progress bar. Show `energy_delivered_kwh / target_kwh` as a horizontal bar using a `<div>` with Tailwind `bg-accent` fill (same pattern as `ProgressBar` in `CommandDomains.tsx`). Show text: `"{delivered.toFixed(1)} / {target.toFixed(1)} kWh"`. When `remaining_kwh <= 0`, show "Complete" with full bar. Only render when mode is "multi_day" and `target_kwh` is not null.
- [ ] 5.7 Implement today's quota display and status badge. Show `"Today's quota: {daily_quota_kwh.toFixed(1)} kWh"` as text. Show status as a colored badge (use the project's `Badge` component from `frontend/src/components/ui/Badge.tsx` if it exists, otherwise a `<span>` with Tailwind classes):
  - `"on_track"` → green background `bg-good/15 text-good`, label "On track"
  - `"behind"` → amber background `bg-warn/15 text-warn`, label "Behind schedule"
  - `"complete"` → green background `bg-good/15 text-good`, label "Complete"
  - `"missed"` → red background `bg-bad/15 text-bad`, label "Deadline missed — {remaining_kwh.toFixed(1)} kWh remaining"
  - `null` quota → grey `bg-muted/15 text-muted`, label "Quota pending"
- [ ] 5.8 Implement the mini day-by-day quota schedule. Render `quota_schedule` as a flex row of compact day boxes. Each box shows: day label (use `moment(date).format('ddd')`), kWh value rounded to integer, and a small colored bar proportional to the quota relative to the max quota in the schedule. Use `text-xs` sizing. Hide entirely when `quota_schedule` is null or empty array.
- [ ] 5.9 Implement "Clear deadline" button. Render a text button `"Clear deadline"` (use `text-sm text-muted hover:text-bad cursor-pointer` styling). On click, call `onDeadlineChange(id, null, null)`. Only show when a deadline is active.
- [ ] 5.10 Integrate `EVChargingCard` into `ResourcesDomain` in `CommandDomains.tsx`. Replace the existing simple EV kWh line (around the `hasEvCharger` conditional block) with an expandable section. The collapsed state shows the existing one-line summary: EV icon + total kWh. Add a `ChevronDown` icon (from lucide-react) that rotates on expand. The expanded state renders one `EVChargingCard` per charger from the API data.
- [ ] 5.11 Add state management and data fetching to `Dashboard.tsx`. Add state: `const [evChargers, setEvChargers] = useState<EVChargerState[]>([])`. Fetch `Api.ev.chargers()` on mount and on a 60-second `setInterval`. Also listen for `useSocket('ev_deadline_changed', ...)` to trigger an immediate refetch. Pass `evChargers` down to `ResourcesDomain` as a new prop. Implement the `onDeadlineChange` callback that calls `Api.ev.setDeadline()` then refetches.
- [ ] 5.12 Show HA entity info tip: when a charger is in "Ready by" mode (mode dropdown set to multi_day) but `ha_deadline_entity` is empty/null in the charger config, render a subtle banner below the controls: `"Tip: Connect a Home Assistant input_datetime helper in Settings → EV Chargers to enable voice control and automations."` Use `text-xs text-muted` styling with an info icon (`Info` from lucide-react).

## 6. End-to-End Verification

**Depends on:** All previous groups complete.

- [ ] 6.1 Write an E2E test (`tests/e2e/test_ev_multi_day_e2e.py`) for the full write→plan→read flow: call `POST /api/ev/chargers/ev_charger_1/deadline` with deadline 3 days out and target_pct=80 → verify state file has correct deadline, target_pct, target_kwh → trigger a planner run (call the pipeline function directly with mocked price forecasts and HA sensors) → verify state file now has remaining_kwh, daily_quota_kwh, quota_schedule, status → call `GET /api/ev/chargers` → verify response includes all fields for the charger with mode="multi_day".
- [ ] 6.2 Write an E2E test for HA sync: mock the HA websocket connection → simulate a `state_changed` event for `input_datetime.ev_departure_tesla` with value `"2026-04-11 07:00:00"` → verify state file updated with the new deadline → call `GET /api/ev/chargers` → verify response reflects the HA-set deadline.
- [ ] 6.3 Write an E2E test for auto-clear: set a deadline via POST API → mock the pipeline computing remaining_kwh=0 → verify state file deadline is cleared (null) → verify `GET /api/ev/chargers` returns status="complete" and null deadline.
- [ ] 6.4 Write a backward-compatibility test: configure an EV charger with only `departure_time: "07:00"` (no deadline, no target_pct, no state file) → run the full pipeline → verify no quota constraint applied → verify `GET /api/ev/chargers` returns mode="daily" with null multi-day fields.
