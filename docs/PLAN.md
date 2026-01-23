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

### [PLANNED] REV // UI7 — Mobile Polish & Extensible Architecture

**Goal:** Improve mobile usability, fix chart tooltip/legend issues, and make PowerFlowCard extensible for future nodes (EV, heat pump, etc.) using a Node Registry pattern.

**Context:**
- Current PowerFlowCard hardcodes 5 nodes (solar, house, battery, grid, water) - adding EV requires refactoring
- Chart tooltips on mobile overlap chart content (screen too small)
- Tooltip color boxes render as white with color stroke (hard to scan)
- Dotted SoC lines in legend are unclear on mobile

**Plan:**

#### Phase 1: PowerFlowCard Node Registry [PLANNED]
* [ ] **Define Node Registry Types:** Create extensible registry structure:
  ```typescript
  interface FlowNodeConfig {
    id: 'solar' | 'house' | 'battery' | 'grid' | 'water' | 'ev'
    configKey: string  // e.g., 'system.has_solar', 'system.has_water_heater'
    position: { x: number; y: number }
    dataAccessor: (data: PowerFlowData) => NodeData
    connections: string[]  // defines valid flow connections
  }
  ```
* [ ] **Update PowerFlowCard Props:** Add `systemConfig?: Partial<SystemConfig>` prop to receive config
* [ ] **Config-Driven Enabled Check:** Replace hardcoded nodes with registry filtered by config flags:
  * `system.has_solar` → solar node
  * `system.has_battery` → battery node
  * `system.has_water_heater` → water node
* [ ] **Auto-positioning:** Calculate node positions dynamically based on enabled node count
* [ ] **EV Placeholder:** Add EV node entry (`configKey: 'system.has_ev'`, disabled by default)
* [ ] **Particle Streams:** Only render connections between enabled nodes

#### Phase 2: ChartCard Mobile UX [PLANNED]
* [ ] **Bottom Sheet Tooltip:** Replace standard Chart.js tooltip with fixed bottom overlay on mobile:
  * Trigger: Tap any point on chart
  * Position: Fixed overlay at bottom of chart container (thumb-reachable)
  * Desktop: Keep current tooltip behavior
* [ ] **Custom Tooltip Plugin:** Create React-based tooltip component rendered by Chart.js external plugin
* [ ] **Filled Color Boxes:** Fix tooltip color swatches:
  ```typescript
  // Instead of white box with stroke → solid filled box
  backgroundColor: context.dataset.borderColor,
  borderColor: context.dataset.borderColor,
  borderWidth: 2,
  borderRadius: 4,
  ```

#### Phase 3: Legend Polish [PLANNED]
* [ ] **Circle Markers Only:** Replace dotted SoC lines with circle markers:
  * SoC Target: Hollow circle (planned = target)
  * SoC Actual: Filled circle (actual = achieved)
* [ ] **Remove borderDash:** Set `pointStyle: 'circle'` with appropriate `pointRadius`
* [ ] **Mobile Legend Test:** Verify legibility on small screens

#### Phase 4: Dashboard Integration [PLANNED]
* [ ] **Update Dashboard.tsx:** Pass `system` config to PowerFlowCard component:
  ```typescript
  <PowerFlowCard data={flowData} systemConfig={config.system} />
  ```
* [ ] **Mobile Viewport Detection:** Add responsive hook for tooltip mode switching
* [ ] **Overlay Menu Mobile:** Ensure toggle buttons are touch-friendly (44px+ tap targets)

#### Phase 5: Testing & Validation [PLANNED]
* [ ] **Feature Combination Testing:** Verify conditional rendering works for:
  * Solar + Battery + Water (full system)
  * Solar + Battery only (no water)
  * Solar + Water only (no battery)
  * Battery + Water only (no solar)
  * Solar only (minimal system)
* [ ] **Regression Test:** Verify desktop tooltip/legend still works correctly
* [ ] **Mobile Test:** Test bottom sheet tooltip on various screen sizes (320px-428px)
* [ ] **Accessibility:** Verify color indicators work for colorblind users (circle vs filled)

---

## **REV // XX - BACKLOG TASK: Data Quality Spike Filtering** (Rewrite title!)

### **Problem Statement**
Home Assistant sensors occasionally report unrealistic spikes (e.g., 0W → 15,000W → 2,500W
) that corrupt ML training data and forecasting accuracy. Need intelligent filtering to
remove obvious sensor glitches while preserving legitimate rapid changes.

### **Requirements**
1. Filter obvious sensor spikes and glitches from HA data
2. Preserve legitimate rapid changes (heat pump startup, etc.)
3. Apply sensor-specific filtering rules based on physical limits
4. Configurable filtering parameters per sensor type
5. Minimal performance impact on data collection pipeline

### **Proposed Solution**
Implement hybrid filtering approach in inputs.py with:
- Simple threshold filter for obvious spikes (>500% change)
- Sensor-specific physical limits (min/max values)
- Rate-of-change limits per sensor type
- Configurable settings in config.yaml

### **Implementation Plan**

Task 1: Create Data Quality Filter Module
- Add backend/data_quality/filters.py with filtering functions
- Implement threshold, median, and rate-of-change filters
- Add sensor-specific limit definitions
- Demo: Filter functions remove spikes while preserving legitimate changes

Task 2: Add Configuration Schema
- Extend config.yaml with data_quality section
- Define sensor limits for battery_soc, pv_power, load_power, grid_power, temperature
- Add enable/disable toggle for filtering
- Demo: Configurable filtering parameters per sensor type

Task 3: Integrate Filtering in Data Pipeline
- Modify inputs.py to apply filters after HA data collection
- Add filtering to get_ha_sensor_data() function
- Log filtering activity for monitoring
- Demo: Sensor data cleaned before ML processing

Task 4: Add Filtering Metrics
- Track filtering statistics (spikes removed, data quality scores)
- Add filtering metrics to health check script
- Include data quality indicators in Aurora dashboard
- Demo: Visibility into data quality and filtering effectiveness

Task 5: Testing & Validation
- Test with historical spike data
- Validate ML model accuracy improvement
- Ensure legitimate rapid changes preserved
- Demo: Improved forecast accuracy with filtered data

### **Configuration Example**
yaml
data_quality:
  enable_filtering: true
  sensor_limits:
    battery_soc:
      min: 0
      max: 100
      max_change_per_minute: 10
    pv_power:
      min: 0
      max: 15000
      max_change_per_minute: 5000
    load_power:
      min: 0
      max: 20000
      max_change_per_minute: 8000


### **Success Criteria**
1. ✅ Sensor spikes automatically filtered from data pipeline
2. ✅ Legitimate rapid changes preserved (heat pump, EV charging)
3. ✅ Configurable filtering per sensor type
4. ✅ Improved ML model accuracy with cleaner training data
5. ✅ Data quality metrics visible in monitoring

---

### [IN PROGRESS] REV // K16 — Water Heating Optimization (Recovered)

**Goal:** Restore planner performance (<1s) while maintaining smart water heating layout.
**Strategy:** "Linearize Everything." Remove binary constraints (hard/slow) and replace with linear soft penalties (fast/flexible).

**Plan:**

#### Phase 0: Investigation & Stabilization [DONE]
* [x] **Benchmark Script:** Created `scripts/benchmark_kepler.py`.
* [x] **Baseline:** Established ~90s solve time for standard scenarios with Gap Constraint.
* [x] **Diagnosis:** Identified "Gap Penalty" (recursive binary constraints) as combinatorial root cause.
* [x] **Fix 1:** Removed Gap Penalty logic. Result: 0.05s solve time (>1000x speedup) but caused "One Big Block" layout.
* [x] **Fix 2:** Implemented hard `Max Block Length` (2.0h) as interim fix.
* [x] **Current State:** Fast (0.43s), Splits blocks, but constraints are HARD (brittle).

#### Phase 1: Smart Comfort (Soft Sliding Window) [DONE]
**Objective:** Solve "One Big Block" layout organically without hard limits.
* [x] **Concept:** Replace binary "Gap" check with linear "Sliding Window" penalty.
* [x] **Implementation:** `sum(water_heat[t-9:t]) <= 8 + slack[t]`.
* [x] **Pivot:** Switched from "Recursive Discomfort" (slow) to "Sliding Window" (fast).
* [x] **Result:** Solve times < 3s (mostly < 0.5s), blocks broken up successfully.
* [x] **Optimization:** Added Symmetry Breaker (Phase 5) to fix "Cheap" scenario slowness.
* [ ] **Commit:** "feat(planner): implement soft sliding window for water heating"

#### Phase 2: Reliability (Soft Constraints) [PLANNED]
**Objective:** Prevent "Infeasible" crashes during edge cases.
* [ ] **Task 2a - Soft Daily Min:**
    *   Convert `min_kwh_per_day` to soft constraint.
    *   Add slack variable `daily_shortfall[day]`.
    *   Penalty: Huge cost (e.g., 500 SEK/kWh) for shortfall.
* [ ] **Task 2b - Soft Spacing:**
    *   Convert `min_spacing_hours` to soft constraint.
    *   Add slack variable `spacing_violation[t]`.
    *   Penalty: Moderate cost for breaking 5h spacing rule (e.g., if re-heating is urgent).
* [ ] **UPDATE PLAN WITH PROGRESS AND COMMIT PHASE AFTER USER REVIEW**

#### Phase 3: Layout Safety (Max Block Length) [CONDITIONAL]
**Objective:** Fallback mechanism if Phase 1 fails to prevent massive blocks.
* [ ] **Condition:** ONLY execute if Phase 1 (`Discomfort Cost`) fails to break up 5-6h heating blocks on cheap days.
* [ ] **Change:** Convert hard 2h limit to SOFT constraint or configurable `max_continuous_hours`.
* [ ] **Validation:** Verify layout on "Free Electricity Day" scenarios.
* [ ] **UPDATE PLAN WITH PROGRESS AND COMMIT PHASE AFTER USER REVIEW**

#### Phase 4: Performance (Variable Optimization) [PLANNED]
**Objective:** Final speed optimization by removing `water_start` binaries.
* [ ] **Hypothesis:** We can prevent sawtooth (ON-OFF-ON) behavior using linear ramping costs instead of binary start penalties.
* [ ] **Implementation:**
    *   Remove `water_start` binary variables.
    *   Remove `block_start_penalty` logic.
    *   Add `water_ramping_cost`: `|water_heat[t] - water_heat[t-1]| * cost_per_switch`.
* [ ] **Benefit:** Removing ~96 binary variables should drop solve time further and improve stability.
* [ ] **Validation:** Confirm no "chatter" (rapid switching) appears in schedule.
* [ ] **UPDATE PLAN WITH PROGRESS AND COMMIT PHASE AFTER USER REVIEW**

#### Phase 5: Documentation & Release [PLANNED]
* [ ] **Docs:** Update `docs/DEVELOPER.md` with new benchmarking notes.
* [ ] **Cleanup:** Remove legacy commented-out Gap Penalty code.
* [ ] **Final Commit after user review:** "feat(planner): optimize water heating constraints".
