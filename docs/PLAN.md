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

### [DONE] REV // DX6 — Dependency Audit

**Goal:** Ensure project dependencies are up to date, secure, and compatible.

**Plan:**

#### Phase 1: Audit [DONE]
* [x] **Frontend:** Run `pnpm outdated` in `frontend/` to identify stale packages.
* [x] **Backend:** Run `uv pip list --outdated` to check Python dependencies.
* [x] **Security:** Check `npm audit` and `pip-audit` (if available) for vulnerabilities.

#### Phase 2: Update [DONE]
* [x] **Apply Updates:** Update `package.json` (minor/patch first) and `requirements.txt`.
* [x] **Verification:** Run `pnpm test` and `uv run pytest` to ensure no breaking changes.
* [x] **Lockfiles:** Commit updated `pnpm-lock.yaml` and pinning in `requirements.txt`.

---

### [DONE] REV // F21 — Backend Startup & Log Cleanup

**Goal:** Fix `uv` startup warnings and silence excessive "DIAG" log spam from Socket.IO and backend services.

**Plan:**

#### Phase 1: Configuration & Logging [DONE]
* [x] **pyproject.toml:** Add `[project]` metadata with `requires-python = ">=3.12"` to satisfy `uv` requirements.
* [x] **Websockets:** Disable `logger` and `engineio_logger` in `backend/core/websockets.py` to stop "emitting event" spam.
* [x] **HA Socket:** Lower `DIAG` logs in `backend/ha_socket.py` from `INFO` to `DEBUG`.

---

### [DONE] REV // F23 — Accurate Startup Logging & Health Robustness (Issue #1)

**Goal:** Resolve misleading "Has Water Heater: true" logs and eliminate "angry red messages" for optional features.

**Plan:**

#### Phase 1: Logging & Health Refactor [DONE]
* [x] **run.sh:** Move status logging from Bash string-matching to Python object-reflection (SSOT: `config.yaml`).
* [x] **health.py:** Downgrade optional sensors (Alarmo, Vacation) from Critical to Warning.
* [x] **health.py:** Respect hardware toggles (`has_solar`, etc.) in sensor validation.

#### Phase 2: Documentation [DONE]
* [x] **PLAN.md:** Document fix for posterity.

---

### [DONE] REV // F22 — Remove aiosqlite & Refactor Tests

**Goal:** Remove `aiosqlite` from production dependencies and refactor tests to align with SQLAlchemy async architecture.

**Plan:**

#### Phase 1: Refactor [DONE]
* [x] **Audit:** Confirm `backend/learning/store.py` uses SQLAlchemy (sync).
* [x] **Refactor:** Rewrite `tests/test_schedule_history_overlay.py` to use `SQLAlchemy` `create_async_engine` + `text()` wrapping instead of raw `aiosqlite`.
* [x] **Cleanup:** Downgrade `aiosqlite` to a test-only dependency in `requirements.txt`.

#### Phase 2: Verification [DONE]
* [x] **Test:** Run `pytest tests/test_schedule_history_overlay.py` (Passed).
* [x] **Regression:** Run full suite (Passed).

---

### [COMPLETED] REV // ARC10 — True Async Database Upgrade (API Layer)

**Goal:** Complete the transition to AsyncIO Database Architecture for the **API layer**, resolving the critical "Split-Brain" state between Sync Store and Async API routes.

**Context:**
Investigation revealed that `LearningStore` is currently **Synchronous** (Blocking), while API routes use raw `aiosqlite` hacks. This contradicts `ARCHITECTURE.md` and causes performance risks.

**Scope Limitation:**
This REV focuses on **API routes ONLY**. The background Recorder (`backend/learning/engine.py`) runs in a thread and will remain synchronous. It will be addressed in **REV ARC11** to avoid mixing threading and async complexity in a single revision.

**Plan:**

#### Phase 1: Core Async Upgrade [COMPLETED]
* [x] **Add Dependency:** Add `aiosqlite` to `requirements.txt` (required for async SQLAlchemy with SQLite).
* [x] **Refactor Engine:** Update `LearningStore.__init__` to use `sqlalchemy.ext.asyncio.create_async_engine` and `async_sessionmaker`.
* [x] **Convert Methods:** Convert all public methods in `LearningStore` to `async def` with `async with self.AsyncSession()` context manager pattern.
* [x] **Engine Disposal:** Add `async def close()` method to dispose engine, call in FastAPI lifespan shutdown.

#### Phase 2: API Route Migration [COMPLETED]
* [x] **Dependency Injection:** Update `backend/main.py` to initialize `LearningStore` in lifespan and add `get_learning_store` dependency.
* [x] **Refactor Schedule Router:** Rewrite `backend/api/routers/schedule.py` (`schedule_today_with_history`) to use `await store.get_history_range_async(...)`.
* [x] **Refactor Services Router:** Rewrite `backend/api/routers/services.py` (`get_energy_range`) to use `await store.AsyncSession`.

#### Phase 3: Cleanup & Verification [COMPLETED]
* [x] **Verify Sync:** Ensure `Recorder` (sync) still works via legacy methods in `LearningStore` (Dual-mode).
* [x] **Verify Async:** Run tests `test_schedule_history_overlay.py`.
* [x] **Lint:** Run `ruff` to ensure clean code.

#### Phase 4: Documentation & Future Work [COMPLETED]
* [x] **Document Scope:** Add comment in `backend/learning/engine.py` explaining Recorder remains sync, referencing REV ARC11.
* [x] **Plan ARC11:** Create ARC11 placeholder in `PLAN.md` for background service async migration.
* [x] **Update ARCHITECTURE.md:** Document the hybrid approach (async API, sync background services) and rationale.

---

### [BACKLOG] REV // ARC11 — Async Background Services (Full Migration)

**Goal:** Complete the migration to full AsyncIO by refactoring the Recorder and Planner Service to use async database methods, eliminating the "Dual-Mode" hybrid state.

**Plan:**
*   Refactor `Recorder` (`backend/recorder.py`) to use `async/await`.
*   Refactor `LearningEngine` (`backend/learning/engine.py`) to use `AsyncSession`.
*   Remove synchronous `Session` and `create_engine` from `LearningStore`.
*   Update `docs/ARCHITECTURE.md` to reflect unified AsyncIO architecture.
