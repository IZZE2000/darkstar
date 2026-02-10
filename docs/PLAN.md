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

### [IN PROGRESS] REV // F53 — Fronius Auto Mode Entity Write Fixes

**Goal:** Prevent extraneous entity writes in Fronius "Auto" work mode. Only `minimum_reserve` (SoC target) should be written in Auto mode.
**Context:** Beta tester reports Fronius in "Auto" mode is receiving writes for `grid_charging`, `max_export_power`, and `discharge_limit` entities. Per `fronius_logic.md`, Auto mode ignores all controls except `minimum_reserve`.

**Plan:**

#### Phase 1: Fix Auto Mode Skip Logic [DONE]
* [x] Update `execute()` in `[executor/actions.py]` to check profile `skip_*` flags BEFORE calling `_set_grid_charging()`, `_set_discharge_limit()`, `_set_max_export_power()`
* [x] Fix generic optimization logic (lines 349-400) that only checks Charge/Idle modes, ignoring profile flags
* [x] Verify `self_consumption` and `zero_export` modes (both "Auto") properly skip all 3 entities
* [x] Test that only `soc_target` and `work_mode` are written in Auto mode

#### Phase 2: Fix Idle Status Display [DONE]
* [x] Update `_generate_reason()` in `[executor/controller.py]` to use profile mode descriptions instead of hardcoded "Hold/Idle" and "Zero-Export" labels
* [x] Use `profile.modes.*.description` for the reason string when available
* [x] Ensure "Auto" mode shows correct description, not "Idle"

#### Phase 3: Fix Config Reload on UI Save [DONE]
* [x] Add `executor.reload_config()` call in `[backend/api/routers/config.py]` after successful config save
* [x] Import `get_executor_instance` from executor router
* [x] Call reload_config() only if executor is running
* [x] Verify executor immediately picks up new settings without restart
* [x] Test with changing SoC target - should reflect immediately in executor status

---

### [IN PROGRESS] REV // F54 — Sungrow Executor Display & Composite Mode Fixes

**Goal:** Fix three critical issues reported by Sungrow beta tester: Forced cmd not updating when work_mode unchanged, incorrect entity display in execution history, and unwanted SoC Target visibility.

**Context:** Sungrow profile uses composite mode entities (forced_charge_discharge_cmd, export_power_limit, max_discharge_power) that are set alongside work_mode changes. User reports that forced commands aren't updating and execution history shows confusing/misleading information.

**Issues Identified:**

1. **Forced cmd not written independently:** In `_set_work_mode()` (actions.py:462), composite mode entities are ONLY processed when work_mode changes. If Sungrow is already in "Forced mode" but needs to switch from "Forced discharge" to "Forced charge", the forced_charge_discharge_cmd is never updated because the composite loop is skipped when work_mode is already at target.

2. **Grid Charging shown incorrectly:** `_set_grid_charging()` returns ActionResult with "Handled by work_mode" message for Sungrow even though it's mode-based and shouldn't be displayed at all.

3. **SoC Target shown for unsupported profile:** `_set_soc_target()` returns ActionResult even when `supports_soc_target: false`, causing it to appear in execution history.

4. **Discharge Limit shown when skipped:** Even with `skip_discharge_limit: true`, an ActionResult is returned with "Skipped per mode setting" message.

5. **Max Export Power shown incorrectly:** Similar to discharge limit, this shows up even when it shouldn't for Sungrow modes.

**Plan:**

#### Phase 1: Fix Composite Mode Independent Updates [DONE]
* [x] Refactor `_set_work_mode()` in `[executor/actions.py]` to process composite mode entities even when work_mode is already at target
* [x] Extract composite entity processing into separate helper method `_apply_composite_entities()`
* [x] Call `_apply_composite_entities()` after the idempotency check for work_mode
* [x] Ensure forced_charge_discharge_cmd updates when charging intent changes (charge vs discharge) even if EMS mode stays "Forced mode"
* [x] All 28 executor action tests pass

#### Phase 2: Fix Grid Charging Silent Skip [DRAFT]
* [ ] Modify `_set_grid_charging()` in `[executor/actions.py]` to return `None` when `separate_grid_charging_switch: false`
* [ ] Update `execute()` method to handle `None` return values (filter out before appending to results)
* [ ] Verify Sungrow self-consumption mode shows NO grid charging entry in history
* [ ] Verify Generic profile with separate switch still shows grid charging correctly

#### Phase 3: Fix SoC Target Silent Skip [DRAFT]
* [ ] Modify `_set_soc_target()` to return `None` when profile has `supports_soc_target: false`
* [ ] Ensure no ActionResult is created for unsupported profiles
* [ ] Verify Sungrow profile never shows SoC Target in execution history
* [ ] Verify Fronius/Deye profiles still show SoC Target when it changes

#### Phase 4: Fix Discharge Limit Silent Skip [DRAFT]
* [ ] Modify `_set_discharge_limit()` to return `None` when `skip_discharge_limit: true` for current mode
* [ ] Remove the "Skipped per mode setting" ActionResult for truly skipped actions
* [ ] Verify Sungrow modes with skip_discharge_limit don't show discharge_limit entries

#### Phase 5: Fix Max Export Power Silent Skip [DRAFT]
* [ ] Add profile-aware skip logic to `_set_max_export_power()` similar to discharge_limit
* [ ] Return `None` for modes that shouldn't show export power changes
* [ ] Verify export modes show export power, non-export modes don't

#### Phase 6: Execute Method Null Handling [DRAFT]
* [ ] Update `execute()` method to filter out `None` results from all action methods
* [ ] Add type hints: `-> ActionResult | None`
* [ ] Ensure no regression in action_results processing in engine.py

#### Phase 7: Testing & Verification [DRAFT]
* [ ] Test Sungrow profile: Forced mode changes (discharge->charge) with same work_mode
* [ ] Test Sungrow profile: Self-consumption mode shows only work_mode + composite entities
* [ ] Test Fronius profile: Verify no regression in Auto mode behavior
* [ ] Test Generic profile: Verify all entities still display correctly
* [ ] Run frontend lint (`pnpm lint`)
* [ ] Run backend pytest (`uv run pytest`)
* [ ] Update relevant tests in `test_executor_actions.py`
