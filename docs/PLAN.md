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

### [DONE] REV // ARC13 — Multi-Inverter Profile System

**Goal:** Enable Darkstar to support multiple inverter brands (Fronius, Victron, Solinteg, etc.) through a flexible profile system without requiring core code changes.

**Context:** Darkstar currently hardcodes Deye/SunSynk inverter behavior. Beta users with Fronius and other brands need brand-specific entity mappings, work mode translations, and control patterns. A comprehensive vision document exists at `docs/INVERTER_PROFILES_VISION.md`. Additional research from Predbat shows Solinteg inverters use service call patterns for mode control (see: https://github.com/springfall2008/batpred/discussions/2529).

**Plan:**

#### Phase 1: Profile Infrastructure [DONE]
* [x] Create profile YAML schema (`profiles/schema.yaml`)
* [x] Implement profile loader (`executor/profiles.py`) with validation
* [x] Add `InverterProfile` dataclass with type hints (capabilities, entities, modes, behavior, defaults)
* [x] Load profile based on config setting with fallback to "generic"
* [x] Add profile validation tests (17 tests passing)
* [x] Enhanced modes section to cover ALL inverter actions: export, zero_export, self_consumption, grid_charge, force_discharge, idle
* [x] **COMPLETED 2026-02-05**

#### Phase 2: Deye Profile Migration [DONE]
* [x] Create `profiles/deye.yaml` matching current hardcoded behavior
* [x] Refactor executor to use profile for entity lookups
* [x] Refactor executor to use profile for mode translations
* [x] Ensure 100% backward compatibility (existing Deye users unaffected)
* [x] Add integration tests comparing old vs new behavior (5 tests passing)
* [x] **COMPLETED 2026-02-05**

#### Phase 3: Config Seeding & Profile Setup Helper [DONE]
* [x] Add `defaults` section to profile YAML schema (suggested config values)
* [x] Implement startup warnings when entities are missing (log profile suggestions)
* [x] Create Settings UI "Profile Setup Helper" component
* [x] Add API endpoint `GET /api/profiles/{name}/suggestions` (returns suggested config keys)
* [x] Add "Apply Suggested Values" button in Settings UI (writes to config.yaml)
* [x] Show diff preview before applying suggestions
* [x] **COMPLETED 2026-02-05**

#### Phase 4: Fronius Profile Implementation [DONE]
* [x] Create `profiles/fronius.yaml` based on community feedback
* [x] Implement Watts-based control (vs Amperes for Deye)
* [x] Handle single battery mode select (no separate grid charging switch)
* [x] Add Fronius-specific mode translations ("Auto", "Discharge to grid", etc.)
* [x] Add config seeding defaults for Fronius entities
* [x] Beta test with Fronius users (Simon, Kristoffer)
* [x] **COMPLETED 2026-02-05**

#### Phase 5: Generic Profile & Documentation [DONE]
* [x] Create `profiles/generic.yaml` for unknown inverters
* [x] Provide sensible defaults and manual entity configuration
* [x] Write `docs/CREATING_INVERTER_PROFILES.md` (community contribution guide)
* [x] Update `profiles/schema.yaml` to serve as profile template
* [x] Document Solinteg service call pattern (future enhancement discussion)
* [x] Add profile validation to CI/CD (pre-commit)
* [x] Update `docs/SETUP_GUIDE.md` with profile selection instructions
* [x] **COMPLETED 2026-02-05**

---

### [IN PROGRESS] REV // IP1 — Fronius Profile Corrections

**Goal:** Fix critical issues in the Fronius inverter profile based on official modbus documentation and beta user feedback.

**Context:** After ARC13 completion, beta tester Kristoffer reported incorrect mode mappings. Analysis of the [Fronius modbus documentation](https://github.com/callifo/fronius_modbus) revealed:
1. "Auto" mode is self-consumption with export (NOT zero export)
2. Fronius requires mode to be set BEFORE controls (order dependency)
3. Missing critical entities: Minimum Reserve and Grid Charge Power
4. Grid charging must be rounded to 10W increments

**Plan:**

#### Phase 1: Mode Mapping Corrections [DONE]
* [x] Set `zero_export: null` (may not exist on Fronius, needs beta testing)
* [x] Update mode descriptions to match Fronius documentation
* [x] Add comments explaining each mode's behavior
* [x] **COMPLETED 2026-02-05**

#### Phase 2: Missing Entity Additions [DONE]
* [x] Add `minimum_reserve` to required entities in Fronius profile
* [x] Add `grid_charge_power` to required entities in Fronius profile
* [x] Update `profiles/schema.yaml` to document these entities
* [x] Add suggested entity mappings to `defaults.suggested_entities`
* [x] Update executor config to handle new entities (ProfileEntities handles dynamic required fields)
* [x] **COMPLETED 2026-02-05**

#### Phase 3: Entity Setting Order Fix [DONE]
* [x] Add profile behavior flag: `requires_mode_settling: true`
* [x] Add profile behavior parameter: `mode_settling_ms: 500`
* [x] Update `executor/actions.py` to check `profile.behavior.requires_mode_settling`
* [x] Add 500ms delay after mode changes when flag is true
* [x] Ensure delay only applies to Fronius (profile-specific)
* [x] **COMPLETED 2026-02-05**

#### Phase 4: Grid Charging Behavior [DONE]
* [x] Add `grid_charge_round_step_w: 10.0` to Fronius behavior section
* [x] Update executor controller to round grid charge commands to 10W
* [x] Document 50% efficiency limitation in profile comments
* [x] Add validation to prevent odd charging behavior
* [x] **COMPLETED 2026-02-05**

#### Phase 5: Multi-Arch Build Support [DONE]
* [x] Modify GitHub Actions to enable `aarch64` builds on dev/main
* [x] Remove `if` conditions restricting non-amd64 builds
* [x] **COMMIT:** feat(ci): enable multi-arch builds for dev
* [x] **COMPLETED 2026-02-05**

#### Phase 6: Config Validation & UX Fixes [DONE]
* [x] **Backend:** Implement profile-aware config validation (removing hardcoded errors)
* [x] **Frontend:** Update `types.ts` to loosen `required` fields
* [x] **Frontend:** Hide "Grid Charging Switch" for Fronius profile
* [x] **Frontend:** Add missing Fronius entities (`minimum_reserve`, `grid_charge_power`)
#### Phase 6: Config Validation & UX Fixes [DONE]
* [x] **Backend:** Implement profile-aware config validation (removing hardcoded errors)
* [x] **Frontend:** Update `types.ts` to loosen `required` fields
* [x] **Frontend:** Hide "Grid Charging Switch" for Fronius profile
* [x] **Frontend:** Add missing Fronius entities (`minimum_reserve`, `grid_charge_power`)
* [x] **COMMIT:** fix(config): profile-aware validation and ui updates
* [x] **Phase 6.1 (UI):** Add `soc_target_entity` to settings (Required for Deye/Generic)
* [x] **Phase 6.2 (Logic):** Make `soc_target` silent-skip for profiles that don't require it (Fronius)
* [x] **COMMIT:** fix(executor): conditional soc_target ui and silent skip
* [x] **Phase 6.3 (Cleanup):** Remove duplicate SoC target fields in `types.ts`
* [x] **COMMIT:** refactor(ui): remove duplicate soc_target settings field


---

### [DONE] REV // IP2 — Sungrow Profile & Multi-Entity Support

**Goal:** Implement full support for Sungrow inverters which require setting multiple entities for a single mode change (Composite Modes).

**Context:** Sungrow integration (via Modbus HA) requires setting both an EMS mode and a specific charge/discharge command to achieve standard behaviors. The current profile system only supports 1-to-1 mode mapping.

**Plan:**

#### Phase 1: Executor Core Updates [DONE]
* [x] Update `InverterConfig` to accept dynamic `custom_entities` (for arbitrary profile keys)
* [x] Update `WorkMode` in profiles to support `set_entities` (map of entity_key -> value)
* [x] Refactor `ActionDispatcher` to handle multi-entity updates for a single mode
* [x] Verify backward compatibility with existing profiles (Deye, Fronius)
* [x] **COMPLETED 2026-02-05**

#### Phase 2: Sungrow Profile [DONE]
* [x] Create `profiles/sungrow.yaml`
* [x] Map "Export", "Zero Export", "Grid Charge" to Sungrow specific entity combinations
* [x] Set defaults (20ms delay, Watts control) based on beta feedback
* [x] Validate profile using `validate_profiles.py`
* [x] **COMPLETED 2026-02-05**

#### Phase 3: Sungrow Forced Power Support [DONE]
* [x] Add `forced_power_entity` to `ProfileEntities` (optional)
* [x] Update `executor/actions.py` to write to `forced_power_entity` when in forced modes (Grid Charge, Force Discharge)
* [x] Update `profiles/sungrow.yaml` to map `input_number.set_sg_forced_charge_discharge_power`
* [x] Verify "Double-Writing" logic (Standard Limit + Forced Limit)
* [x] **COMPLETED 2026-02-06**

---

### [DONE] REV // UI16 — Mobile UX Polish

**Goal:** Improve mobile view by removing the intrusive menu banner and replacing it with a floating hamburger button.

**Plan:**

#### Phase 1: Sidebar Redesign [DONE]
* [x] Remove full-width mobile top bar in `Sidebar.tsx`
* [x] Implement fixed floating hamburger button (top-4 left-4)
* [x] Verify click behavior and z-index transparency
* [x] **COMPLETED 2026-02-05**

#### Phase 2: Card Contrast & Shadows [DONE]
* [x] **UI16-2: Card Contrast & Shadows**
    - Added `surface-elevated` for nested cards.
    - Deepened section shadows with `shadow-section` (60px radius).
    - Removed shadows from elevated cards to fix clipping issues.
    - Fixed `overflow` and padding across all settings tabs.
* [x] Fix `bg-surface1` inconsistency in `SolarArraysEditor.tsx`
* [x] **COMPLETED 2026-02-05**

* [x] **COMMIT (AMEND):** feat(ui): mobile hamburger and settings contrast polish

---

### [DONE] REV // F45 — Fix soc_target_entity Regression

**Goal:** Resolve the "executor.inverter.soc_target_entity is not configured" error and standardize the entity's location.

**Context:** The new profile system expects inverter-specific entities in `executor.inverter`, but `soc_target_entity` was left in the root `executor` config. This caused validation errors and confusion.

**Plan:**

#### Phase 1: Standardization & Migration [DONE]
* [x] **Config:** Move `soc_target_entity` to `executor.inverter.soc_target_entity` in `config.default.yaml`.
* [x] **Backend:** Update `executor/config.py` to read from new location with fallback to old location.
* [x] **Backend:** Update `executor/actions.py` to use `config.inverter.soc_target_entity`.
* [x] **Migration:** Implement explicit `migrate_soc_target_entity` in `backend/config_migration.py`.
* [x] **Frontend:** Update `types.ts`, `Executor.tsx`, and `config-help.json` to reflect new path.
* [x] **Validation:** Fix `profiles/schema.yaml` naming (`soc_target` -> `soc_target_entity`).
* [x] **COMMIT:** fix(config): standardize soc_target_entity location and add migration

---

### [DONE] REV // F46 — Fix Missing Profiles Directory in Docker Images

**Goal:** Fix the critical bug where inverter profile YAML files are not included in Docker containers, causing "Profile file not found" errors.

**Context:** Both `darkstar/Dockerfile` and `darkstar-dev/Dockerfile` are missing the `COPY profiles/ ./profiles/` instruction. When the add-on runs in Home Assistant, the executor cannot load inverter profiles (deye, fronius, generic, sungrow) because the `profiles/` directory was never copied into the container. The code looks for `profiles/deye.yaml` relative to `/app` working directory, but the directory doesn't exist.

**Root Cause:** The `profiles/` directory exists in the repo root with all inverter YAML files, but neither Dockerfile includes it in the COPY instructions.

**Plan:**

#### Phase 1: Fix Dockerfiles [DONE]
* [x] Add `COPY profiles/ ./profiles/` to `darkstar/Dockerfile` after line 38 (where other app directories are copied)
* [x] Add `COPY profiles/ ./profiles/` to `darkstar-dev/Dockerfile` after line 38
* [x] Verify both Dockerfiles have consistent COPY ordering
* [x] **COMMIT:** fix(docker): add missing profiles directory to both Dockerfiles

#### Phase 2: Verification [PLANNED]
* [ ] Build test image locally to confirm profiles are included
* [ ] Verify profile loading works in container context
* [ ] Test with different inverter profiles (deye, fronius)
