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

**Architecture:** WebSocket-based real-time status updates for both features.

**Task 1: Backend - Planner Progress Events**
* [ ] Modify `backend/services/planner_service.py`:
  * Add `_current_phase: str | None` and `_phase_start_time: datetime | None` instance variables
  * Add `async def _emit_progress(phase: str, elapsed_ms: float)` helper method
  * Add `def get_status() -> dict` method for HTTP fallback
  * Instrument `run_once()` to emit WebSocket events at 5+ phases:
    1. `fetching_prices` - Before price data fetch
    2. `fetching_forecasts` - Before forecast fetch
    3. `applying_learning` - Before learning overlays
    4. `running_solver` - Before Kepler solver
    5. `applying_schedule` - After solver, before save
    6. `complete` - After successful save
* [ ] Add `GET /api/planner/status` endpoint in `backend/api/routers/planner.py`
* [ ] Test: Run planner and verify WebSocket `planner_progress` events are emitted with `{phase: str, elapsed_ms: float, remaining_seconds: int}`

**Task 2: Frontend - Planning Button WebSocket Integration**
* [ ] Modify `frontend/src/components/QuickActions.tsx`:
  * Import `getSocket()` from `lib/socket.ts`
  * Add `useEffect` to connect WebSocket and listen for `planner_progress` events
  * Update `plannerPhase` state to `{phase: string, elapsed_ms: number} | null`
  * Update button text to show phase name + elapsed time (e.g., "Running solver... (15s)")
  * Add automatic retry logic if WebSocket disconnects (reconnect every 2s)
* [ ] Test: Click "Run Planner" and verify real-time status updates with elapsed time

**Task 3: Backend - Water Boost WebSocket Events**
* [ ] Modify `backend/executor/engine.py`:
  * Add `_last_boost_state: dict | None` instance variable to track changes
  * In `_tick()`, check if boost status changed and emit `water_boost_updated` event
  * Emit periodic status every 30s even if unchanged (for new WebSocket clients)
  * Event payload: `{active: bool, expires_at: ISO string, remaining_seconds: int}`
* [ ] Modify `backend/api/routers/services.py`:
  * After `set_water_boost()` success, emit `water_boost_updated` WebSocket event
* [ ] Test: Activate boost and verify WebSocket event is emitted with correct payload

**Task 4: Frontend - Water Boost Timer WebSocket Integration**
* [ ] Modify `frontend/src/components/CommandDomains.tsx`:
  * Import `getSocket()` from `lib/socket.ts`
  * Add `useEffect` to connect WebSocket and listen for `water_boost_updated` events
  * Update `boostExpiresAt` and `boostSecondsRemaining` from WebSocket events
  * Keep local countdown `useEffect` for smooth 1s UI updates
  * Remove 30s polling interval (replaced by WebSocket push)
  * Add defensive null checks in countdown logic
  * Add automatic retry logic if WebSocket disconnects
* [ ] Test: Activate boost, verify timer counts down smoothly, survives re-renders, and syncs with backend

**USER VERIFICATION AND COMMIT:** Stop and let the user verify all 4 tasks.

#### Phase 2: Chart Zoom & Reset [PLANNED]
* [ ] **Zoom Logic:** Update `ChartCard.tsx` to preserve zoom state during background data refreshes.
* [ ] **Reset Button:** Add a "Reset Zoom" button to the ChartCard header.
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify.

#### Phase 3: Configuration Documentation [PLANNED]
* [ ] **Config Comments:** Add detailed comments to the `learning:` section in `config.default.yaml` explaining auto-tuning and Reflex thresholds.
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify.
