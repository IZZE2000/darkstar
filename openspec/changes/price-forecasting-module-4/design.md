## Context

Darkstar's EV charging is currently single-day: each charger has a `departure_time` (HH:MM) and the pipeline calculates the next occurrence as a deadline. Kepler optimizes all charging within the 24-48h Nordpool horizon up to that deadline. There is no concept of "charge over several days."

With Module 1 delivering 7-day price forecasts (p10/p50/p90 spot prices per slot), the system can now identify which days are cheapest and distribute charging accordingly. The deferral controller sits *above* Kepler as a strategic layer — it decides *how much* to charge each day, while Kepler decides *when* within each day.

Key existing code:
- `planner/pipeline.py`: Orchestrates forecast fetch, S-Index, and Kepler. Calculates per-device EV deadlines (line ~536-593).
- `planner/solver/kepler.py`: MILP solver with per-device `ev_energy[d][t]` variables and deadline constraints.
- `planner/solver/adapter.py`: Converts config + state into `KeplerInput`. `EVChargerInput` has `deadline: datetime | None`.
- `executor/config.py`: Parses `EVChargerDeviceConfig` with `departure_time: str | None`.
- Module 1 delivers price forecasts via `price_forecasts` DB table with `spot_p50` per slot and `days_ahead`.

## Goals / Non-Goals

**Goals:**
- Build a reusable `MultiDayPlanner` that distributes energy across days based on price forecasts
- Integrate it with EV charging as the first consumer
- Preserve existing single-day `departure_time` behavior as the default
- Make the controller agnostic to load type (EV today, potentially pool heaters or other deferrable loads tomorrow)
- Recalculate quotas daily so forecast errors self-correct

**Non-Goals:**
- Modifying Kepler's MILP formulation (Kepler receives a daily quota as input, not a multi-day horizon)
- Supporting intra-day deadline changes (user sets deadline once, it stays)
- Building a UI for setting multi-day deadlines (future work; initially config-only or HA input_datetime)
- Supporting non-EV deferrable loads in this change (architecture supports it, but only EV is wired up)

## Decisions

### 1. Controller placement: Strategy layer, not solver layer

The `MultiDayPlanner` lives in `planner/strategy/` alongside the S-Index. It runs *before* Kepler in the pipeline and passes a `daily_quota_kwh` to the adapter, which becomes an upper bound on total EV energy for that charger in today's solve.

**Why not extend Kepler to a 7-day horizon?** Kepler uses exact Nordpool prices and a 15-min slot resolution. A 7-day MILP at 15-min resolution = 672 slots with binary EV variables per device — too slow, and we don't have real prices beyond D+1. The two-layer approach (strategic allocation + tactical optimization) is both faster and safer.

**Alternative considered:** Passing forecast prices directly to Kepler for D+2-D+7 slots. Rejected because mixing real and forecast prices in the same MILP creates false precision — Kepler would optimize against forecast prices as if they were certain.

### 2. Quota algorithm: Weighted cost allocation

The `MultiDayPlanner` receives daily average spot prices (p50) for each remaining day until the deadline. It allocates more kWh to cheaper days using an inverse-price weighting:

```
weight[day] = 1 / avg_price[day]
quota[day] = (weight[day] / sum(weights)) * remaining_kwh
```

With guardrails:
- **Minimum daily quota**: On every day except the last, at least `min_daily_fraction` (e.g., 10%) of remaining energy is allocated to prevent over-deferral.
- **Last-day safety**: If only 1 day remains, all remaining energy is allocated (no deferral possible).
- **Charger power cap**: Daily quota cannot exceed `max_power_kw * available_hours` for that day.

**Why inverse-price weighting over threshold-based?** Threshold approaches ("only charge below X SEK/kWh") risk allocating nothing on expensive weeks. Inverse weighting always produces a valid allocation — it just biases toward cheaper days.

### 3. Daily recalculation with carry-forward

Each planner run:
1. Read the charger's `energy_delivered_kwh` (from `slot_observations` or HA sensor).
2. Compute `remaining_kwh = target_kwh - energy_delivered_kwh`.
3. Fetch fresh price forecasts for remaining days.
4. Re-run the quota algorithm on `remaining_kwh` across remaining days.

This naturally handles forecast errors: if yesterday's "cheap day" wasn't actually cheap and less was charged, today's quota adjusts upward.

### 4. Config: `ev_deadline` as optional per-charger field

Add an optional `deadline` field to each EV charger config entry:

```yaml
ev_chargers:
  - id: ev_charger_1
    departure_time: "07:00"      # Existing: daily departure
    deadline: "2026-04-04T07:00"  # New: multi-day deadline (ISO datetime)
    target_kwh: 60                # New: total energy needed by deadline
```

When `deadline` is set AND `price_forecast.enabled` is true:
- The `MultiDayPlanner` computes today's quota
- `departure_time` is ignored for deadline purposes (the multi-day deadline governs)
- Once the deadline passes, the field is effectively inert until the user sets a new one

When `deadline` is absent or `price_forecast.enabled` is false:
- Existing `departure_time` single-day behavior applies unchanged

The `target_kwh` field is required when using multi-day mode. It represents the total energy the user wants delivered by the deadline. This could alternatively be derived from `battery_capacity_kwh` and desired SoC, but explicit kWh is simpler and works for non-EV loads too.

### 5. Kepler integration: Daily quota as EV energy upper bound

The adapter passes a `daily_quota_kwh` field on each `EVChargerInput`. In Kepler, this adds one constraint per charger in multi-day mode:

```
sum(ev_energy[d][t] for t in today_slots) <= daily_quota_kwh[d]
```

The existing deadline constraint still applies (using the multi-day deadline datetime instead of daily departure). All other EV constraints (discharge blocking, grid-only, incentive buckets) remain unchanged.

### 6. Pipeline wiring

In `planner/pipeline.py`, after S-Index calculation and before adapter conversion:

1. For each EV charger with a `deadline` set:
   a. Fetch 7-day price forecast (p50 daily averages)
   b. Calculate `remaining_kwh` from `target_kwh - energy_delivered_kwh`
   c. Call `MultiDayPlanner.compute_quota(remaining_kwh, deadline, daily_prices)`
   d. Attach `daily_quota_kwh` to the charger state dict
2. Adapter reads `daily_quota_kwh` from state and sets it on `EVChargerInput`
3. Kepler adds the quota constraint if `daily_quota_kwh` is not None

### 7. Read-only EV charger state API

Module 5 needs a way to read the computed multi-day state. Rather than coupling the frontend to internal planner data structures, Module 4 exposes a clean read-only endpoint.

**Endpoint:** `GET /api/ev/chargers`

**New router:** `backend/api/routers/ev.py`

**Response shape:**
```json
{
  "chargers": [
    {
      "id": "ev_charger_1",
      "name": "Tesla",
      "mode": "multi_day",
      "plugged_in": true,
      "soc_percent": 35.0,
      "power_kw": 7.4,
      "departure_time": "07:00",
      "deadline": "2026-04-04T07:00:00+02:00",
      "target_kwh": 60.0,
      "remaining_kwh": 36.9,
      "energy_delivered_kwh": 23.1,
      "daily_quota_kwh": 15.0,
      "days_remaining": 3,
      "quota_schedule": [
        { "date": "2026-04-01", "quota_kwh": 15.0, "avg_price_sek": 0.45 },
        { "date": "2026-04-02", "quota_kwh": 25.0, "avg_price_sek": 0.28 },
        { "date": "2026-04-03", "quota_kwh": 20.0, "avg_price_sek": 0.35 }
      ],
      "status": "on_track"
    }
  ]
}
```

**Fields:**
- `mode`: `"multi_day"` | `"daily"` | `"none"` — which scheduling mode is active
- `plugged_in`, `soc_percent`, `power_kw`: Live values from HA sensors (same source as `/api/system/status`)
- `departure_time`: The configured daily departure time (always present if set)
- `deadline` through `quota_schedule`: Multi-day state from the planner's last run (null when `mode != "multi_day"`)
- `status`: `"on_track"` (remaining_kwh achievable in remaining days), `"behind"` (may not complete), `"complete"` (remaining_kwh ≤ 0), `"idle"` (no active deadline)

**State persistence:** The pipeline writes the computed multi-day state per charger to a lightweight JSON state file (`data/ev_multi_day_state.json`) at the end of each run. The API endpoint reads this file and merges with live HA sensor data. This avoids adding a new DB table for transient state that changes every 30 minutes.

**Why a new router?** EV charging is growing into a distinct feature area (Module 4 backend, Module 5 UI + HA sync). A dedicated `/api/ev/` router keeps it organized and avoids bloating the system status endpoint with multi-day fields.

## Risks / Trade-offs

**[Risk] Forecast is badly wrong, too little energy allocated to early days** → Mitigation: Daily recalculation redistributes remaining energy. Minimum daily fraction prevents zero-allocation days. Last day gets all remaining energy regardless of price.

**[Risk] User forgets to update/clear deadline after trip** → Mitigation: Once deadline passes and `remaining_kwh <= 0`, the controller becomes inert. System falls back to normal `departure_time` behavior. Could add a log warning when deadline is in the past.

**[Risk] `target_kwh` is hard for users to estimate** → Mitigation: Future UI could compute this from current SoC + desired SoC + battery capacity. For now, explicit kWh is the simplest correct approach. Documentation should provide examples.

**[Risk] Power cap calculation needs charger availability hours** → Mitigation: Assume charger is available all day except during `departure_time` hours. For the current day, available hours = hours remaining today. Conservative assumption is fine since Kepler handles the actual scheduling.

**[Trade-off] Config-only deadline vs HA entity** → Starting with config is simpler but requires restarting the planner to change deadlines. Module 5 will add HA `input_datetime` entity sync and a dashboard UI for dynamic deadline setting. This module focuses on the backend plumbing only.

**[Risk] No way to verify multi-day state without UI** → Mitigation: A read-only API endpoint (`GET /api/ev/chargers`) exposes the computed multi-day state per charger. This lets Module 5's frontend consume it, and also allows manual verification during development/testing via curl.
