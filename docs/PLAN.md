# Darkstar Energy Manager: Active Plan

**Vision: From Calculator to Agent**
Darkstar is transitioning from a deterministic optimizer (v1) to an intelligent energy agent (v2). It does not just optimize based on static config; it observes context (Weather, Vacation, Prices), predicts outcomes (Aurora ML), and actively strategizes (Strategy Engine) to maximize efficiency and comfort.

---

## Revision Naming Conventions

| Prefix | Area | Examples |
|--------|------|----------|
| **K** | Kepler (MILP solver) | K1-K19 |
| **E** | Executor | E1 |
| **A** | Aurora (ML) | A25-A29 |
| **H** | History/DB | H1 |
| **O** | Onboarding | O1 |
| **UI** | User Interface | UI1, UI2 |
| **DS** | Design System | DS1 |
| **F** | Fixes/Bugfixes | F1-F6 |
| **DX** | Developer Experience | DX1 |
| **ARC** | Architecture | ARC1-ARC* |

---

## 🤖 AI Instructions (Read First)

1.  **Structure:** This file is a **chronological stream**. Newest items are at the **bottom**.

2.  **No Reordering:** Never move items. Only update their status or append new items.

3.  **Status Protocol:**

    -   Update the status tag in the Header: `### [STATUS] REV // ID00 — Title`

    -   Allowed Statuses: `[DRAFT]`, `[PLANNED]`, `[IN PROGRESS]`, `[DONE]`, `[PAUSED]`, `[OBSOLETE]`.

4.  **New Revisions:** Always use the template below.

5.  **Cleanup:** When this file gets too long (>15 completed items), move the oldest `[DONE]` items to `CHANGELOG.md`.


### Revision Template

```

### [STATUS] Rev ID — Title

**Goal:** Short description of the objective.
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

### [PLANNED] REV // UI6 — ChartCard Overlay & Data Toggle

**Goal:** Refactor the `ChartCard` to prioritize visibility of planned actions and forecasts, with a toggleable overlay for actual historical data.

**Context:**
Currently, the charts can become cluttered when mixing planned and actual data. The user wants to ALWAYS see the plan (forecasts, scheduled actions, target SoC) as the primary view, but be able to toggle "Actual" data (load, PV, grid, real SoC) as an overlay for comparison.

**Plan:**

#### Phase 1: Frontend Refactor [PLANNED]
* [ ] Modify `ChartCard.tsx` to separate "Planned/Forecast" series from "Actual" series.
* [ ] Add a UI toggle (e.g., "Show Actual Data") to the chart controls.
* [ ] Implement conditional rendering for actual data series based on the toggle state.

#### Phase 2: Design & Polish [PLANNED]
* [ ] Ensure "Actual" data overlays are visually distinct (e.g., using dashed lines, thinner lines, or lower opacity).
* [ ] Verify legend updates correctly when toggling.


---

### [PLANNED] REV // K22 — Effekttariff (Active Guard)

**Goal:** Implement a dual-layer strategy (Planner + Executor) to minimize peak power usage ("Effekttariff").

**Plan:**

#### Phase 1: Configuration & Entities [PLANNED]
* [ ] Add `grid.import_breach_penalty_sek` (Default: 5000.0) to `config.default.yaml`.
* [ ] Add `grid.import_breach_penalty_enabled` (Default: false) to `config.default.yaml`.
* [ ] Add `grid.import_breach_limit_kw` (Default: 11.0) for the hard executor limit.
* [ ] Add override entities to `executor.config`.

#### Phase 2: Planner Logic (Economic) [PLANNED]
* [ ] **Planner Logic:** Pass the penalty cost to Kepler if enabled.
* [ ] **Re-planning:** Trigger re-plan if penalty configuration changes.

#### Phase 3: Executor Active Guard (Reactive) [PLANNED]
* [ ] **Monitor:** In `executor/engine.py` `_tick`, check `grid_import_power` vs `import_breach_limit_kw`.
* [ ] **Reactive Logic:**
    *   If Breach > Limit:
        *   Trigger `ForceDischarge` on Battery (Max power).
        *   Trigger `Disable` on Water Heating.
        *   Log "Grid Breach Detected! Engaging Emergency Shedding".
* [ ] **Recovery:** Hysteresis logic to release overrides when grid import drops.
* [ ] **Frontend:** Add controls to `Settings > Grid`.

---

### [DONE] REV // ML2: Load Disaggregation [DONE]

> Improving ML forecast accuracy by separating base load from controllable appliances.

**Plan:**

#### Phase 1: Deferrable Load Framework [x]
* [x] Create `backend/loads/` module with `DeferrableLoad` base class supporting binary and variable power control types.
* [x] Implement `LoadDisaggregator` service with sensor validation, fallback strategies, and graceful degradation.
* [x] Add `deferrable_loads` configuration schema to `config.default.yaml` with load type definitions (water, ev, heat_pump, pool_pump).
* [x] Create load registry system for dynamic load type registration and management.

#### Phase 2: Enhanced Recorder Pipeline [x]
* [x] Modify `backend/recorder.py` to use `LoadDisaggregator` for calculating `base_load_kw = total_load_kw - sum(controllable_loads)`.
* [x] Add sensor health monitoring with automatic fallback to total load when individual sensors fail.
* [x] Implement data validation ensuring `base_load_kw >= 0` with warning logs for calculation drift.
* [x] Store clean base load data in existing `load_kwh` column (no schema changes needed).

#### Phase 3: ML Model Refresh [x]
* [x] Clear existing model files to force retraining on clean base load data.
* [x] Add forecast accuracy monitoring comparing base load predictions vs actuals.
* [x] Implement model performance alerts when accuracy degrades below thresholds.

#### Phase 4: Planner Integration [x]
* [x] Update Kepler solver to use disaggregated base load + planned controllable loads in energy balance.
* [x] Add load type validation in planner input processing.
* [x] Create debugging tools to visualize total vs base load forecasts.
* [x] UI & Config Polish: Add manual training, remove redundant risk appetite card, and refine configuration comments.

#### Phase 5: Ad-hoc Pipeline Fixes [x]
* [x] Data Pipeline: Differentiate between "Base Load Forecast" and "Total Load Forecast" in database schema.
* [x] Fix Double Counting: Update `inputs.py` to strictly prefer clean base load forecasts for planning.
* [x] DB Migration: Add `base_load_forecast_kwh` columns to `slot_forecasts` table.
* [x] Inference Refresh: Update `ml/forward.py` to populate the new base load columns.



---

### [PLANNED] REV // UI7 — Mobile Polish & Water Sensor Cleanup

**Goal:** Improve mobile usability and remove visual clutter when features are disabled.

**Plan:**

#### Phase 1: Water Sensor Cleanup [PLANNED]
* [ ] **Conditional Rendering:** In `frontend/src/components/PowerFlowCard`, check if `water_heating` is enabled (from config/state).
* [ ] **Hide Elements:** If disabled, completely hide the water tank bubble and the energy flow line leading to it.

#### Phase 2: Mobile Tooltips [PLANNED]
* [ ] **Chart Configuration:** Adjust the chart tooltip styles (Recharts/Chart.js) to ensure they fit within small screens.
* [ ] **Positioning:** Ensure tooltips do not overflow off-screen or obscure the data point being pressed.

---

---

### [DONE] REV // UI8 — Load Disaggregation Debug View [DONE]

**Goal:** Add a dedicated troubleshooting view for load disaggregation to the Debug page.

**Plan:**

#### Phase 1: Implementation [x]
* [x] Update API types and definitions.
* [x] Refactor `Debug.tsx` into a tabbed interface (Logs vs Loads).
* [x] Implement real-time controllable power list and data quality metrics.
* [x] Add auto-refresh and error handling.
* [x] Pass production-grade linting and type checks.
