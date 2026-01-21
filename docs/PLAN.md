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

### [DONE] REV // F27 — Recorder & History Fixes

**Goal:** Fix critical bugs in Recorder, Backfill, and History Overlay to ensure data integrity and correct visualization.

**Plan:**

#### Phase 1: Backend Fixes [DONE]
* [x] Fix `TypeError` in `recorder.py` (missing config).
* [x] Fix `BackfillEngine` initialization of `learning_config`.
* [x] Fix `store.get_executions_range` keys (compatibility with `schedule.py`) and SoC bug.

#### Phase 2: Test Suite Stabilization [DONE]
* [x] Fix `tests/test_grid_meter_logic.py`.
* [x] Fix `tests/test_schedule_history_overlay.py` schema and assertions.
* [x] Fix `tests/test_reflex.py` fixture usage (asyncio) and SQL data version.
* [x] Fix `tests/test_learning_k6.py` fixture usage.
* [x] Fix `tests/test_store_plan_mapping.py` fixture usage.

---

### [DONE] REV // F28 — v2.5.1-beta Startup Stabilization

**Goal:** Fix critical startup failures (config migration locking and Alembic path resolution) for the v2.5.1-beta release.

**Changes:**
* [x] Move `migrate_config()` to start of lifespan (Superseded by F29)
* [x] Implement absolute path resolution for `alembic.ini` (Superseded by F29)
* [x] Add container environment debug logging (CWD, config paths).
* [x] Fix `TestClient` lifespan triggering in `tests/test_api_routes.py`.
* [x] Implement build gating in `.github/workflows/build-addon.yml`.

---

### [DONE] REV // F29 — v2.5.1-beta Migration Architecture Fixes

**Goal:** Move migrations to container entrypoint to prevent race conditions and ensure file availability.

**Changes:**
* [x] Move config and database migrations to `docker-entrypoint.sh`.
* [x] Add `alembic.ini` and `alembic/` to `Dockerfile`.
* [x] Remove migration logic from FastAPI `lifespan`.
* [x] Add safeguard checks to application startup.
---

 ### [DONE] REV // F30 — v2.5.1-beta Migration Final Fixes

 **Goal:** Resolve config migration file lock issues and ensure database migration idempotency for v2.5.1-beta.

 **Plan:**

 #### Phase 1: Robust Config Migration [DONE]
 * [x] Add detailed logging and retry logic to `backend/config_migration.py`.
 * [x] Implement atomic replace fallback with helpful Docker hints.

 #### Phase 2: Database Idempotency & Backup [DONE]
 * [x] Make baseline migration `f6c8f45208da` idempotent (table checks).
 * [x] Make `b40631944987` idempotent (column checks).
 * [x] Implement automated DB backup in `docker-entrypoint.sh`.
 * [x] Improve error handling and recovery instructions.

 #### Phase 3: YAML Structure Validation [DONE]
 * [x] Add root-level dictionary validation to `migrate_config`.
 * [x] Fix `recursive_merge` type-mismatch handling.
 * [x] Add pre-write schema validation (version check).

---

### [DONE] REV // F31 — Config Migration (Bind Mounts) & CI Stability

**Goal:** Fix config migration failures on Docker bind mounts and stabilize CI tests.

**Plan:**

#### Phase 1: Bind Mount Support [DONE]
* [x] Detect bind mount vs atomic replacement scenarios.
* [x] Implement direct write fallback with backup/restore logic.
* [x] Add verification check after write.
* [x] **Verification**: Test migration with integration script.

#### Phase 2: CI & Database Stability [DONE]
* [x] Create `tests/conftest.py` for automatic DB initialization.
* [x] Add graceful error handling for missing DB/tables in API routers.
* [x] **Verification**: API tests pass in CI-like environment.

---

### [DONE] REV // F32 — Migration UX & Grid Validation Refinements

**Goal:** Improve migration transparency for Docker users and fix false grid sensor warnings.

**Plan:**

#### Phase 1: UX Improvements [DONE]
* [x] Update `config_migration.py` with friendly Docker bind mount message.
* [x] Document Docker bind mount limitations in `ARCHITECTURE.md`.
* [x] **Verification**: Logs show informative `ℹ️` instead of alarming `⚠️`.

#### Phase 2: Health Check Refinement [DONE]
* [x] Update `health.py` to respect `grid_meter_type` (`net` vs `dual`).
* [x] Implement explicit check for missing required sensors.
* [x] **Verification**: `dual` mode correctly warns for missing import/export sensors; `net` mode does not.

---

### [DONE] REV // F35 — Fix Slot Observation Upsert Data Wipe

**Goal:** Fix sleeping bug where BackfillEngine could wipe good recorded energy data with zeros.

**Root Cause:** `store_slot_observations` unconditionally overwrote `import_kwh`, `export_kwh`, `pv_kwh`, `load_kwh`, `water_kwh` on conflict. When backfill ran with broken sensor mappings (producing 0.0), it wiped existing good data.

**Plan:**

#### Phase 1: Fix Upsert Logic [DONE]
* [x] Identify root cause in `store.py` lines 141-145.
* [x] Add SQLAlchemy `case()` import.
* [x] Change energy field upserts to only overwrite when new value > 0.
* [x] **Verification**: Lint passed, import verified.

---

### [DONE] REV // ARC12 — SQLite WAL Mode (Concurrency Fix)

**Goal:** Eliminate `database is locked` errors by enabling WAL (Write-Ahead Logging) mode for SQLite, allowing concurrent reads/writes.

**Root Cause:** Two separate SQLAlchemy engines (`ExecutorHistory` sync, `LearningStore` async) compete for write access to `planner_learning.db`. SQLite's default journal mode only allows one writer at a time, causing lock contention.

**Plan:**

#### Phase 1: Add Timeouts (Quick Fix) [DONE]
* [x] Add `timeout: 30.0` to `ExecutorHistory` engine in `executor/history.py`.
* [x] Add `check_same_thread: False` to `ExecutorHistory` for thread safety.
* [x] **Verification**: Error frequency should decrease.

#### Phase 2: Enable WAL Mode [DONE]
* [x] Add WAL pragma execution after engine creation in `executor/history.py`.
* [x] Add WAL pragma execution after engine creation in `backend/learning/store.py`.
* [x] Create one-time migration script to convert existing databases to WAL.
* [x] **Verification**: `PRAGMA journal_mode` returns `wal`.

#### Phase 3: Documentation & Testing [DONE]
* [x] Document WAL mode in `ARCHITECTURE.md` section 9.3.
* [x] Verify linting passes for all modified files.
---

 ### [DONE] REV // DX2 — Silence Noisy HTTPX Logs

 **Goal:** Reduce log clutter by silencing verbose `httpx` and `httpcore` logs at the `INFO` level.

 **Plan:**

 #### Phase 1: Logging Configuration [DONE]
 * [x] Modify `backend/core/logging.py` to set `httpx`, `httpcore`, `uvicorn.access`, and `darkstar.api` loggers to `WARNING` level.
 * [x] **Verification**: Logs no longer show daily sensor polling or repetitive API access/loading messages.

---

### [PLANNED] REV // UI8 — Remove 24h/48h Toggle, Implement Smart Auto-Zoom

**Goal:** Fix chart action visibility issues by removing problematic 24h/48h toggle and implementing intelligent auto-zoom on single 48h chart.

**Context:**
The 24h/48h toggle is causing chart rendering issues where battery actions disappear in 48h mode but show in 24h mode. Console logs show excessive chart rebuilds (12+ times) causing actions to be overwritten. User can see discharge actions in 24h but missing charge actions, indicating data processing inconsistencies between modes.

**Plan:**

#### Phase 1: Remove Toggle UI [DONE]
* [x] Remove `showDayToggle` prop from ChartCard component interface
* [x] Remove toggle buttons from ChartCard render method
* [x] Remove `rangeState` useState and related state management
* [x] Update Dashboard to remove `showDayToggle={true}` prop
* [x] **STOP - Verification**: Chart shows no toggle buttons, always processes 48h data

#### Phase 2: Simplify Data Processing [DONE]
* [x] Always pass `range="48h"` to buildLiveData function
* [x] Remove all `range === 'day'` conditional logic from buildLiveData
* [x] Remove day-specific data processing paths that cause action visibility issues
* [x] Clean up useEffect dependencies to prevent excessive re-renders
* [x] **STOP - Verification**: Single data processing path, reduced console log spam

#### Phase 3: Implement Smart Auto-Zoom [DONE]
* [x] Add function to detect tomorrow's price availability: `hasTomorrowPrices = slots.some(slot => isTomorrow(slot.start_time) && slot.import_price_sek_kwh != null)`
* [x] Implement auto-zoom logic after chart data is applied: `if (!hasTomorrowPrices) chart.zoomScale('x', {min: 0, max: 95})`
* [x] Ensure zoom happens after chart update, not during data processing
* [x] Maintain manual zoom functionality for user control
* [x] **STOP - Verification**: Chart auto-zooms to ~24h view when only today's prices available, shows full 48h when tomorrow's prices exist

#### Phase 4: Debug Action Visibility [DONE]
* [x] Add debugging to identify what triggers excessive useEffect calls
* [x] Verify all battery actions (charge/discharge) are visible consistently
* [x] Test that actions remain visible during live metric updates
* [x] Ensure socket.io reconnections don't cause action loss
* [x] **STOP - Verification**: All future battery actions visible and stable, no disappearing after brief appearance

---

### [DONE] REV // F36 — Fix Future Actions Data Source (Schedule.json vs Database)

**Goal:** Fix missing future battery actions by ensuring they come from schedule.json only, not stale database data, with proper time-based splitting at "now" marker.

**Context:**
Root cause identified: `/api/schedule/today_with_history` loads future battery actions from database `slot_plans` table (stale data) instead of live `schedule.json`. This causes future actions to disappear because database has old planned values while schedule.json has current optimized actions. Actions appear briefly on refresh when `Api.schedule()` loads first, then disappear when `Api.scheduleTodayWithHistory()` overwrites with stale DB data.

**Plan:**

#### Phase 1: Fix Backend Data Source Logic [DONE]
* [x] Modify `/api/schedule/today_with_history` in `backend/api/routers/schedule.py`
* [x] Split data sources at current time ("now" marker):
  - **Past slots (< now)**: Use database history data (actual_charge_kw, actual_discharge_kw)
  - **Future slots (>= now)**: Use schedule.json data (battery_charge_kw, battery_discharge_kw)
* [x] Remove database `planned_map` lookup for future slots (lines 250-275)
* [x] Fix synthetic future slot creation from DB keys (prevent creating slots from stale DB records)
* [x] Keep price and forecast data sources unchanged (Nordpool cache + DB forecasts)
* [x] **Verification**: Future actions come from schedule.json, historical from database

#### Phase 2: Preserve Non-Action Data [DONE]
* [x] Ensure price data (Nordpool cache) continues working for both past and future
* [x] Ensure forecast data (pv_forecast_kwh, load_forecast_kwh) continues from database
* [x] Ensure SoC targets and projections work correctly across time split
* [x] Keep historical overlays (actual_pv_kwh, actual_load_kwh) from database
* [x] **Verification**: Only battery actions split by time, other data sources unchanged

#### Phase 3: Frontend Validation [DONE]
* [x] Test that future actions are immediately visible and stable
* [x] Verify historical actions show when available in database
* [x] Confirm "now" marker correctly separates data sources
* [x] Test that missing schedule.json shows as missing future actions (desired behavior)
* [x] **Verification**: Chart shows live future actions from schedule.json, historical from DB

#### Phase 4: Edge Case Handling [DONE]
* [x] Handle missing schedule.json gracefully (show empty future actions)
* [x] Handle timezone edge cases around "now" marker calculation
* [x] Ensure proper error handling when database history unavailable
* [x] Add logging to distinguish data source for debugging
* [x] **Verification**: Robust handling of missing data sources, clear debugging info
