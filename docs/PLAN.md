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

### [PLANNED] REV // F58 — Sungrow Config Healing (Post-F57 Fixes)

**Goal:** Fix critical Sungrow configuration bugs that survived F57: HA add-on migration failures, missing `custom_entities` section, UI save failures, and misleading error messages.

**Context:** Investigation revealed F57 migration works correctly in backend, but HA add-on (`darkstar/run.sh`) uses naive key-adding logic that resurrects deprecated keys. Sungrow composite entities (`ems_mode`, `forced_charge_discharge_cmd`) belong in `executor.inverter.custom_entities` but config template doesn't create this section. Additionally, UI change detection has a critical bug treating `undefined` as equal to empty string, preventing users from saving new entity fields.

**Plan:**

#### Phase 1: Fix HA Add-on Migration [PLANNED]
* [ ] Replace `deep_merge_missing()` in `darkstar/run.sh` with proper migration call
* [ ] Import `backend.config_migration:migrate_config()` in run.sh Python block
* [ ] Call `asyncio.run(migrate_config('/config/darkstar/config.yaml', '/app/config.default.yaml'))`
* [ ] Remove `deep_merge_missing()` function entirely (lines 123-140)
* [ ] Test: Create corrupted config with `version`, `deferrable_loads`, old `_entity` keys
* [ ] Verify: After HA add-on start, all deprecated keys deleted, `config_version` set correctly

#### Phase 2: Add `custom_entities` to Template [PLANNED]
* [ ] Add empty `custom_entities: {}` section to `config.default.yaml` under `executor.inverter`
* [ ] Add comment: `# Profile-specific composite entities (e.g., Sungrow ems_mode)`
* [ ] Template merge will automatically add this section to existing configs
* [ ] Test: Load config without `custom_entities`, verify template merge creates empty section

#### Phase 3: Fix Error Messages [PLANNED]
* [ ] Update `executor/profiles.py:get_missing_entities()` to distinguish standard vs custom paths
* [ ] Create `STANDARD_ENTITY_KEYS` constant matching frontend's `standardInverterKeys`
* [ ] Update error message logic (line 272):
  - Standard keys: `"executor.inverter.{key}"`
  - Custom keys: `"executor.inverter.custom_entities.{key}"`
* [ ] Update suggestion messages accordingly
* [ ] Test: Trigger missing entity validation for both standard and custom entities, verify paths are correct

#### Phase 4: Fix UI Change Detection Bug [PLANNED]
* [ ] Update `frontend/src/pages/settings/utils.ts:areEqual()` to treat `undefined → value` as a change
* [ ] Add check: `if (a === undefined && b !== undefined && b !== '') return false`
* [ ] This fixes the critical bug where adding new entity fields shows "No changes detected"
* [ ] Test: Add new entity via UI, verify save succeeds and config is updated

#### Phase 5: Integration Testing [PLANNED]
* [ ] **Test 1 - HA Add-on Migration:**
  - Create test config with: `version: 2.4.21-beta`, `deferrable_loads: []`, `executor.inverter.work_mode_entity`
  - Start HA add-on via `./darkstar/run.sh` (bash script)
  - Verify: All deprecated keys removed, `config_version: 2`, structure matches template
* [ ] **Test 2 - Sungrow Setup:**
  - Fresh config with `system.inverter_profile: sungrow`
  - No `custom_entities` section
  - Start app, verify template merge creates `executor.inverter.custom_entities: {}`
  - Add entities via UI, verify save succeeds and values appear in config
* [ ] **Test 3 - Error Messages:**
  - Remove `executor.inverter.work_mode` (standard)
  - Remove `executor.inverter.custom_entities.ems_mode` (custom)
  - Check validation errors show correct paths
* [ ] **Test 4 - UI Change Detection:**
  - Fresh config with Sungrow profile, no `ems_mode` in `custom_entities`
  - Open Settings > System, add `select.ems_mode` to EMS Mode entity field
  - Click Save, verify "No changes detected" does NOT appear
  - Verify config file contains the new entity
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

---
