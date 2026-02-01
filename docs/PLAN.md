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

### [PLANNED] REV // ARC13 — Multi-Inverter Profile System

**Goal:** Enable Darkstar to support multiple inverter brands (Fronius, Victron, Solinteg, etc.) through a flexible profile system without requiring core code changes.

**Context:** Darkstar currently hardcodes Deye/SunSynk inverter behavior. Beta users with Fronius and other brands need brand-specific entity mappings, work mode translations, and control patterns. A comprehensive vision document exists at `docs/INVERTER_PROFILES_VISION.md`. Additional research from Predbat shows Solinteg inverters use service call patterns for mode control (see: https://github.com/springfall2008/batpred/discussions/2529).

**Plan:**

#### Phase 1: Profile Infrastructure [PLANNED]
* [ ] Create profile YAML schema (`profiles/schema.yaml`)
* [ ] Implement profile loader (`executor/profiles.py`) with validation
* [ ] Add `InverterProfile` dataclass with type hints (capabilities, entities, modes, behavior, defaults)
* [ ] Add `system.inverter_profile` config key to `config.default.yaml`
* [ ] Load profile based on config setting with fallback to "generic"
* [ ] Add profile validation tests
* [ ] **USER VERIFICATION AND COMMIT**

#### Phase 2: Deye Profile Migration [PLANNED]
* [ ] Create `profiles/deye.yaml` matching current hardcoded behavior
* [ ] Refactor executor to use profile for entity lookups
* [ ] Refactor executor to use profile for mode translations
* [ ] Ensure 100% backward compatibility (existing Deye users unaffected)
* [ ] Add integration tests comparing old vs new behavior
* [ ] **USER VERIFICATION AND COMMIT**

#### Phase 3: Config Seeding & Profile Setup Helper [PLANNED]
* [ ] Add `defaults` section to profile YAML schema (suggested config values)
* [ ] Implement startup warnings when entities are missing (log profile suggestions)
* [ ] Create Settings UI "Profile Setup Helper" component
* [ ] Add API endpoint `GET /api/profiles/{name}/suggestions` (returns suggested config keys)
* [ ] Add "Apply Suggested Values" button in Settings UI (writes to config.yaml)
* [ ] Show diff preview before applying suggestions
* [ ] **USER VERIFICATION AND COMMIT**

#### Phase 4: Fronius Profile Implementation [PLANNED]
* [ ] Create `profiles/fronius.yaml` based on community feedback
* [ ] Implement Watts-based control (vs Amperes for Deye)
* [ ] Handle single battery mode select (no separate grid charging switch)
* [ ] Add Fronius-specific mode translations ("Auto", "Discharge to grid", etc.)
* [ ] Add config seeding defaults for Fronius entities
* [ ] Beta test with Fronius users (Simon, Kristoffer)
* [ ] **USER VERIFICATION AND COMMIT**

#### Phase 5: Generic Profile & Documentation [PLANNED]
* [ ] Create `profiles/generic.yaml` for unknown inverters
* [ ] Provide sensible defaults and manual entity configuration
* [ ] Write `docs/CREATING_INVERTER_PROFILES.md` (community contribution guide)
* [ ] Add profile template (`profiles/template.yaml`)
* [ ] Document Solinteg service call pattern as example for future profiles
* [ ] Add profile validation to CI/CD
* [ ] Update `docs/SETUP_GUIDE.md` with profile selection instructions
* [ ] **USER VERIFICATION AND COMMIT**

#### Phase 6: Community Expansion [PLANNED]
* [ ] Accept community-contributed profiles (Victron, Goodwe, Solinteg, etc.)
* [ ] Add profile marketplace documentation
* [ ] Implement profile versioning and update notifications
* [ ] Add profile auto-detection from HA entities (optional enhancement)
* [ ] **USER VERIFICATION AND COMMIT**

---

---
