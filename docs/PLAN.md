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

### [DONE] REV // PERS1 — HA Add-on Persistent Storage

**Goal:** Fix critical bug where ML models and schedule.json are not persisted across container restarts in the HA add-on deployment, making debugging impossible and causing planner to fall back to heuristics.

**Context:**
- HA add-on uses `/share/darkstar/` for persistent storage, symlinked to `/app/data/`
- Models were being saved to ephemeral `/app/ml/models/` → Lost on restart
- Schedule was being saved to ephemeral `/app/schedule.json` → Lost on restart
- Database (`planner_learning.db`) was already correctly using `data/` → Working fine

**Changes:**
* [x] Update `ml/train.py` L28: `models_dir = Path("data/ml/models")`
* [x] Update `ml/train.py` L57: `delete_trained_models()` default path
* [x] Update `ml/forward.py` L19: `_load_models()` default path
* [x] Update `ml/training_orchestrator.py` L18: `MODELS_DIR` constant
* [x] Update `ml/corrector.py` L133,185,210,288: All function default paths
* [x] Update `planner/output/schedule.py` L46: `output_path = "data/schedule.json"`
* [x] Update `executor/config.py` L117,331: `schedule_path` defaults
* [x] Update `darkstar/Dockerfile` L42: Create `data/ml/models` at build time
* [x] Document persistence architecture in `docs/ARCHITECTURE.md` (New Section 14)

**Impact:**
- ✅ ML models now persist across restarts
- ✅ Schedule.json visible in `/share/darkstar/` for debugging
- ✅ Training runs successfully update models in persistent location
- ✅ Executor can always find current schedule
- ✅ Database, models, and schedule all in same persistent directory

**Files Modified:**
- `ml/train.py` - Training models directory
- `ml/forward.py` - Forward inference models directory
- `ml/training_orchestrator.py` - Training orchestrator constants
- `ml/corrector.py` - Error correction models directory
- `planner/output/schedule.py` - Schedule output path
- `executor/config.py` - Schedule path defaults
- `darkstar/Dockerfile` - Build-time directory creation
- `docs/ARCHITECTURE.md` - New Section 14: Persistence Architecture
- `docs/PLAN.md` - This revision entry

---

### [DONE] REV // PERS2 — HA Add-on Planner Regression Fix

**Goal:** Fix critical planner regression where HA Add-on produces flat schedules (no charge/discharge) because ML models fail to load silently.

**Root Cause:**
1. **Path Inconsistencies** - Several files used old `ml/models/` path while core ML code used `data/ml/models/`. Training saved to `data/`, but some code loaded from `ml/`.
2. **Silent Failure** - `_load_models()` returns empty dict `{}` on failure with just an "Info" log. Empty models → zero forecasts → trivial MILP → 0.2s solve time.
3. **Dockerfile Bug** - Only copied `ml/*.py`, not `ml/models/*.lgb`. Images shipped without models.

**Plan:**

#### Phase 1: Ship Baseline Models [DONE]
* [x] Remove `ml/models/` from `.gitignore` (only `antares_*` subdirs ignored)
* [x] Add `ml/models/*.lgb` files to git tracking (10 models)

#### Phase 2: Fix Path Inconsistencies [DONE]
* [x] Update `ml/evaluate.py` L31 → `data/ml/models`
* [x] Update `scripts/health_check.py` L320,389,391,432 → `data/ml/models`, `data/schedule.json`
* [x] Update `scripts/train_corrector.py` L21,91 → `data/ml/models`
* [x] Update `scripts/diagnose_ml.py` L56 → `data/ml/models`
* [x] Update `backend/api/routers/learning.py` L251 → LOCK_FILE path fix

#### Phase 3: Robust Model Loading [DONE]
* [x] Update `ml/forward.py`: Log CRITICAL error when no models loaded
* [x] Update `ml/forward.py`: Load fallback (0.5 kWh baseline average)
* [x] Update `ml/forward.py`: PV fallback (Open-Meteo radiation-based)

#### Phase 4: Startup Model Copy [DONE]
* [x] Update `darkstar/Dockerfile`: Ship `ml/models/*.lgb` with image
* [x] Update `darkstar/run.sh`: Copy models to persistent storage on first boot

**Impact:**
- ✅ Models now tracked in git → shipped with Docker image
- ✅ All code paths use consistent `data/ml/models` location
- ✅ Fallback ensures planner never silently runs with zero forecasts
- ✅ First-boot model copy ensures fresh installs work immediately
- ✅ User-trained models are never overwritten

---

### [DONE] REV // F38 — AURORA Pipeline Data Structure Fix

**Goal:** Fix critical AURORA ML inference pipeline failure causing flat battery schedules in v2.5.5-beta due to data structure mismatch between ML API and forecast retrieval.

**Root Cause:**
The ML API (`ml/api.py`) changed forecast data structure from flat to nested format, but `inputs.py` was not updated to match:
- **Old format**: `{"pv_forecast_kwh": 1.5, "load_forecast_kwh": 0.8}`
- **New format**: `{"final": {"pv_kwh": 1.5, "load_kwh": 0.8}, "probabilistic": {...}}`

This caused `KeyError: 'pv_forecast_kwh'` during forecast data retrieval, not ML inference. The error was misleading - models were working correctly.

**Plan:**

#### Phase 1: Fix Data Structure Access [DONE]
* [x] Update `inputs.py` L819-825: Use `rec["final"]["pv_kwh"]` instead of `rec.get("pv_forecast_kwh")`
* [x] Update `inputs.py` L425-430: Fix daily forecast aggregation data access
* [x] Verify other forecast access points use correct structure

#### Phase 2: Version Release [DONE]
* [x] Bump version to v2.5.6-beta in all 8 locations:
  - `/VERSION`
  - `/package.json`
  - `/config.default.yaml`
  - `/darkstar/config.yaml`
  - `/darkstar/run.sh`
  - `/frontend/package.json`
* [x] Update `docs/RELEASE_NOTES.md` with comprehensive fix description

**Impact:**
- ✅ AURORA ML pipeline completes successfully without KeyError
- ✅ Battery schedules show proper charging/discharging actions instead of flat SoC
- ✅ `/api/run_planner` returns 200 with valid schedule instead of 524 timeout
- ✅ Error reporting accurately distinguishes ML failures from data retrieval failures
- ✅ Fallback logic works correctly when models are actually missing

**Files Modified:**
- `inputs.py` - Fixed forecast data structure access in two functions
- All version files - Bumped to v2.5.6-beta
- `docs/RELEASE_NOTES.md` - Added comprehensive release notes
