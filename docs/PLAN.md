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

## **REV // K16: Simplify Water Heating Constraints**

**Problem Statement:**
Current water heating MILP implementation is overly complex with ~746 variables and ~600 constraints, causing slow solve times and potential solver hangs. The complexity comes from hard constraints, 2-tier gap systems, start detection variables, and hard spacing constraints.

**Requirements:**
- Maintain all current water heating functionality (daily minimum, comfort gaps, block consolidation, spacing)
- Dramatically reduce MILP complexity for faster solve times
- Keep profitable optimization - MILP should still choose optimal heating times
- Preserve user comfort controls via existing comfort_level slider (1-5)

**Background:**
Current implementation uses:
- Hard daily minimum kWh constraints (feasibility requirements)
- 2-tier progressive gap penalty system (8h + 12h thresholds)
- Binary start detection variables (`water_start[t]`) for block consolidation
- Hard spacing constraints preventing heating within `min_spacing_hours`

This creates ~746 extra variables and ~600 constraints just for water heating in a 48-hour horizon.

**Proposed Solution:**
Convert all hard constraints to soft penalties in the objective function, eliminate redundant constraint tiers, and replace complex start detection with simple transition penalties.

**Task Breakdown:**

**Task 1: Create Baseline Performance Benchmark [DONE]**
- [x] Create comprehensive benchmarking script for water heating solver performance
- [x] Measure current solve times, variable counts, constraint counts across different scenarios
- [x] Test with various comfort levels (1-5), different daily minimums, and horizon lengths
- [x] Generate baseline performance report with statistical analysis (mean, p95, max solve times)
- [x] Include memory usage and solver iteration counts if available
- [x] Save benchmark results for before/after comparison
- [x] Test: Script runs reliably and produces consistent measurements
- [x] Demo: Clear baseline metrics showing current solver performance bottlenecks

**Task 2: Convert Daily Minimum to Soft Constraint**
- Replace hard daily minimum kWh constraint with soft penalty approach
- Add `daily_shortfall` continuous variable per day bucket
- Apply high comfort penalty (derived from comfort_level) for unmet daily requirements
- Maintain existing smart deferral logic (defer_up_to_hours)
- Test: Verify daily minimum is still respected with appropriate penalty weights
- Demo: Water heating still meets daily requirements but solver can find solutions even with conflicting constraints

**Task 3: Eliminate 2-Tier Gap System**
- Remove `gap_violation_2` variables and constraints (Tier 2: 1.5x threshold)
- Keep only single-tier gap penalty for `max_hours_between_heating`
- Simplify gap penalty calculation to single penalty rate
- Update comfort_level mapping to compensate for single-tier system
- Test: Verify comfort behavior is preserved with single-tier approach
- Demo: Gap penalties still discourage long heating gaps but with ~50% fewer variables

**Task 4: Replace Start Detection with Transition Penalties**
- Remove `water_start[t]` binary variables and start detection constraints
- Replace with direct transition penalty: `|water_heat[t] - water_heat[t-1]|`
- Apply block consolidation penalty per transition (start/stop events)
- Map existing `block_start_penalty_sek` to transition penalty rate
- Test: Verify heating still consolidates into blocks rather than scattered slots
- Demo: Block consolidation behavior preserved with simpler mathematical formulation

**Task 5: Convert Spacing to Soft Constraint**
- Remove hard spacing constraints that prevent heating within `min_spacing_hours`
- Replace with soft penalty for spacing violations using linear formulation
- Add continuous `spacing_violation[t]` slack variables for each time slot
- Linear constraint: `sum(water_heat[j] for j in recent_window) <= spacing_slots * (1 - water_heat[t]) + spacing_violation[t]`
- Apply penalty rate derived from existing `spacing_penalty_sek` config to slack variables
- Test: Verify spacing behavior is maintained with soft penalties and linear constraints
- Demo: Heating blocks still respect minimum spacing but solver has flexibility for optimization

**Task 6: Update Configuration Mapping**
- Ensure existing config parameters map correctly to new penalty structure
- Verify `comfort_level` (1-5) still produces appropriate penalty weights
- Update penalty calculations in `planner/solver/adapter.py`
- Maintain backward compatibility with existing config files
- Test: Existing configurations produce similar heating behavior
- Demo: User comfort settings work identically to before

**Task 7: Performance Validation and Tuning**
- Re-run benchmark script from Task 1 with simplified implementation
- Compare before/after performance metrics (solve times, variable counts, constraint counts)
- Validate heating behavior matches expectations across comfort levels
- Tune penalty weights if behavior deviates significantly from current implementation
- Add performance metrics logging for constraint count and solve duration
- Test: Solve times improve significantly (target: >50% reduction)
- Demo: Faster planning with equivalent water heating intelligence and comprehensive performance comparison

**Expected Outcomes:**
- Reduce water heating binary variables from ~384 to ~192 (50% reduction - eliminate water_start variables)
- Reduce water heating constraints from ~600 to ~50 (92% reduction)
- Add minimal continuous slack variables for soft constraints (much less expensive than binary variables)
- Maintain all existing functionality: daily minimums, comfort gaps, block consolidation, spacing
- Preserve profitable optimization within MILP framework
- Significantly improve solver performance and stability


---

**Task 8: Performance recovery: Revert to 448de35 and optimize (DONE)**
- Stripped "Gap Penalty" logic that caused 90s solve times.
- Implemented lightweight `Max Block Length` linear constraint (2.0h).
- Successfully split "One Big Block" into two 2-hour segments via `min_spacing_hours` interaction.
- Result: **0.43s solve time** (200x speedup) with correct scheduling behavior.
