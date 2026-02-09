# Darkstar Energy Manager: Active Plan

**Vision: From Calculator to Agent**
Darkstar is transitioning from a deterministic optimizer (v1) to an intelligent energy agent (v2). It does not just optimize based on static config; it observes context (Weather, Vacation, Prices), predicts outcomes (Aurora ML), and actively strategizes (Strategy Engine) to maximize efficiency and comfort.

---

## Revision Naming Conventions

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

### [DONE] REV // F52 — Composite Mode Entities Sungrow & Auto mode Fronius fixes

**Goal:** Ensure composite mode entity changes (e.g., Sungrow `forced_charge_discharge_cmd`, `export_power_limit`) are properly logged to executor history and visible to users.
**Context:** Beta tester reported Sungrow "Battery Forced Charge/Discharge Command" not being set. Investigation revealed that while the code DOES call HA to set composite mode entities, these changes are NOT logged to executor history. This makes debugging impossible - users cannot verify what entities are being changed via the executor API. The root cause is in `executor/actions.py:421-441` where composite mode changes make direct HA calls without creating `ActionResult` objects.

**Plan:**

#### Phase 1: Fix Composite Mode Action Logging [DONE]
* [x] Refactor composite mode entity loop in `[executor/actions.py]` to create `ActionResult` objects for each entity change.
* [x] Return composite mode `ActionResult` list from `_set_work_mode()` method.
* [x] Update `execute()` method to collect and include composite mode results in final `action_results` list.
* [x] Add verification for composite mode entity changes.
* [x] Update log messages to include `ActionResult` details.
* [x] Verify with Sungrow profile and idempotent behavior.

#### Phase 2: Frontend History Display [DONE]
* [x] Update executor history UI to display composite mode entity changes.
* [x] Ensure `action_results` from API includes all composite mode actions.
* [x] Display entity ID and value changes in history table or detail view.
* [x] Differentiate composite mode actions from primary mode changes visually (grouped/indented).

#### Phase 3: Documentation & User Guide [DONE]
* [x] Document composite mode behavior in inverter profile documentation.
* [x] Explain that some modes require setting multiple HA entities.
* [x] Provide examples (Sungrow charge_from_grid sets `ems_mode` + `forced_charge_discharge_cmd` + `export_power_limit`).
* [x] Explain that all entity changes are logged to executor history.
* [x] Add FAQ entry for "Executor not setting entity" - how to check history logs.

#### Phase 4: Ambiguous Mode Resolution Fix (Sungrow) [DONE]
* [x] Fix ambiguity between "Charge from Grid" and "Export" modes for profiles like Sungrow where the main mode string is identical.
* [x] Update `_set_work_mode` to accept `is_charging` flag.
* [x] Implement `_resolve_profile_mode` helper to prioritize `charge_from_grid` when `is_charging=True`.
* [x] Pass `decision.grid_charging` from `execute()` to `_set_work_mode()`.
* [x] Verify that "Forced Charge" command is correctly applied in Sungrow profile.

#### Phase 5: Fix Error Visibility - Display HA API Error Messages [DONE]
* [x] Add `error_details: str | None = None` field to `ActionResult` dataclass in `[executor/actions.py]`.
* [x] Create `HACallError` exception class with HTTP status, response body, exception type in `[executor/actions.py]`.
* [x] Modify `call_service()` to raise `HACallError` on error.
* [x] Update HA wrapper methods to raise `HACallError` on validation failure.
* [x] Update all action methods to catch `HACallError` and populate `error_details`.
* [x] Update action_results dict conversion to include `error_details` in `[executor/engine.py]`.
* [x] Update result["actions"] dict conversion to include `error_details`.
* [x] Update error tracking (`recent_errors`) to include `error_details`.
* [ ] Frontend Verification: Test error display by setting an invalid value (requires real Fronius inverter).

#### Phase 6: Fix Max Export Power Logic for Fronius - Skip in Auto Mode [DONE]
* [x] Add `skip_export_power: bool = False` field to `WorkMode` dataclass in `[executor/profiles.py]`.
* [x] Add `skip_export_power: true` to both `zero_export` and `self_consumption` modes in `[profiles/fronius.yaml]`.
* [x] Add mode-aware skip logic in `_set_max_export_power()` in `[executor/actions.py]`.
* [x] Fronius profile tests passing: `test_fronius_profile_parsing`, `test_fronius_grid_charging_skipped`, `test_fronius_controller_decisions`, `test_fronius_watt_limit_execution`.

#### Phase 7: Fix Sungrow max_discharge_power - Set to Inverter Max for All Modes Except Idle [DONE]
* [x] Add `max_discharge_power: 9000` and `skip_discharge_limit: true` to Export, Zero Export, Self-Consumption, and Charge from Grid modes in `[profiles/sungrow.yaml]`.
* [x] Update logic mapping table in `[profiles/sungrow_logic.md]` to show Max Discharge = 9000W for all modes except Idle (10W).
* [x] Verify `_set_discharge_limit()` respects `skip_discharge_limit` flag and composite mode values.
* [x] Verify composite mode entity loop correctly sets `max_discharge_power`.
* [x] Profile loading test, linting, and pytest all pass.

---

### [PLANNED] REV // UI19 — Custom Date Picker for Grid & Financial Card

**Goal:** Add custom date range selection to the Grid & Financial card, matching the Executor History date picker implementation.
**Context:** Users currently have preset options (Today, Yesterday, 7 Days, 30 Days) but cannot select arbitrary date ranges for financial analysis.

**Plan:**

#### Phase 1: Frontend UI Updates [PLANNED]
* [ ] Update period type in CommandDomains.tsx to include 'custom': `'today' | 'yesterday' | 'week' | 'month' | 'custom'`
* [ ] Add state for startDate and endDate (string type, YYYY-MM-DD format)
* [ ] Add "Custom" button to period selector
* [ ] Show date input fields (start date, "to", end date) below period buttons when period is 'custom' (matching Executor History layout)
* [ ] Add production-grade validation: prevent end date before start date, show inline error message
* [ ] Update "Net Cost" label to show "Custom Period Cost" when using custom range

#### Phase 2: Frontend Data Fetching [PLANNED]
* [ ] Calculate default dates when switching to Custom (start date = previous period start, end date = today)
* [ ] Modify API call to pass start_date and end_date query parameters when period is 'custom'
* [ ] Handle loading states for custom date changes
* [ ] Add error handling for invalid date ranges

#### Phase 3: API Layer Updates [PLANNED]
* [ ] Update energyRange function in api.ts to accept optional start_date and end_date parameters
* [ ] Build query string with custom dates: `/api/energy/range?period=custom&start_date=${startDate}&end_date=${endDate}`
* [ ] Update EnergyRangeResponse type to include 'custom' as valid period value

#### Phase 4: Backend API Updates [PLANNED]
* [ ] Add optional query parameters: start_date: str | None = None, end_date: str | None = None in services.py get_energy_range endpoint
* [ ] Parse YYYY-MM-DD format dates and convert to timezone-aware datetime
* [ ] If custom dates are provided, use them instead of period-based calculation
* [ ] Skip real-time HA sensor overlay for custom periods (only apply to "today" preset)
* [ ] Add validation for date range validity on backend

#### Phase 5: Testing & Verification [PLANNED]
* [ ] Test custom date range with valid dates
* [ ] Test validation for invalid ranges (end date before start date)
* [ ] Verify default dates populate correctly when switching from presets
* [ ] Test with various date ranges (single day, week, month, multi-month)
* [ ] Verify financial calculations are correct for custom ranges
* [ ] Lint and type check all changes
