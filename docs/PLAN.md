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

### [DRAFT] REV // F65 — Cumulative Sensor Validation Gap

**Goal:** Make cumulative energy sensors (`total_*`) and today's sensors (`today_*`) REQUIRED for proper operation. These are critical for forecasting, ML, and dashboard functionality - NOT optional.

**Context:** Investigation of Sungrow beta tester revealed:
1. `total_load_consumption` was empty in config
2. Planner forecasting silently fell back to dummy sine wave profile (~0.2-0.8 kWh/slot)
3. No warning was shown in health checks
4. "Today's Stats" worked (uses `today_*` sensors) but ChartCard forecast was wrong

**Critical Finding:** These sensors are NOT optional - they are essential for:
- **Forecasting accuracy** (`total_*` sensors provide historical load patterns)
- **ML model training** (`total_*` sensors required for Aurora learning)
- **Dashboard "Today's Stats"** (`today_*` sensors for real-time daily totals)
- **Backfill calculations** (`total_grid_import/export` for energy accounting)

Without these sensors, Darkstar cannot function correctly.

**Root Cause:** The `sensor_requirements` dict in `backend/health.py:468-481` only validates:
- `load_power`, `pv_power`, `grid_power` (real-time power sensors)
- Optional sensors for features (`water_power`, etc.)

Missing from validation:
- `total_load_consumption` (required for forecasting)
- `total_pv_production` (required for ML/forecasting)
- `total_grid_import`, `total_grid_export` (required for backfill)
- `total_battery_charge`, `total_battery_discharge` (required for ML)

**Sensor Types:**
| Type | Examples | Used By | Currently Validated? |
|------|----------|---------|---------------------|
| Real-time Power | `load_power`, `pv_power` | Recorder, live metrics | ✅ Yes |
| Today's Totals | `today_load_consumption` | Dashboard "Today's Stats" | ❌ No |
| Cumulative/Lifetime | `total_load_consumption` | Forecasting, ML | ❌ No |

**Plan:**

#### Phase 1: Add Cumulative Sensors to Health Validation [DRAFT]
* [ ] Add `total_load_consumption` to `sensor_requirements` dict in `backend/health.py`
* [ ] Add `total_pv_production` to validation
* [ ] Add `total_grid_import`, `total_grid_export` to validation
* [ ] Add `total_battery_charge`, `total_battery_discharge` to validation
* [ ] Mark as required when `learning.enable: true` (forecasting needs these)

#### Phase 2: Add Today's Sensors to Health Validation [DRAFT]
* [ ] Add `today_load_consumption` to validation
* [ ] Add `today_pv_production` to validation
* [ ] Add `today_grid_import`, `today_grid_export` to validation
* [ ] These are used by Dashboard "Today's Stats" card

#### Phase 3: Add Forecasting-Specific Warnings [DRAFT]
* [ ] In health check, if `learning.enable: true` AND any `total_*` sensor is missing:
    * Add warning: "Forecasting may use inaccurate fallback data"
    * List which sensors are missing
* [ ] Add similar warning for "Today's Stats" if `today_*` sensors missing

#### Phase 4: Improve Fallback Behavior [DRAFT]
* [ ] Log warning when forecasting falls back to HA profile due to missing `total_load_consumption`
* [ ] Log warning when HA profile fallback is used (entity empty or fetch failed)
* [ ] Add health status "degraded" when using fallback data

#### Phase 4: Add Cumulative Sensors to Profile Required Entities [DRAFT]
* [ ] Add cumulative sensors to `entities.required` in all inverter profiles:
  - `total_load_consumption` (all profiles)
  - `total_pv_production` (all profiles)
  - `total_grid_import`, `total_grid_export` (all profiles)
  - `total_battery_charge`, `total_battery_discharge` (all profiles)
* [ ] Add today's sensors to `entities.required` in all profiles:
  - `today_load_consumption`, `today_pv_production`
  - `today_grid_import`, `today_grid_export`
  - `today_battery_charge`, `today_battery_discharge`
* [ ] Update frontend field definitions to map to profile entities
* [ ] Verify ProfileSetupHelper shows missing required sensors correctly

#### Phase 5: Test & Verify [DRAFT]
* [ ] Test: Empty `total_load_consumption` shows health warning
* [ ] Test: Empty `today_load_consumption` shows health warning
* [ ] Test: UI shows required markers (red asterisk) on all cumulative/today sensors
* [ ] Test: Form validation prevents save with empty required fields
* [ ] Test: With all sensors configured, no warnings
* [ ] Run `uv run ruff check .`
* [ ] Run `pnpm lint` in frontend

---

### [DRAFT] REV // F68 — Advanced Tab showIf & inverter_profile Preservation

**Goal:** Fix two post-deployment bugs: (1) Inverter Logic card blank in Advanced settings, (2) Config migration resetting inverter_profile.

**Context:**
1. **Advanced Tab showIf Bug**: `AdvancedTab.tsx:47` renders ALL sections without checking `showIf` conditions. "Inverter Logic" section has `showIf: { configKey: 'system.inverter_profile', value: 'generic' }` but it's ignored, causing blank card.
2. **inverter_profile Reset**: Config migration overwrites user's `system.inverter_profile: deye` → `generic` (default).

**Plan:**

#### Phase 1: Fix Advanced Tab showIf Filtering [DRAFT]
* [x] Update `AdvancedTab.tsx` to evaluate `showIf` conditions before rendering each section
* [x] Section only renders if `showIf` condition passes or is undefined
* [x] Add `showIf` to "Inverter Logic" section in `types.ts`
* [x] Test: Inverter Logic card shows when `inverter_profile: generic`, hidden otherwise

#### Phase 2: Fix Config Migration Preserving inverter_profile [DRAFT]
* [x] Add `migrate_root_inverter_profile` function to move inverter_profile from root to system
* [x] Add migration to legacy_steps list
* [x] Test: Config with `inverter_profile: deye` preserves value after migration
