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


### [DONE] REV // IP5 — Sungrow & Fronius Logic Fixes

**Goal:** Fix override logic to respect profile modes and update Sungrow profile with correct entities and behaviors.
**Context:** "Zero Export To CT" is hardcoded in `override.py`, causing Sungrow inverters to fail during low SoC events. Sungrow integration has also updated entity names.

**Plan:**

#### Phase 1: Backend Logic & Profile Update [DONE]
* [x] **Profile (`sungrow.yaml`):** Updated to mkaiser v2 integration entity names (`select.ems_mode`, `number.battery_max_charge_power`, etc.).
* [x] **Profile (`sungrow.yaml`):** Update `forced_power` entity name to `number.battery_forced_charge_discharge_power`.
* [x] **Profile (`sungrow.yaml`):** Fix Idle mode: use `Stop (default)` with `max_discharge_power=10` (not 0).
* [x] **Backend (`actions.py`):** Fix `_set_charge_limit` to set BOTH `forced_power` AND `max_charge_power` in forced charge mode.
* [x] **Backend (`actions.py`):** Fix `_set_discharge_limit` to set BOTH `forced_power` AND `max_discharge_power` in forced discharge mode.
* [x] **Backend (`actions.py`):** Standardize `forced_power_entity` search to check for both `forced_power` and legacy `forced_power_entity` in `custom_entities`.
* [x] **Backend (`override.py`):** Remove hardcoded `work_mode` from `actions` dict (Emergency/Low SoC/Fallback).
* [x] **Backend (`controller.py`):** Verify `defaults` fall back to `profile.modes.zero_export`.
* [x] **Backend (`controller.py`):** Force "W" units for Sungrow in `_calculate_charge_limit`.
* [x] **Profile (`sungrow.yaml`):** Update `behavior.min_charge_w` from 100 to 10.
* [x] **Frontend (`SystemTab.tsx`):** Hide `control_unit` selector when `profile.behavior.control_unit` is set (A or W), auto-use profile value.
* [x] **Frontend (`SystemTab.tsx`):** Only show `control_unit` selector for `generic` profile (when `control_unit: null`).
* [x] **Verification:** Full suite passing (102 tests).
* [x] **USER VERIFICATION AND COMMIT:** Stop and let the user verify.

#### Phase 2: Fronius Entity Routing & Defaults [DONE]
* [x] **Backend (`actions.py`):** Fix `_set_charge_limit` to use `inverter.grid_charge_power` directly (stop looking in `custom_entities`).
* [x] **Backend (`config.py`):** Verify `grid_charge_power_entity` is correctly aliased during config loading.
* [x] **Profile (`fronius.yaml`):** Add BYD battery entities as defaults/suggestions (extracted from user production config).
* [x] **Validation:** Add unit test for Fronius grid-charge routing to prevent regression with `pv_charge_limit`.
* [x] **Verification:** Confirm fix in shadow mode logs.
* [x] **USER VERIFICATION AND COMMIT:** Stop and let the user verify.

#### Phase 3: Profile & Logic Verification [DONE]

**Verification Summary:** All 4 inverter profiles audited against logic documentation. **74/74 tests passing.**

**✅ Profile Entity Updates (mkaiser v2):**
* [x] **Sungrow (`sungrow.yaml`):** Updated to mkaiser v2 integration entity names:
  * `select.sg_ems_mode` → `select.ems_mode`
  * `input_number.set_sg_battery_max_charge_power` → `number.battery_max_charge_power`
  * `input_number.set_sg_battery_max_discharge_power` → `number.battery_max_discharge_power`
  * `input_number.set_sg_export_power_limit` → `number.export_power_limit`
* [x] **Documentation:** Added mkaiser v2 integration note to profile metadata

**✅ Backend Audit:**
* [x] `actions.py` (lines 636-648, 728-746): Correctly syncs `forced_power` in forced modes
* [x] `actions.py` (lines 637-639, 729-731): Standardized search for `forced_power` + legacy `forced_power_entity`
* [x] `override.py` (lines 144-186): No hardcoded `work_mode` in emergency/low SoC/fallback actions
* [x] `controller.py` (lines 104-107): Falls back to `profile.modes.zero_export` correctly
* [x] `controller.py` (lines 176-178, 255-257): Forces profile `control_unit` (W for Sungrow/Fronius)

**✅ Frontend Audit:**
* [x] `SystemTab.tsx` (lines 56-66): Disables `control_unit` selector for non-generic profiles
* [x] `SystemTab.tsx` (lines 82-89): Auto-syncs `control_unit` from `profile.behavior.control_unit`

**✅ Test Results:**
* `test_executor_actions.py`: 29 tests passing
* `test_executor_override.py`: 16 tests passing
* `test_rev_ip4.py`: 3 tests passing
* `test_executor_profiles.py`: 13 tests passing
* **Total: 74/74 tests passing**

---

### [DONE] REV // F48 — Fronius Skip Logic & UI Saving Fixes

**Goal:** Resolve redundant discharge limit writes for Fronius and fix UI configuration saving bugs.
**Context:** Fronius inverters in "Auto" mode handle their own discharge limits, making external writes redundant. Additionally, the settings UI failed to detect certain changes (like entity IDs) due to loose equality checks in the patch logic.

**Plan:**

#### Phase 1: Executor & Profile Logic [DONE]
* [x] Add `skip_discharge_limit` flag to `WorkMode` dataclass.
* [x] Update `fronius.yaml` to enable `skip_discharge_limit` for Auto modes.
* [x] Implement skip logic in `ActionDispatcher._set_discharge_limit`.
* [x] Verify via `test_executor_fronius_profile.py`.

#### Phase 2: UI Saving Fixes [DONE]
* [x] Refactor `areEqual` in `utils.ts` for strict change detection.
* [x] Add debug logging to `buildPatch` and `useSettingsForm.ts`.
* [x] Verify linting and formatting pass.

---

### [DONE] REV // F49 — Settings UI Polish & Export Limit Switch

**Goal:** Fix missing export limit switch, redundant shadow mode toggle, and improve visibility of advanced inverter logic strings.
**Context:** Beta testers reported missing "Export Power Limit" switch (required for Sungrow). Shadow mode is redundant in settings. Inverter logic strings should be profile-aware.

**Plan:**

#### Phase 1: Backend Logic & Configuration [DONE]
* [x] **[config.py](file:///home/s/sync/documents/projects/darkstar/executor/config.py):** Add `grid_max_export_power_switch` to `InverterConfig`.
* [x] **[actions.py](file:///home/s/sync/documents/projects/darkstar/executor/actions.py):** Update `_set_max_export_power` to control the switch entity.
* [x] **[executor.py](file:///home/s/sync/documents/projects/darkstar/backend/api/routers/executor.py):** Expose new field in API config endpoints.
* [x] **Unit Tests:** Add tests for new switch logic in `test_executor_actions.py`.

#### Phase 2: Frontend & Profiles [DONE]
* [x] **[types.ts](file:///home/s/sync/documents/projects/darkstar/frontend/src/pages/settings/types.ts):** Add Export Switch entity field.
* [x] **[types.ts](file:///home/s/sync/documents/projects/darkstar/frontend/src/pages/settings/types.ts):** Fix visibility of Mode Strings and remove Shadow Mode.
* [x] **[sungrow.yaml](file:///home/s/sync/documents/projects/darkstar/profiles/sungrow.yaml):** Add `grid_max_export_power_switch` to entity mapping.
* [x] **Manual Verification:** Verify UI behavior and log output.

---

### [PLANNED] REV // F50 — EV Charging Configuration Unification & UI Fixes

**Goal:** Fix critical configuration mismatch causing EV features to fail, and add missing UI indicators.
**Context:** Beta tester reported no re-planning when plugging in EV. Investigation revealed TWO separate configuration keys (`system.has_ev_charger` vs `ev_charger.enabled`) causing the backend to ignore EV sensors even when UI shows "EV charger installed" as enabled. Additionally, UI lacks visual feedback for plug status and EV charging visibility in charts.

**Critical Issues Found:**
1. **Backend checks `ev_charger.enabled`** but **UI sets `system.has_ev_charger`** - entities never monitored!
2. **PowerFlow node** only shows when plugged in (no indication when unplugged)
3. **ChartCard** has EV data but **no toggle** to show it (dataset always hidden)

**Plan:**

#### Phase 1: Configuration Unification [DONE]
* [x] **[backend/ha_socket.py](file:///home/s/sync/documents/projects/darkstar/backend/ha_socket.py:110):** Change `ev_cfg.get("enabled", False)` to check `system.has_ev_charger` instead
* [x] **[config.default.yaml](file:///home/s/sync/documents/projects/darkstar/config.default.yaml:66):** Remove `enabled: false` field from `ev_charger:` section (keep only `system.has_ev_charger`)
* [x] **[config.yaml](file:///home/s/sync/documents/projects/darkstar/config.yaml:69):** Remove `enabled: false` field from `ev_charger:` section
* [x] **[executor/config.py](file:///home/s/sync/documents/projects/darkstar/executor/config.py):** Remove `enabled` field from `EVChargerConfig` dataclass (if exists)
* [x] **Documentation:** Update comments in config files to clarify single source of truth
* [x] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

#### Phase 2: PowerFlow Visual Indicator [DONE]
* [x] **[PowerFlowRegistry.ts](file:///home/s/sync/documents/projects/darkstar/frontend/src/components/PowerFlowRegistry.ts:101):** Modify EV node to always render (remove `shouldRender` condition)
* [x] **[PowerFlowRegistry.ts](file:///home/s/sync/documents/projects/darkstar/frontend/src/components/PowerFlowRegistry.ts:105):** Add greyed color state when `!data.evPluggedIn` (use `--color-text-muted` or similar)
* [x] **[PowerFlowRegistry.ts](file:///home/s/sync/documents/projects/darkstar/frontend/src/components/PowerFlowRegistry.ts:109):** Add plug icon indicator when `data.evPluggedIn` is true (use `lucide-react` Plug icon)
* [x] **[PowerFlowCard.tsx](file:///home/s/sync/documents/projects/darkstar/frontend/src/components/PowerFlowCard.tsx):** Update node rendering to support conditional icon and color based on plugged-in state
* [x] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

#### Phase 3: ChartCard EV Toggle [DONE]
* [x] **[ChartCard.tsx](file:///home/s/sync/documents/projects/darkstar/frontend/src/components/ChartCard.tsx:787):** Add `ev: false` to initial overlays state in localStorage migration (increment STORAGE_VERSION to 3)
* [x] **[ChartCard.tsx](file:///home/s/sync/documents/projects/darkstar/frontend/src/components/ChartCard.tsx:1056):** Fix dataset index misalignment (all indices after 7 were off-by-one)
* [x] **[ChartCard.tsx](file:///home/s/sync/documents/projects/darkstar/frontend/src/components/ChartCard.tsx:1155):** Add EV toggle button to the chart overlay menu
* [x] **[ChartCard.tsx](file:///home/s/sync/documents/projects/darkstar/frontend/src/components/ChartCard.tsx:423):** Remove `hidden: true` from EV Charging dataset (now controlled by toggle)
* [x] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

#### Phase 4: Testing & Validation [DONE]
* [x] **Backend:** Verify EV entities are monitored when `system.has_ev_charger: true`
* [x] **Testing:** Run `pytest` and `pnpm lint` to ensure no regressions
* [x] **USER VERIFICATION AND COMMIT:** Final wrap-up and user review


#### Phase 5: UI Polish & EV SoC Display [DONE]
* [x] **[PowerFlowRegistry.ts](file:///home/s/sync/documents/projects/darkstar/frontend/src/components/PowerFlowRegistry.ts:105):** Fix CSS variable: change `--color-text-muted` to `--color-muted` (fixes black node)
* [x] **[PowerFlowRegistry.ts](file:///home/s/sync/documents/projects/darkstar/frontend/src/components/PowerFlowRegistry.ts:18):** Add `evSoc?: number` to PowerFlowData interface
* [x] **[PowerFlowRegistry.ts](file:///home/s/sync/documents/projects/darkstar/frontend/src/components/PowerFlowRegistry.ts:107):** Add `subValueAccessor` to EV node to show SoC percentage when plugged in
* [x] **[Dashboard.tsx](file:///home/s/sync/documents/projects/darkstar/frontend/src/pages/Dashboard.tsx:91):** Add `ev_soc?: number` to livePower state type
* [x] **[Dashboard.tsx](file:///home/s/sync/documents/projects/darkstar/frontend/src/pages/Dashboard.tsx:115):** Capture `ev_soc` in live_metrics WebSocket handler
* [x] **[Dashboard.tsx](file:///home/s/sync/documents/projects/darkstar/frontend/src/pages/Dashboard.tsx:778):** Pass `evSoc: livePower.ev_soc` to PowerFlowCard data
* [x] **[ha_socket.py](file:///home/s/sync/documents/projects/darkstar/backend/ha_socket.py:275):** Emit `ev_soc` value in live_metrics alongside `ev_plugged_in`
* [x] **Testing:** Verify node shows grey when unplugged, peak color + SoC when plugged in
* [x] **USER VERIFICATION AND COMMIT:** Final verification and commit

#### Phase 6: Color Unification & Penalty Editor [DONE]
* [x] **[ChartCard.tsx](file:///home/s/sync/documents/projects/darkstar/frontend/src/components/ChartCard.tsx:414-429):** Change EV overlay color from `DS.peak` (pink) to `DS.ai` (violet #8B5CF6)
* [x] **[ChartCard.tsx](file:///home/s/sync/documents/projects/darkstar/frontend/src/components/ChartCard.tsx:1158-1171):** Update EV toggle button styling to use `bg-ai/20 border-ai` instead of `bg-peak/20 border-peak`
* [x] **[PowerFlowRegistry.ts](file:///home/s/sync/documents/projects/darkstar/frontend/src/components/PowerFlowRegistry.ts:104-105):** Change EV node peak color to violet when plugged in (match ChartCard)
* [x] **[index.css](file:///home/s/sync/documents/projects/darkstar/frontend/src/index.css):** Ensure `--color-ai` is properly defined (violet #8B5CF6)
* [x] **[pipeline.py](file:///home/s/sync/documents/projects/darkstar/planner/pipeline.py:398):** Remove redundant `and ev_cfg.get("enabled", False)` - use only `has_ev_charger`
* [x] **[adapter.py](file:///home/s/sync/documents/projects/darkstar/planner/solver/adapter.py:196):** Remove redundant `and ev_cfg.get("enabled", False)` - use only `system.has_ev_charger`
* [x] **[config.default.yaml](file:///home/s/sync/documents/projects/darkstar/config.default.yaml:69-104):** Verify no `enabled` field exists under `ev_charger:` section
* [x] **[types.ts](file:///home/s/sync/documents/projects/darkstar/frontend/src/pages/settings/types.ts:1268-1319):** Replace 4 flat penalty fields with single `penalty_levels` field using new type
* [x] **[types.ts](file:///home/s/sync/documents/projects/darkstar/frontend/src/pages/settings/types.ts):** Add `'penalty_levels'` to FieldType union
* [x] **[PenaltyLevelsEditor.tsx](file:///home/s/sync/documents/projects/darkstar/frontend/src/pages/settings/components/PenaltyLevelsEditor.tsx):** Create new component for editing array-based penalty levels (emergency/high/normal/opportunistic)
* [x] **[SettingsField.tsx](file:///home/s/sync/documents/projects/darkstar/frontend/src/pages/settings/components/SettingsField.tsx):** Add case for `'penalty_levels'` type rendering PenaltyLevelsEditor
* [x] **[utils.ts](file:///home/s/sync/documents/projects/darkstar/frontend/src/pages/settings/utils.ts):** Handle `'penalty_levels'` type in `parseFieldInput` and `buildFormState`
* [x] **[inputs.py](file:///home/s/sync/documents/projects/darkstar/inputs.py:708-722):** Add EV state fetching to `get_initial_state()` - fetch `ev_soc_percent` from `input_sensors.ev_soc` and `ev_plugged_in` from `input_sensors.ev_plug`
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

---

### [DONE] REV // F51 — EV Economic Planner (Modulation & Value Buckets)

**Goal:** Implement continuous (modulating) EV power control and an economic "Value Bucket" model to replace hardcoded penalties and binary on/off logic.
**Context:** Current binary logic causes grid limit deadlocks. Hardcoded 5000 SEK penalties ignore user "willingness to pay". Redundant configuration fields cause confusion.

**Plan:**

#### Phase 1: Configuration Cleanup & Schema [DONE]
* [x] **[config.yaml](file:///home/s/sync/documents/projects/darkstar/config.yaml):** Remove redundant `soc_sensor`, `plug_sensor`, and `switch_entity` from top-level `ev_charger`.
* [x] **[config.yaml](file:///home/s/sync/documents/projects/darkstar/config.yaml):** Remove legacy `min_target_soc` and `min_soc` fields.
* [x] **[KeplerConfig](file:///home/s/sync/documents/projects/darkstar/planner/solver/types.py):** Remove `ev_target_soc_percent` (to be replaced by bucket limits).
* [x] **[KeplerConfig](file:///home/s/sync/documents/projects/darkstar/planner/solver/types.py):** Add support for multiple SOC-threshold "Incentive Buckets" (Value in SEK/kWh).
* [x] **USER VERIFICATION:** Confirm schema matches the "Willingness to Pay" economic model.

#### Phase 2: Solver Logic (Kepler) [DONE]
* [x] **Continuous Power:** Change `ev_energy` constraint from `==` to `<=` (binary-guarded) in `kepler.py`. This allows the solver to "throttle" charging to fit under grid limits.
* [x] **Value Bucket Model:** Implement multi-stage objective function terms where each SoC range earns a specific "Urgency Incentive" (SEK/kWh).
* [x] **Sign Flip:** Core logic fix to ensure incentives are subtracted from cost (making charging a "profit" for the solver).
* [x] **Remove Hardcoded Penalty:** Delete the 5000 SEK `ev_target_violation` logic; urgency is now entirely economic.
* [x] **Verification:** Run `repro_ev_block.py` variant to confirm modulation solves the grid deadlock.

#### Phase 3: Frontend & UI [DONE]
* [x] **[PenaltyLevelsEditor.tsx](file:///home/s/sync/documents/projects/darkstar/frontend/src/pages/settings/components/PenaltyLevelsEditor.tsx):** Update to a "Threshold-based" (chained) UI.
* [x] **UI Logic:** Level 1 ends at X%, Level 2 starts at X% and ends at Y%, etc. (chained percentages). 0% -> T1 -> T2 -> T3 -> 100%.
* [x] **Labeling:** Clearly label penalty inputs as "Maximum Price (SEK/kWh)" or "Willingness to Pay".
* [x] **Settings Schema:** Simplify to shared percentage boundaries.

#### Phase 4: Integration & Hardening [DONE]
* [x] **[planner/pipeline.py](file:///home/s/sync/documents/projects/darkstar/planner/pipeline.py):** Map new UI bucket thresholds to `KeplerConfig`.
* [x] **[inputs.py](file:///home/s/sync/documents/projects/darkstar/inputs.py):** Add logging warnings if `has_ev_charger` is ON but `input_sensors` are missing.
* [x] **Final Verification:** Verify that setting a low price limit (e.g., 0.5 SEK) correctly skips expensive slots even if SoC is below "target".
* [x] **USER VERIFICATION AND COMMIT:** Final wrap-up and user review.

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
