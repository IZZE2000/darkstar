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

### [PLANNED] REV // ARC11 — Complete ML Model Training System

**Goal:** Implement missing automatic ML training, create unified training for all model types, and add comprehensive training status UI with production-grade safety features.

**Context:**
- AURORA ML pipeline fails because error correction models are missing but never trained
- Automatic ML training is configured in `config.default.yaml` but not implemented in `SchedulerService`
- Current "Train Model Now" only trains main AURORA models, not error correction models
- No UI feedback for training status, schedules, or model freshness
- System expects both main models and error correction models but only provides manual training for main models

**Plan:**

#### Phase 1: Unified Training Orchestrator [PLANNED]
* [ ] **Create Training Orchestrator:** New `ml/training_orchestrator.py` module with `train_all_models()` function
* [ ] **Training Lock System:** Add simple file-based training lock to prevent concurrent training
* [ ] **Model Backup System:** Copy existing models to `ml/models/backup/` with timestamp before training, keep only last 2 backups
* [ ] **Graduation Level Integration:** Check graduation level using existing `ml.corrector._determine_graduation_level()`
* [ ] **Unified Training Flow:** Train main models (load/PV) using `ml.train.train_models()`, then error correction models using `ml.corrector.train()` only if Graduate level (14+ days)
* [ ] **Detailed Status Return:** Return status including which models were trained, errors, training duration, and partial failure handling
* [ ] **Auto-restore on Failure:** Restore from backup if training fails completely

#### Phase 2: Database Schema & Tracking [PLANNED]
* [ ] **Extend learning_runs Table:** Add migration with new columns:
  * `training_type` VARCHAR ("automatic", "manual")
  * `models_trained` TEXT (JSON array of trained model types)
  * `training_duration_seconds` INTEGER
  * `partial_failure` BOOLEAN (true if some models failed)
* [ ] **Training History Cleanup:** Add cleanup job to keep only last 30 days of training records
* [ ] **Update Learning Queries:** Modify existing learning history queries to include new training fields

#### Phase 3: Automatic Training Implementation [PLANNED]
* [ ] **Scheduler Service Integration:** Modify `backend/services/scheduler_service.py` to add ML training logic to `_loop()` method
* [ ] **Training Schedule Logic:** Add `_should_run_training()` method to check schedule based on `config.ml_training` section
* [ ] **Config Validation:** Validate `run_days` (0-6) and `run_time` (HH:MM format), log warnings and use defaults for invalid values
* [ ] **Training Execution:** Add `_run_ml_training()` method that calls unified training orchestrator
* [ ] **Timezone Handling:** Use local timezone for `run_time` parsing and comparison
* [ ] **Task Status Tracking:** Set `current_task = "ml_training"` during training execution
* [ ] **Retry Logic:** Add retry logic (2 attempts) for failed automatic training with exponential backoff
* [ ] **Training Logging:** Log training trigger reason ("automatic_schedule") and detailed results

#### Phase 4: Manual Training API Updates [PLANNED]
* [ ] **Update Training Endpoint:** Modify `/api/learning/train` in `backend/api/routers/learning.py`
* [ ] **Unified Training Call:** Replace `ml.train.train_models()` call with new unified `train_all_models()`
* [ ] **Concurrency Control:** Check training lock and return appropriate status if training already in progress
* [ ] **Detailed Response:** Return detailed status including individual model training results and duration
* [ ] **Error Handling:** Add proper error handling for partial failures
* [ ] **Manual Training Logging:** Log training trigger reason ("manual") and results

#### Phase 5: Training Status APIs [PLANNED]
* [ ] **Training Status Endpoint:** Create `/api/learning/training-status` endpoint to return current training state
* [ ] **Training History Endpoint:** Create `/api/learning/training-history` endpoint to return recent training attempts
* [ ] **Status Information:** Include training lock status, current operation, and progress information
* [ ] **Model File Status:** Return model file timestamps and ages for status display

#### Phase 6: Model Training Status UI Card [PLANNED]
* [ ] **Create Training Card:** New `ModelTrainingCard.tsx` component in `frontend/src/components/aurora/`
* [ ] **Card Positioning:** Position between "System Health" and "Controls" cards in Aurora tab
* [ ] **Model Status Display:** Show separate status for main models vs error correction models with file timestamps
* [ ] **Age Indicators:** Display "Last trained: X days ago" for each model type
* [ ] **Schedule Display:** Show next scheduled automatic training time
* [ ] **Unified Training Button:** Include "Train Models Now" button with progress indicator
* [ ] **Training History:** Show training history (last 5 training attempts with timestamps, type, and status)
* [ ] **Loading States:** Handle loading states and error messages for individual model types
* [ ] **Concurrency Feedback:** Show "Training in progress..." message and disable button when automatic training is running
* [ ] **Partial Failure Display:** Display partial failure status clearly (e.g., "Main models: ✅, Error correction: ❌")
* [ ] **Graduation Level Indicator:** Show graduation level indicator so users understand why error correction might be disabled

#### Phase 7: Training Progress Feedback [PLANNED]
* [ ] **WebSocket Events:** Add WebSocket events for training progress updates (`training_started`, `training_progress`, `training_completed`)
* [ ] **Progress Percentages:** Include progress percentages in WebSocket events
* [ ] **UI Progress Indicators:** Show progress spinner and disable button during training
* [ ] **Error Message Display:** Display specific error messages for failed model types
* [ ] **Real-time Updates:** Update training history in real-time
* [ ] **Duration Display:** Show training duration and completion status

#### Phase 8: Config Migration & Validation [PLANNED]
* [ ] **Config Migration:** Update `backend/config_migration.py` to add default `ml_training` config if missing
* [ ] **Default Values:** Set defaults: `enabled: true`, `run_days: [1, 4]`, `run_time: "03:00"`
* [ ] **Future Flexibility:** Add optional `error_correction_enabled: true` config key for future flexibility
* [ ] **Migration Validation:** Validate config values during migration and log warnings for invalid values

#### Phase 9: Scheduler Status Integration [PLANNED]
* [ ] **Extend Scheduler Status:** Extend `SchedulerStatus` dataclass to include training schedule info
* [ ] **Training Status Fields:** Add `next_training_at`, `last_training_at`, `last_training_status`, `training_enabled` fields
* [ ] **API Updates:** Update `/api/scheduler/status` endpoint to return training information
* [ ] **Lock Status:** Include training lock status for UI feedback

#### Phase 10: Immediate Error Correction Fix [PLANNED]
* [ ] **Quick Fix Script:** Create temporary script or API endpoint to manually train error correction models
* [ ] **Graduation Check:** Check graduation level before attempting error correction training
* [ ] **Clear Feedback:** Provide clear feedback about why error correction training was skipped (if not Graduate level)

#### Phase 11: Integration Testing [PLANNED]
* [ ] **Schedule Testing:** Test automatic training schedule calculation across timezone changes and DST transitions
* [ ] **Concurrency Testing:** Test manual training during automatic training (should show progress or disable button)
* [ ] **Failure Scenarios:** Test partial failure scenarios (main models succeed, error correction fails)
* [ ] **Graduation Transitions:** Test graduation level transitions (infant -> statistician -> graduate)
* [ ] **Config Validation:** Test config validation with invalid values
* [ ] **Backup & Restore:** Test backup and restore functionality
* [ ] **WebSocket Events:** Verify WebSocket events work correctly for training progress
* [ ] **History Cleanup:** Test training history cleanup (30-day retention)

#### Phase 12: Logging & Documentation [PLANNED]
* [ ] **Comprehensive Logging:** Add comprehensive logging for all training operations with clear prefixes
* [ ] **Trigger Logging:** Log training trigger reasons (automatic_schedule vs manual)
* [ ] **Graduation Logging:** Log graduation level decisions for error correction training
* [ ] **Success Logging:** Add training duration and model count to success logs
* [ ] **Error Context:** Ensure all training errors are logged with sufficient context for debugging
* [ ] **Backup Logging:** Log backup restore failures and continue with broken models

---
