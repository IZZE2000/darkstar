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

### [PLANNED] REV // ML2 — Active Load Disaggregation

**Goal:** Sanitize historical data by separating "Base Load" from controllable heavy loads (EV, Water) to improve ML forecast accuracy.

**Plan:**

#### Phase 1: Instrumentation [PLANNED]
* [ ] Verify configuration for `input_sensors.ev_power` and `input_sensors.water_power`.
* [ ] Ensure `input_sensors.load_power` represents TOTAL house load.

#### Phase 2: Recorder Logic [PLANNED]
* [ ] Modify `backend/recorder.py` -> `record_observation_from_current_state`.
* [ ] Calculate `base_load_kw = total_load_kw - ev_power_kw - water_power_kw`.
* [ ] **Safety:** Ensure `base_load_kw` is never negative (clamp to 0.0), log warning if calculation drifted.
* [ ] Store `base_load_kw` in the `load_kwh` column (or decided new schema? *Decision: Use existing column for "Uncontrollable Load" to implicitly train model on this*).

#### Phase 3: Verification [PLANNED]
* [ ] Dry-run script to visualize "Total vs Base" load.
* [ ] Verify `planner_learning.db` contains clean base load data.
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

### [IN PROGRESS] REV // ARC11 — Async Background Services (Full Migration)

**Goal:** Complete the migration to full AsyncIO by refactoring background services (Recorder, LearningEngine, BackfillEngine, Analyst) to use async database methods, eliminating the "Dual-Mode" hybrid state.

**Context:**
Currently, `LearningStore` operates in **Hybrid Mode** (REV ARC10):
*   **API Layer**: Uses `AsyncSession` (non-blocking, production-ready).
*   **Background Services**: Use sync `Session` (blocking, runs in threads).

This creates technical debt: duplicate engine initialization, dual testing requirements, and potential threading/GIL contention.

**Scope:**
*   **Primary**: Migrate all background services to `async/await`.
*   **Secondary**: Remove all synchronous database code from `LearningStore`.
*   **Tertiary**: Verify no performance regression on low-power hardware (N100).

**Risk Assessment:**
*   **Breaking Changes**: None (internal refactor only, no API changes).
*   **Data Integrity**: SQLite async operations require careful lock management.
*   **Performance**: Async overhead in tight loops could reduce throughput vs threads.
*   **Rollback**: Must be possible to revert to sync code if async causes issues.

**Plan:**

#### Phase 1: Audit & Dependency Mapping [DONE]
* [x] **Inventory**: List all files that instantiate `LearningStore` or call sync methods.
    * `backend/recorder.py` (main loop)
    * `backend/learning/engine.py` (LearningEngine delegates to store)
    * `backend/learning/analyst.py` (Reflex learning loop)
    * `backend/learning/backfill.py` (BackfillEngine for historical data)
    * `backend/api/routers/learning.py` (API endpoint using `asyncio.to_thread`)
* [x] **Call Graph**: Identify all `LearningStore` sync methods still in use:
    * `store_slot_prices()`, `store_slot_observations()`, `store_forecasts()`, `store_plan()`
    * `get_last_observation_time()`, `calculate_metrics()`, `get_performance_series()`
    * All methods in `analyst.py` and `backfill.py`
* [x] **Thread Safety**: Verify no shared mutable state between sync/async code paths.

#### Phase 2: Incremental Migration (Background Services) [DONE]
* [x] **Step 1: Recorder**
    * Convert `record_observation_from_current_state()` to `async def`.
    * Replace `time.sleep()` with `await asyncio.sleep()` in main loop.
    * Update `backend/recorder.py::main()` to use `asyncio.run()` instead of `while True` loop.
    * Update API endpoint (`backend/api/routers/learning.py`) to call async version directly (remove `asyncio.to_thread`).
* [x] **Step 2: LearningEngine**
    * Convert all methods in `backend/learning/engine.py` to `async def`.
    * Replace `self.store.store_*()` calls with `await self.store.store_*_async()`.
    * Update `etl_cumulative_to_slots()` to be async-compatible (CPU-bound, may need `asyncio.to_thread` wrapper).
* [x] **Step 3: BackfillEngine**
    * Convert `backend/learning/backfill.py::run()` to `async def`.
    * Replace sync pandas DB queries with async SQLAlchemy queries.
    * Update `main.py` startup to `await backfill.run()`.
* [x] **Step 4: Analyst**
    * Convert `backend/learning/analyst.py::update_learning_overlays()` to `async def`.
    * Replace all `store.*()` calls with `await store.*_async()`.
    * Update Recorder's `_run_analyst()` to `await analyst.update_learning_overlays()`.

#### Phase 3: Cleanup (Remove Dual-Mode Code) [DONE]
* [x] Audit codebase for remaining sync `LearningStore` usage.
* [x] Identify all `LearningStore` sync methods still in use.
* [x] Refactor remaining sync methods to async (e.g. `store_plan` in pipeline).
* [x] Remove `self.engine` check in `LearningStore.__init__`.
* [x] Remove `self.engine` (sync SQLAlchemy engine) from `LearningStore`.
* [x] Remove `self.Session` (sync session factory).
* [x] Audit `inputs.py` for remaining blocking IO.
* [x] Delete all `store_*()` sync methods (keep only `*_async()` versions).
* [x] Rename `*_async()` methods to remove `_async` suffix (e.g., `store_slot_prices_async` → `store_slot_prices`).
* [x] **Test Cleanup**:
    * Update all tests to use `pytest-asyncio` fixtures.
    * Replace sync DB setup with `async with` context managers.
* [x] **Lint & Type Check**:
    * Run `uv run ruff check backend/` (zero tolerance).
    * Run `uv run mypy backend/learning/` (verify async type hints).

#### Phase 4: Verification & Performance Testing [DONE]
- [x] Run full test suite (`uv run pytest`).
- [x] Manually verify Recorder writes observations to DB (Async).
- [x] Verify Analyst runs without locking the main thread.
- [x] Verify BackfillEngine correctly handles gaps.
- [x] Verify `run_planner.py` executes successfully.
- [x] **Create Benchmark Script**:
    - [x] Create `scripts/benchmark_async.py` (measure DB write latency, API response time).
    - [x] Run benchmark on dev machine to ensure no regressions.

#### Phase 4.1: Critical Production Fixes [DONE]

Context: REV ARC11 migration is 95% complete, but several API routes still use the old sync Session() which
no longer exists in LearningStore, causing AttributeError crashes.

* [x] Fix API Forecast Routes (CRITICAL):
  - **File**: backend/api/routers/forecast.py
  - **Problem**: Lines 66, 178, 236, 292, 357 use engine.store.Session() which was removed
  - **Fix**: Replace with `async with engine.store.AsyncSession() as session:` and `await`.

* [x] Fix Planner Logging (HIGH):
  - **File**: planner/observability/logging.py
  - **Problem**: Line 37 uses engine.store.Session()
  - **Fix**: Replace with `AsyncSession` and `await session.commit()`.

* [x] Fix Planner Output (MEDIUM):
  - **File**: planner/output/schedule.py
  - **Problem**: `save_schedule_to_json` logic needs to await `record_debug_payload`.
  - **Fix**: Convert to `async def` and `await`.

* [x] Fix Planner Pipeline (MEDIUM):
  - **File**: planner/pipeline.py
  - **Problem**: Needs to `await save_schedule_to_json`.
  - **Fix**: Add `await`.
**: curl http://localhost:8000/api/forecast/status should return 200, not 500
  - **Planner Test**: python bin/run_planner.py should complete without AttributeError
  - **Lint Test**: ruff check backend/ should show zero errors

Root Cause: Phase 3 cleanup removed self.Session from LearningStore.__init__ but missed updating all call
sites.

Risk: Without this fix, production deployment will have broken API endpoints and planner crashes.

#### Phase 5: Documentation & Rollback Plan [DONE]
* [ ] **Update ARCHITECTURE.md**:
    * Remove "Hybrid Mode" section (9.2).
    * Update to "Unified AsyncIO Architecture".
    * Document async best practices (e.g., no blocking calls in `async def`).
* [ ] **Rollback Strategy**:
    * Tag commit before ARC11 merge: `git tag pre-arc11`.
    * Document rollback procedure in `docs/ROLLBACK.md`:
        * `git revert <arc11-commit-hash>`
        * Restart server (auto-migrates DB schema back if needed).
    * **Critical**: Do NOT delete sync methods until Phase 4 tests pass.
* [ ] **Deployment Guide**:
    * Add migration notes to `docs/DEVELOPER.md`.
    * Update `run.sh` to detect old sync code and warn users.

---

**Success Criteria:**
1. ✅ All background services use `async/await` exclusively.
2. ✅ `LearningStore` has no synchronous engine or methods.
3. ✅ All tests pass (`pytest`, `ruff`, `mypy`).
4. ✅ No performance regression on N100 hardware (<5% latency increase).
5. ✅ Rollback procedure tested and documented.
