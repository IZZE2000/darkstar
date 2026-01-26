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

5.  **Cleanup:** When this file gets too long (>10 completed REV's), notify the user.


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

### [DONE] REV // K16 — Water Heating Optimization (Recovered)

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
* [x] **Commit:** "feat(planner): implement soft sliding window for water heating"

#### Phase 2: Reliability (Soft Constraints) [DONE]
**Objective:** Prevent "Infeasible" crashes during edge cases.
* [x] **Concept:** Convert hard constraints (Min kWh, Spacing) to soft constraints + penalty.
* [x] **Implementation:** `sum(...) <= M + slack[t]`.
* [x] **Verification:** "Impossible Scenario" (200kWh demand in 48h) no longer crashes.
* [x] **Commit:** "feat(planner): soft constraints for water heating reliability"

#### Phase 3: Layout Safety (Max Block Length) [OBSOLETE]
**Objective:** Fallback mechanism if Phase 1 fails.
* [x] **Status:** SCRAPPED. Verified in "Mirrored Stress Test" that Phase 1 (Soft Window) naturally breaks up blocks even under extreme price incentive flips. Hard limits are not needed.

#### Phase 4: Performance (Variable Optimization) [DONE]
**Objective:** Final speed optimization by balancing binaries and soft constraints.
* [x] **Hypothesis:** Removing binaries caused a performance regression due to loss of solver guidance.
* [x] **Implementation:** Restored `water_start` (Binary) and Hard Spacing constraints. Kept `min_kwh` as a Soft Constraint.
* [x] **Result:** "Stress" scenario down to 7s (was 23s). "Reference (Cheap)" down to 36s. "Expensive" remains < 1s.
* [x] **Commit:** "feat(planner): optimize water constraints with hybrid hard/soft approach"


#### Phase 5: Documentation & Release [DONE]
* [x] **Docs:** Update `docs/DEVELOPER.md` with new benchmarking notes.
* [x] **Cleanup:** Removed legacy `discomfort` and `water_start` logic.
* [x] **Verification:** Verified all reliability and performance targets.
* [x] **Final Commit after user review:** "feat(planner): optimize water constraints with hybrid hard/soft approach".
* [x] **Final Commit after user review:** "feat(planner): optimize water constraints with hybrid hard/soft approach".


### [DONE] REV // K17 — Configuration Exposure & Polish

**Goal:** Expose all hardcoded solver constraints to `config.yaml`, unify "Comfort Level" logic, and prepare UI schema for Advanced Mode (UI10).

**Plan:**

#### Phase 1: Audit & Categorization [DONE]
* [x] Audit all hardcoded keys in `adapter.py` vs `types.py`.
* [x] Create Categorized Audit Report in `docs/reports/REV_K17_CONFIG_AUDIT.md`.
* [x] Review categorization (UI Normal vs UI Advanced vs Config Only) with user.

#### Phase 2: Configuration & Backend [DONE]
* [x] **Config:** Add new Category B/C keys to `config.default.yaml` (defaults matching K16 hardcodes).
* [x] **Adapter:** Update `config_to_kepler_config` in `adapter.py` to map all exposed keys.
* [x] **Cleanup:** Remove hardcoded defaults in `types.py` (ensure everything flows from config).

#### Phase 3: Verification [DONE]
* [x] **Benchmark:** Run `scripts/benchmark_kepler.py` to ensure performance parity (0 regression).
* [x] **Unit Test:** Verified with `benchmark_kepler.py` passing (0.07s on Heavy scenario).

#### Phase 4: UI Exposure [DONE]
* [x] **Water Heating Config:** Edit `frontend/src/pages/settings/types.ts`. Added the following fields to the `Water Heating` section in `parameterSections`:
    *   `reliability_penalty_sek`: type `number`, label "Reliability Penalty (SEK)", helper "Heavy penalty for failing to meet the daily min kWh quota (higher = stricter quota enforcement)."
    *   `block_penalty_sek`: type `number`, label "Block Penalty (SEK)", helper "Small penalty per active heating slot (higher = encourages shorter, more efficient heat blocks)."
    *   `block_start_penalty_sek`: type `number`, label "Block Start Penalty (SEK)", helper "Penalty per heating start (higher = more consolidated bulk heating)."
    *   **STATUS:** Marked as `subsection: 'Advanced Tuning'` and `isAdvanced: true`.
* [x] **Solver Tuning:** Edit `frontend/src/pages/settings/types.ts`. Added the following fields to the `Arbitrage & Economics` section in `parameterSections`:
    *   `target_soc_penalty_sek`: type `number`, label "Target SoC Penalty (SEK)", helper "Penalty for missing the seasonal target SoC (higher = stricter adherence to reserve)."
    *   `curtailment_penalty_sek`: type `number`, label "Curtailment Penalty (SEK)", helper "Penalty for wasting available solar power when battery is not full (higher = more aggressive charging)."
    *   `ramping_cost_sek_per_kw`: type `number`, label "Ramping Cost (SEK/kW)", helper "Penalty for rapid battery power changes (higher = smoother power flow, reduces \"sawtooth\" behavior)."
    *   **STATUS:** Marked as `subsection: 'Advanced Tuning'` and `isAdvanced: true`.
* [x] **Schema Prep:** Updated `BaseField` interface to include `isAdvanced?: boolean` in preparation for REV UI10.

---

### [DONE] REV // UI10 — Advanced Settings Mode

**Goal:** Simplify the settings experience by implementing a global "Advanced Mode" that hides complex technical parameters by default.

**Plan:**

#### Phase 1: Foundation (UI & Persistence) [DONE]
* [x] **State Management:** Add `advancedMode` state to `frontend/src/pages/settings/index.tsx`, persisting to `localStorage` (key: `darkstar_ui_advanced_mode`).
* [x] **Header Layout:** Refactor the Settings tab bar in `index.tsx` to use `flex justify-between`, placing tabs on the left and the new toggle on the right.
* [x] **Toggle Component:** Implement the "Advanced Mode" switch:
    *   **Inactive:** Green style (`bg-good`), "Standard Mode".
    *   **Active:** Orange/Red style (`bg-bad`), "Advanced Mode", with a warning icon.
* [x] **Prop Drilling:** Update `ParametersTab`, `SystemTab`, and `SettingsField` to accept the `advancedMode` boolean prop.

#### Phase 2: Schema & Filtering Logic [DONE]
* [x] **Type Update:** Add `isAdvanced?: boolean` to the `BaseField` interface in `types.ts`.
* [x] **Component Logic:** Update `SettingsField.tsx` to return `null` if `(!advancedMode && field.isAdvanced)`.
* [x] **Verification Point:** Manually verify that field filtering works as expected.
* [x] **Commit:** `feat(ui): implement conditional rendering for advanced settings (UI10 Phase 2)`

#### Phase 3: Key Migration & Re-organization [DONE]
* [x] **Review & Tag Keys:** Applied `isAdvanced: true` to forecasting tuning, water heating tuning, and kepler solver tuning.
* [x] **Re-organize:** Moved `battery_cycle_cost_kwh` to System tab (Battery Specification).
* [x] **Cleanup:** Removed `automation.schedule.jitter_minutes` from UI and deprecated in `config.yaml`.
* [x] **Verification:** Verified that System tab remains fully functional in Standard Mode.
* [x] **Commit:** `feat(ui): migrate technical settings to advanced mode (UI10 Phase 3)`

#### Phase 4: UI Refinement (Option B) [DONE]
* [x] **Lock Notice Component:** Created `AdvancedLockedNotice` for empty sections.
* [x] **Integration:** Added adaptive notices to `SystemTab`, `ParametersTab`, and `UITab`:
    *   Show "Locked" notice if a section is entirely advanced.
    *   Show footer notice if a section has mixed fields.
* [x] **Tagging Refinement:** Completed `isAdvanced` tagging for all `learning.*` and `s_index.*` fields.
* [x] **Verification:** Verified notice visibility in Standard Mode and correct unlocking in Advanced Mode.
* [x] **Commit:** `feat(ui): implement advanced settings notice and refined tagging (UI10 Phase 4)`

#### Phase 5: Transition Animations (Framer Motion) [DONE]
* [x] **Refactoring:** Removed internal visibility filtering from `SettingsField` to enable mount/unmount animations.
* [x] **Animation Engine:** Integrated `framer-motion` with `AnimatePresence` in all Settings tabs.
* [x] **FX Implementation:** Added "fade and slide" transitions for fields and "locked" notices.
* [x] **Type Safety:** Cleaned up TypeScript props and removed unused `advancedMode` from children.
* [x] **Verification:** Confirmed smooth layout shifts and visual fluidity during mode toggles.
* [x] **Commit:** `feat(ui): add smooth transitions for advanced settings (UI10 Phase 5)`

#### Phase 6: Ultra-Compact Standard Mode Layout [DONE]
* [x] **Card Logic:** Refactored all tabs to hide entire cards if all fields are advanced.
* [x] **Global Notice:** Created `GlobalAdvancedLockedNotice` and placed it at the bottom of each tab to centralize the "hidden settings" info.
* [x] **Micro-Notices:** Kept footer notices for cards with mixed content to avoid confusion.
* [x] **Verification:** Confirmed significant vertical space reduction in Standard Mode.
* [x] **Commit:** `feat(ui): implement ultra-compact settings layout for standard mode (UI10 Phase 6)`

---

### [DONE] REV // UI11 — Enhanced Execution History with Entity Visibility & Status Verification

**Goal:** Improve the Execution History display to show which Home Assistant entities are being controlled and whether commands actually succeeded, helping beta users understand and debug inverter integration issues.

**Plan:**

#### Phase 1: Backend Data Enhancement [DONE]
* [x] **ActionResult Extension:** Extend the `ActionResult` dataclass in `executor/actions.py` to include:
    * `entity_id: str | None = None` - The HA entity being controlled
    * `verified_value: Any | None = None` - Value read back after setting
    * `verification_success: bool | None = None` - Whether verification matched expected value
* [x] **Entity Capture:** Modify all action methods in `ActionDispatcher` class to capture and store the target entity ID in the ActionResult
* [x] **Verification Logic:** Implement post-action verification in `ActionDispatcher`:
    * After successful HA API call, wait 1 second for entity state to update
    * Read back the entity value using existing `ha.get_state_value()` method
    * Compare with expected value and set verification_success flag
    * Skip verification in shadow mode (but still capture entity_id and target value)
* [x] **ExecutionRecord Integration:** Update `_create_execution_record()` in `executor/engine.py` to capture ActionResult details including entity info and verification status
* [x] **Commit:** `feat(executor): add entity tracking and post-action verification (UI11 Phase 1)`

#### Phase 2: Database Schema & Storage [DONE]
* [x] **ExecutionLog Model:** Extend the `ExecutionLog` model in `backend/learning/models.py` to store action details:
    * Add `action_results` JSON field to store array of ActionResult data
    * Ensure backward compatibility with existing records
* [x] **History Manager:** Update `ExecutionHistory.log_execution()` in `executor/history.py` to serialize and store ActionResult data in the new field
* [x] **API Response:** Modify `/api/executor/history` endpoint in `backend/api/routers/executor.py` to include action_results in response
* [x] **Migration Safety:** Ensure existing execution records without action_results continue to display properly
* [x] **Commit:** `feat(db): extend execution log schema for action tracking (UI11 Phase 2)`

#### Phase 3: Frontend Status Display Enhancement [DONE]
* [x] **Color Coding System:** Implement status color coding in the "Commanded (What We Set)" section of `frontend/src/pages/Executor.tsx`:
    * Green (🟢): Command sent and verified successfully
    * Blue (🔵): Skipped due to idempotent logic (already at target value)
    * Red (🔴): Failed (either HA API error or verification mismatch)
    * Purple (🟣): Shadow mode (shows target value that would have been sent)
* [x] **Entity Information Display:** Add entity ID display under each commanded value:
    * Show full entity ID (e.g., "number.inverter_max_charge_current")
    * Use small, muted text styling for minimal visual impact
    * Only display when action_results data is available
* [x] **Status Indicators:** Apply color coding to both the colored dot/icon and the value text itself for clear visual feedback
* [x] **Backward Compatibility:** Ensure execution records without new action data continue to display with existing styling
* [x] **Commit:** `feat(ui): implement entity visibility and status colors in execution history (UI11 Phase 3)`

#### Phase 4: Shadow Mode Enhancement [DONE]
* [x] **Shadow Mode Logic:** Update shadow mode behavior in `ActionDispatcher` to:
    * Capture current entity values without sending commands
    * Show target values that would have been set
    * Display purple color coding for all shadow mode actions
    * Maintain same entity information display as normal mode
* [x] **Visual Distinction:** Ensure shadow mode entries are clearly distinguishable with purple styling throughout the execution history
* [x] **Testing:** Verify shadow mode provides complete visibility into what actions would be taken without actually controlling devices
* [x] **Commit:** `feat(executor): enhance shadow mode with full action visibility (UI11 Phase 4)`

#### Phase 5: Error Handling & Edge Cases [DONE]
* [x] **Verification Timeout:** Handle cases where entity state doesn't update within verification window:
    * Implement reasonable timeout (2-3 seconds max)
    * Mark as verification failed if timeout exceeded
    * Log appropriate error messages for debugging
* [x] **Missing Entity Handling:** Gracefully handle cases where configured entities don't exist or are unavailable
* [x] **Partial Failure Display:** Ensure individual action failures are clearly shown when some commands succeed and others fail in the same execution
* [x] **Performance Impact:** Verify that verification delays don't significantly impact executor performance or timing
* [x] **Commit:** `feat(executor): robust error handling for entity verification (UI11 Phase 5)`

#### Phase 6: Testing & Validation [DONE]
* [x] **Integration Testing:** Test with real inverter entities to ensure verification works across different device types and response times
* [x] **UI Responsiveness:** Verify execution history remains performant with enhanced data display
* [x] **Beta User Feedback:** Validate that the enhanced display provides the debugging information needed for inverter integration
* [x] **Documentation Update:** Update relevant documentation to explain the new status indicators and entity visibility features
* [x] **Commit:** `test(ui11): validate enhanced execution history functionality (UI11 Phase 6)`

#### Phase 7: Critical Fixes & Performance Optimization [DONE]
* [x] **Async Verification:** Convert verification from blocking `time.sleep(1.0)` to async `asyncio.sleep(1.0)`:
    * Make `_verify_action()` method async in `ActionDispatcher`
    * Make all action methods (`_set_work_mode`, `_set_grid_charging`, etc.) async
    * Update `ActionDispatcher.execute()` to be async and use `await`
    * Update executor engine to await the async execute call
* [x] **Verification Tolerance Fix:** Change numeric matching tolerance from ±1.0 to ±0.1 in `_verify_action()` method for more precise verification
* [x] **Shadow Mode Logic Fix:** Fix ActionStatusIndicator to check individual action shadow status instead of global shadow mode:
    * Remove `shadowMode` parameter from ActionStatusIndicator
    * Check `result.skipped && result.message.includes('[SHADOW]')` to detect shadow mode actions
    * Only show purple status for actions that were actually in shadow mode
* [x] **UI Consolidation:** Remove duplicate command display by consolidating into single enhanced section:
    * Remove the old "Commanded (What We Set)" section entirely from Executor.tsx
    * Rename "Control Verification" section to "Commanded (What We Set)"
    * Ensure color coding and entity information display correctly in the consolidated view
* [x] **Commit:** `fix(ui11): async verification, precise tolerance, and consolidated UI (UI11 Phase 7)`

---

### [DONE] REV // UI12 — Move Debug Tab to Settings

**Goal:** Clean up the sidebar by moving the Debug tab into the Settings page, making it accessible only in Advanced Mode.

**Plan:**

#### Phase 1: Implementation [DONE]
* [x] **Sidebar:** Remove Debug link from sidebar.
* [x] **Debug Page:** Refactor `Debug.tsx` to export reusable `DebugContent`.
* [x] **Settings:** Integrate `DebugContent` into `Settings` page as a new tab.
* [x] **Conditional Logic:** Make Debug tab visible only when `advancedMode` is true.
* [x] **UI Polish:** Adjust logs view height and container width for optimal display in Settings context.
* [x] **Commit:** `feat(ui): move debug tab to settings advanced mode (REV UI12)`

---

### [DONE] REV // K23 — Water Comfort Multi-Parameter Control

**Goal:** Make Water Comfort levels (1-5) actually functional by controlling multiple existing solver penalties simultaneously, providing meaningful Economy vs Comfort trade-off.

**Context:** Water Comfort levels currently only control a deprecated gap penalty that was disabled in K16 for performance reasons. Users can adjust the comfort level but it has no actual effect on water heating behavior.

**Plan:**

#### Phase 1: Baseline Performance Benchmark [DONE]
* [x] **Benchmark Script:** Run `scripts/benchmark_kepler.py` to establish current performance baseline.
* [x] **Commit Baseline:** Saved benchmark results for comparison after implementation.

#### Phase 2: Multi-Parameter Penalty Mapping [DONE]
* [x] **Function Redesign:** Modify `_comfort_level_to_penalty()` in `planner/solver/adapter.py` to return penalty tuple instead of single value.
* [x] **Penalty Matrix:** Implement comfort level to penalty mapping:
    * Level 1 (Economy): reliability=5, block_start=1.5, block=0.25
    * Level 2 (Balanced): reliability=15, block_start=2.25, block=0.375
    * Level 3 (Neutral): reliability=25, block_start=3.0, block=0.50
    * Level 4 (Priority): reliability=60, block_start=4.5, block=0.75
    * Level 5 (Maximum): reliability=300, block_start=7.5, block=1.0
* [x] **Adapter Integration:** Update `config_to_kepler_config()` to apply all penalty values from comfort level mapping.

#### Phase 3: Configuration Integration [DONE]
* [x] **Override Logic:** Ensure comfort level overrides individual penalty settings in config when enabled.
* [x] **Preserve Spacing:** Keep `spacing_penalty_sek` unchanged at current 0.20 SEK value.
* [x] **Validation:** Verify comfort level setting affects water heating behavior as expected.

#### Phase 4: Performance Validation [DONE]
* [x] **Regression Testing:** Run benchmark suite again with new implementation.
* [x] **Performance Check:** Ensure solve times remain within 10% of baseline across all scenarios.
* [x] **Comfort Level Testing:** Test all comfort levels (1-5) for performance impact.

#### Phase 5: Behavioral Testing & Documentation [DONE]
* [x] **Economy Testing:** Verify Level 1 allows skipping quota during expensive periods (>5 SEK extra cost).
* [x] **Maximum Testing:** Verify Level 5 prioritizes quota regardless of cost (up to 300 SEK penalty).
* [x] **Documentation:** Update relevant docs explaining new comfort level behavior and penalty mapping.
* [x] **Final Validation:** Confirm comfort levels provide meaningful Economy vs Comfort trade-off.

---

### [DONE] REV // F38 — Critical Asyncio Executor Fix

**Goal:** Fix critical `RuntimeError` in executor engine where `asyncio.run()` is called from within a running event loop, breaking the executor.

**Plan:**

#### Phase 1: Engine Async Refactor [DONE]
* [x] **Async Engine:** Convert `ExecutorEngine._tick`, `run_once` to async methods.
* [x] **Await Actions:** Replace `asyncio.run(dispatcher.execute)` with `await dispatcher.execute`.
* [x] **Loop Management:** Update `resume` and `_run_loop` to correctly schedule the async tick using `asyncio.create_task` or `asyncio.run` as appropriate for the context.
* [x] **Tests:** Verify fix with `tests/test_executor_engine.py` to ensure no `RuntimeError`.

#### Phase 2: Verification [DONE]
* [x] **Action Verification:** Ensure async actions (HA calls) execute correctly.
* [x] **Logging:** Verify execution history is logged successfully after async refactor.

---

### [DONE] REV // F39 — Test Suite Stabilisation

**Goal:** Fix the 7 failing tests identified during the V2 environment verification.
**Plan:**

#### Phase 1: Config Integration [DONE]
* [x] **Fix `test_config_mapping`:** Update `tests/test_config_integration.py` to account for the "Comfort Level" adapter logic which overrides raw config values (e.g. `reliability_penalty_sek`).

#### Phase 2: Executor Health (Async) [DONE]
* [x] **Fix `test_executor_engine_captures_action_errors`:** Convert the test to `async` and validly `await` the `_tick()` method, resolving the `RuntimeWarning` and `assert False` failure.

#### Phase 3: Executor Override Logic [DONE]
* [x] **Fix `test_no_slot_exists_triggers_fallback`:** Investigate missing `grid_charging` key in `OverrideResult`. Update expectation or restore key if it was a regression.

#### Phase 4: Kepler Export Logic [DONE]
* [x] **Fix `test_kepler_solver_export_disabled`:** Fix the solver constraint generation in `planner/solver/kepler.py`. Currently `enable_export: False` is ignored by the MILP solver.

#### Phase 5: Kepler Spacing Logic [DONE]
* [x] **Fix `test_strict_spacing_enforced` & `test_spacing_disabled`:** Investigate why water heating isn't triggering despite cheap prices. Likely a penalty tuning issue or a regression in `water_heating_binary` constraints.

#### Phase 6: Schedule Overlay Logic [DONE]
* [x] **Fix `test_today_with_history_includes_planned_actions`:** Investigate why `soc_target_percent` is returning `14.0` (likely `min_soc` + buffer) instead of the plan's `50.0`. Fix the "Merge History" logic in `backend/api/routers/schedule.py`.

#### Phase 7: Final Validation [DONE]
* [x] **Full Test Suite:** Run `uv run python -m pytest` and verify 0 failures.
* [x] **Run Linting:** Verify `./scripts/lint.sh` passes.

---

### REV // K24 — Dynamic Water Comfort Windows

**Goal:** Fix water comfort levels (1-5) by implementing dynamic sliding window sizes that provide meaningful Economy vs Comfort trade-off, replacing the current hardcoded 2.0h window with comfort-level-dependent windows.

**Context:** Current water comfort system uses K16's "Soft Sliding Window" (`block_overshoot` penalty) but hardcodes 2.0h windows for all comfort levels. This prevents true comfort differentiation - Economy users want bulk heating in cheap periods (large windows), while Maximum comfort users want frequent, spread-out heating (small windows).

**Plan:**

#### Phase 1: Investigation & Baseline [DONE]
* [x] **Current Behavior Analysis:** Document current `block_overshoot` penalty behavior with 2.0h hardcoded windows.
* [x] **Benchmark Script:** Run `scripts/benchmark_kepler.py` to establish performance baseline before changes.
* [x] **Test Scenarios:** Create test cases showing Level 1 vs Level 5 should produce different heating patterns.
* [x] **Key Finding:** Comfort levels show limited differentiation due to hardcoded 2.0h window ceiling. Level 5 creates more blocks (3 vs 2) but all hit same 2.0h max block size.

#### Phase 2: Dynamic Window Implementation [TODO]
* [ ] **Window Size Mapping:** Implement comfort-level-dependent `max_block_hours` in `_comfort_level_to_penalty()`:
  * Level 1 (Economy): 4.0h windows = bulk heating in cheap periods
  * Level 2 (Balanced): 3.0h windows = moderate consolidation
  * Level 3 (Neutral): 2.0h windows = current behavior
  * Level 4 (Priority): 1.5h windows = more frequent heating
  * Level 5 (Maximum): 1.0h windows = frequent, spread-out heating
* [ ] **Adapter Integration:** Update `config_to_kepler_config()` to pass dynamic `max_block_hours` to solver.
* [ ] **Solver Update:** Modify `kepler.py` to accept `max_block_hours` parameter instead of hardcoded 2.0.

#### Phase 3: Penalty Scaling [TODO]
* [ ] **Penalty Calibration:** Scale `water_block_penalty_sek` values to be meaningful vs electricity costs (~1.5 SEK/slot):
  * Level 1: Low penalty (5-10 SEK) = allows window violations for cheap prices
  * Level 5: High penalty (50-100 SEK) = strictly enforces small windows
* [ ] **Balance Testing:** Ensure penalties are strong enough to affect behavior but not so high they dominate electricity costs.

#### Phase 4: Validation & Testing [TODO]
* [ ] **Behavioral Testing:** Verify Level 1 produces bulk heating patterns while Level 5 produces frequent heating.
* [ ] **Performance Testing:** Ensure solve times remain <3s after dynamic window implementation.
* [ ] **Edge Case Testing:** Test extreme scenarios (very cheap/expensive periods) to ensure comfort levels still differentiate.

#### Phase 5: Documentation & Release [TODO]
* [ ] **User Documentation:** Update comfort level descriptions to explain window size behavior.
* [ ] **Technical Documentation:** Document the two-parameter comfort system (window size + penalty).
* [ ] **Final Validation:** Confirm all comfort levels (1-5) produce visibly different heating schedules.
