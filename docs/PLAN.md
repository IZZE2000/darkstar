# Darkstar Energy Manager: Active Plan

**Vision: From Calculator to Agent**
Darkstar is transitioning from a deterministic optimizer (v1) to an intelligent energy agent (v2). It does not just optimize based on static config; it observes context (Weather, Vacation, Prices), predicts outcomes (Aurora ML), and actively strategizes (Strategy Engine) to maximize efficiency and comfort.

---

## Revision Naming Conventions

| Prefix | Area | Examples |
|--------|------|----------|
| **K** | Kepler (MILP solver) | F41 |
| **E** | Executor | E1 |
| **A** | Aurora (ML) | A29 |
| **H** | History/DB | H1 |
| **O** | Onboarding | O1 |
| **UI** | User Interface | UI2 |
| **DS** | Design System | DS1 |
| **F** | Fixes/Bugfixes | F6 |
| **DX** | Developer Experience | DX1 |
| **ARC** | Architecture | ARC1 |

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

### [PLANNED] REV // UI14 — UX Polish & Config Documentation

**Goal:** Improve dashboard responsiveness, fix timer state issues, fix chart zoom behavior, and document the learning engine configuration.

**Context:**
- Planning button lacks granular feedback during long solves.
- Water boost timer is brittle and disappears on re-render/sync.
- Chart zoom is buggy (resets on update) and lacks a manual reset mechanism.
- `learning` section in `config.default.yaml` lacks descriptive comments.

**Plan:**

#### Phase 1: Planning Button & Water Boost Timer [PLANNED]
* [ ] **Planning Progress:** Implement a multi-stage status indicator for the planning button in `QuickActions.tsx`.
* [ ] **Boost Timer Fix:** Refactor `ControlParameters.tsx` to sync `boostExpiresAt` more reliably and survive re-renders.
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify.

#### Phase 2: Chart Zoom & Reset [PLANNED]
* [ ] **Zoom Logic:** Update `ChartCard.tsx` to preserve zoom state during background data refreshes.
* [ ] **Reset Button:** Add a "Reset Zoom" button to the ChartCard header.
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify.

#### Phase 3: Configuration Documentation [PLANNED]
* [ ] **Config Comments:** Add detailed comments to the `learning:` section in `config.default.yaml` explaining auto-tuning and Reflex thresholds.
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify.
