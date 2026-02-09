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
