# Darkstar Energy Manager: Active Plan

**Vision: From Calculator to Agent**
Darkstar is transitioning from a deterministic optimizer (v1) to an intelligent energy agent (v2). It does not just optimize based on static config; it observes context (Weather, Vacation, Prices), predicts outcomes (Aurora ML), and actively strategizes (Strategy Engine) to maximize efficiency and comfort.

---

| Prefix  | Area                 | Examples |
| ------- | -------------------- | -------- |
| **K**   | Kepler (MILP solver) | F41      |
| **E**   | Executor             | E1       |
| **A**   | Aurora (ML)          | A29      |
| **H**   | History/DB           | H1       |
| **O**   | Onboarding           | O1       |
| **UI**  | User Interface       | UI2      |
| **DS**  | Design System        | DS1      |
| **F**   | Fixes/Bugfixes       | F6       |
| **DX**  | Developer Experience | DX1      |
| **ARC** | Architecture         | ARC1     |
| **IP**  | Inverter Profiles    | IP1      |

---

## 🤖 AI Instructions (Read First)

1.  **Structure:** This file is a **chronological stream**. Newest items are at the **bottom**.

2.  **No Reordering:** Never move items. Only update their status or append new items.

3.  **Status Protocol:**

    -   Update the status tag in the Header: `### [STATUS] REV // ID00 — Title`

    -   Allowed Statuses: `[DRAFT]`, `[PLANNED]`, `[IN PROGRESS]`, `[DONE]`, `[PAUSED]`, `[OBSOLETE]`.

4.  **New Revisions:** Always use the template below.

5.  **Cleanup:** When this file gets too long (>10 completed REV's), notify the user.


### Revision Template

```

### [STATUS] REV // ID — Title

**Goal:** Short description of the objective.
**Context:** Short description of the context and issues.

**Plan:**

#### Phase 1: [STATUS]
* [ ] Step 1
* [ ] Step 2

#### Phase 2: [STATUS]
* [ ] Step 1
* [ ] Step 2

```

---

## REVISION STREAM:

---

### [PLANNED] REV // K22 — Effekttariff (Active Guard)

**Goal:** Implement a dual-layer strategy (Planner + Executor) to minimize peak power usage ("Effekttariff").

**Plan:**

#### Phase 1: Configuration & Entities [PLANNED]
* [ ] Add `grid.import_breach_penalty_sek` (Default: 5000.0) to `config.default.yaml`.
* [ ] Add `grid.import_breach_penalty_enabled` (Default: false) to `config.default.yaml`.
* [ ] Add `grid.import_breach_limit_kw` (Default: 11.0) for the hard executor limit.
* [ ] Add override entities to `executor.config`.
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

#### Phase 2: Planner Logic (Economic) [PLANNED]
* [ ] **Planner Logic:** Pass the penalty cost to Kepler if enabled.
* [ ] **Re-planning:** Trigger re-plan if penalty configuration changes.
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

#### Phase 3: Executor Active Guard (Reactive) [PLANNED]
* [ ] **Monitor:** In `executor/engine.py` `_tick`, check `grid_import_power` vs `import_breach_limit_kw`.
* [ ] **Reactive Logic:**
    *   If Breach > Limit:
        *   Trigger `ForceDischarge` on Battery (Max power).
        *   Trigger `Disable` on Water Heating.
        *   Log "Grid Breach Detected! Engaging Emergency Shedding".
* [ ] **Recovery:** Hysteresis logic to release overrides when grid import drops.
* [ ] **Frontend:** Add controls to `Settings > Grid`.
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

---

### [DRAFT] REV // K26 — Inverter Clipping Support

**Goal:** Correctly model DC vs AC inverter limits in the Kepler solver to prevent over-optimistic planning on high-PV systems.
**Context:** User has a 15kWp array but a 10kW (AC) / 12kW (DC-Input) inverter. Current model assumes all PV is available at the AC bus.

**Plan:**

#### Phase 1: Configuration & Schema [DRAFT]
* [ ] Add `inverter.max_pv_input_kw` (DC limit) and `inverter.max_ac_output_kw` (AC limit) to `config.default.yaml`.
* [ ] Deprecate/Migration: Map old `system.inverter.max_power_kw` to `max_ac_output_kw`.
* [ ] **USER VERIFICATION:** Confirm schema covers all hardware limits (Access Power vs Input Power).

#### Phase 2: Solver Logic (DC Bus) [DRAFT]
* [ ] **Kepler Model:** Introduce `pv_to_ac[t]` and `discharge_to_ac[t]` variables.
* [ ] **Constraint:** `pv_actual[t] + discharge_dc[t] == charge_dc[t] + ac_produced[t]`.
* [ ] **Constraint:** `ac_produced[t] <= inverter_ac_limit`.
* [ ] **Constraint:** `pv_actual[t] <= inverter_pv_dc_limit`.
* [ ] Verify with test case (15kW PV, 10kW AC, 12kW DC battery charge).

#### Phase 3: Input Pipeline [DRAFT]
* [ ] **Inputs:** Update `inputs.py` to optionally clip forecasts early (for heuristic simplicity) or pass through raw data.
* [ ] **UI:** Show "Clipped Solar" in the dashboard forecast chart.


---

### [DRAFT] REV // F64 — EV Node Tooltip for Multiple EVs

**Goal:** Add a tooltip to the PowerflowCard EV node that shows detailed information about all configured EVs when hovering.

**Context:** The PowerflowCard currently shows only the first enabled EV's data (power, SoC, plug status). When multiple EVs are configured, users can't see individual EV details. A tooltip on hover should display:
- Total number of EVs
- Individual EV names
- Individual power draw (kW)
- Individual SoC (%)
- Plug status for each EV

**Backend Status:** Already aggregates correctly in `planner/solver/adapter.py` (sums max power, etc.). The issue is frontend display only shows first EV.

**Plan:**

#### Phase 1: Backend - Pass All EV Data to Frontend [DRAFT]
* [ ] Update `backend/ha_socket.py` to include all EV data in `emit_live_metrics` payload
* [ ] Change from single `ev_kw`, `ev_soc`, `ev_plug_in` to array `ev_chargers: [{name, kw, soc, plugged_in}]`
* [ ] Test: WebSocket payload contains all EV details

#### Phase 2: Frontend - Update API Types [DRAFT]
* [ ] Update `frontend/src/lib/api.ts` to reflect new EV charger array in `LiveMetrics`
* [ ] Add proper TypeScript types for individual EV charger data

#### Phase 3: Frontend - Update PowerflowCard EV Node [DRAFT]
* [ ] Add tooltip component to EV node in `PowerFlowCard.tsx`
* [ ] Tooltip shows on hover with:
  - "X EVs" header
  - List of each EV with name, power, SoC, plug status
* [ ] Tooltip styling: dark background, rounded corners, max-height with scroll if many EVs

#### Phase 4: Backend - Aggregation Fallback [DRAFT]
* [ ] For backward compatibility: If frontend expects old format, provide aggregate values
* [ ] Or: Version the WebSocket API with compatibility layer

#### Phase 5: Test & Lint [DRAFT]
* [ ] Test with single EV - tooltip shows single EV details
* [ ] Test with multiple EVs - tooltip shows all EVs
* [ ] Run `pnpm lint` - fix any errors
* [ ] Build succeeds

---

### [PLANNED] REV // F67 — Aurora PV Forecast Pipeline Fix

**Goal:** Fix 5 bugs in the Aurora ML pipeline causing 7-8x PV forecast underestimation on sunny days.

**Context:** Investigation revealed that the Aurora PV model effectively ignores weather data due to a
resolution mismatch between hourly Open-Meteo data and 15-min observation slots. This, combined with
an overly restrictive corrector clamp and a slow/diluted Reflex feedback loop, results in the model
predicting "average PV for this time of day" regardless of weather conditions. On sunny days this
means 7-8x under-prediction (e.g. forecast 2 kWh vs actual 14.5 kWh). The confidence scaling at 83%
further amplifies the error.

**Bugs addressed:**

1. **Weather resolution mismatch** — Open-Meteo returns hourly data but slots are 15-min; 75% of training rows have NaN weather features, so the model ignores radiation.
2. **Corrector clamp ±50%** — Even when the corrector detects a huge error, it can only adjust by half the base forecast.
3. **Reflex night-slot dilution** — PV bias is averaged across ALL slots including nighttime zeros, drowning the daytime under-prediction signal.
4. **Reflex too slow** — Confidence changes ±2%/day, takes 9 days to recover; capped at 80-100% so it can never compensate a 7x error.
5. **Confidence amplifies under-prediction** — Multiplying an already-too-low forecast by 0.83 makes it worse.

**Plan:**

#### Phase 1: Weather Interpolation (Bug #1) [PLANNED]
* [ ] In `ml/weather.py`: After fetching hourly data, resample to 15-min using linear interpolation: `weather_df.resample("15min").interpolate(method="linear")`
* [ ] Ensure this applies to `temp_c`, `cloud_cover_pct`, and `shortwave_radiation_w_m2`
* [ ] Verify interpolated DataFrame has 4x the rows, no NaN gaps between hours
* [ ] This fix automatically improves both `ml/train.py` and `ml/forward.py` since both call `get_weather_series`
* [ ] Add unit test: mock hourly weather → verify 15-min output with correct interpolated values

#### Phase 2: Corrector Clamp (Bug #2) [PLANNED]
* [ ] In `ml/corrector.py` `_clamp_correction`: Change `max_abs = 0.5 * base` → `max_abs = 2.0 * base`
* [ ] Add unit test: verify corrections up to 200% are allowed

#### Phase 3: Reflex Improvements (Bugs #3, #4, #5) [PLANNED]
* [ ] In `backend/learning/store.py` `get_forecast_vs_actual`: Add filter `actual > 0.01` when target is "pv" to exclude night slots from bias calculation
* [ ] In `backend/learning/reflex.py`: Change `MAX_DAILY_CHANGE["forecasting.pv_confidence_percent"]` from `2.0` → `5.0`
* [ ] In `backend/learning/reflex.py`: Change `BOUNDS["forecasting.pv_confidence_percent"]` from `(80, 100)` → `(70, 120)`
* [ ] Update existing `tests/test_reflex.py` if any assertions check the old bounds/rate values

#### Phase 4: Verification [PLANNED]
* [ ] Run `uv run python -m pytest tests/test_aurora_forward.py -v`
* [ ] Run `uv run python -m pytest tests/test_reflex.py -v`
* [ ] Run `uv run ruff check ml/ backend/learning/reflex.py backend/learning/store.py`
* [ ] Local smoke test: run training script and verify weather features are populated (not NaN) in training logs

---
