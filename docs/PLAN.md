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

### [PLANNED] REV // IP1 — Fronius Profile Corrections

**Goal:** Fix critical issues in the Fronius inverter profile based on official modbus documentation and beta user feedback.

**Context:** After ARC13 completion, beta tester Kristoffer reported incorrect mode mappings. Analysis of the [Fronius modbus documentation](https://github.com/callifo/fronius_modbus) revealed:
1. "Auto" mode is self-consumption with export (NOT zero export)
2. Fronius requires mode to be set BEFORE controls (order dependency)
3. Missing critical entities: Minimum Reserve and Grid Charge Power
4. Grid charging must be rounded to 10W increments

**Plan:**

#### Phase 1: Mode Mapping Corrections [PLANNED]
* [ ] Update `profiles/fronius.yaml` mode mappings:
  * [ ] `self_consumption: "Auto"` (was incorrectly mapped to zero_export)
  * [ ] `export: "Discharge to grid"` (update from current)
  * [ ] `hold: "Block discharging"` (add new)
  * [ ] `charge_from_grid: "Charge from grid"` (keep)
  * [ ] `idle: "Maximum Storage"` (update)
  * [ ] `zero_export: null` (may not exist on Fronius, needs beta testing)
* [ ] Update mode descriptions to match Fronius documentation
* [ ] Add comments explaining each mode's behavior
* [ ] **COMMIT:** Mode mapping corrections

#### Phase 2: Missing Entity Additions [PLANNED]
* [ ] Add `minimum_reserve` to required entities in Fronius profile
* [ ] Add `grid_charge_power` to required entities in Fronius profile
* [ ] Update `profiles/schema.yaml` to document these entities
* [ ] Add suggested entity mappings to `defaults.suggested_entities`
* [ ] Update executor config to handle new entities
* [ ] **COMMIT:** Entity additions

#### Phase 3: Entity Setting Order Fix [PLANNED]
* [ ] Add profile behavior flag: `requires_mode_settling: true`
* [ ] Add profile behavior parameter: `mode_settling_ms: 500`
* [ ] Update `executor/actions.py` to check `profile.behavior.requires_mode_settling`
* [ ] Add 500ms delay after mode changes when flag is true
* [ ] Ensure delay only applies to Fronius (profile-specific)
* [ ] **COMMIT:** Mode settling implementation

#### Phase 4: Grid Charging Behavior [PLANNED]
* [ ] Add `grid_charge_round_step_w: 10.0` to Fronius behavior section
* [ ] Update executor controller to round grid charge commands to 10W
* [ ] Document 50% efficiency limitation in profile comments
* [ ] Add validation to prevent odd charging behavior
* [ ] **COMMIT:** Grid charging rounding

#### Phase 5: Testing & Documentation [PLANNED]
* [ ] Test with Fronius beta users (Kristoffer, Simon)
* [ ] Verify mode changes work correctly with new mappings
* [ ] Verify entity order works (mode → controls)
* [ ] Verify grid charging rounds to 10W increments
* [ ] Update `docs/SETUP_GUIDE.md` with Fronius-specific notes
* [ ] Document known limitations (zero_export may not exist)
* [ ] **COMMIT:** Testing results and documentation

---
