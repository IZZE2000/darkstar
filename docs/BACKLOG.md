# Darkstar Energy Manager: Backlog

This document contains ideas, improvements, and tasks that are not yet scheduled for implementation. Items here are moved to [PLAN.md](PLAN.md) when they become active priorities.

---

## 🤖 AI Instructions (Read First)

1.  **Structure:** This file is organized by category. Items do **not** have strict ordering.

2.  **Naming:** Use generic names (e.g., `Settings Cleanup`, `Chart Improvements`) until the item is promoted.

3.  **Promotion Flow:**
    - When starting work on a backlog item, assign it a proper **Rev ID** following the [naming conventions in PLAN.md](PLAN.md#revision-naming-conventions).
    - Move the item to `PLAN.md` with status `[PLANNED]` or `[IN PROGRESS]`.
    - Delete the item from this file.

4.  **Categories:**
    - **Backlog** — Concrete tasks ready for implementation
    - **On Hold** — Paused work with existing code/design
    - **Future Ideas** — Brainstorming, needs design before implementation

5.  **Format:** Use the template below for new items.

### Backlog Item Template

```
### [Category] Item Title

**Goal:** What we want to achieve.

**Notes:** Context, constraints, or design considerations.
```

---

## 📋 Backlog

---
## 📥 Inbox (User Added / Unsorted)

<!-- Add new bugs/requests here. AI will wipe this section when processing. -->

- INVERTER PROFILES! Already planned in docs/INVERTER_PROFILES_VISION.md
- [Recurring] Check dependencies (`pnpm outdated` / `pip list --outdated`) every month.
- Info for the inverter profiles expansion (add a task to create multiple profiles, do we need a unique default config for different brands?):
"
Så som det fungerar i predbat, att ställa om lägen är något i denna stilen, i denna tråden står där en hel del nyttig information som man skulle kunna ta med sig till denna plugin.
# Service for start/stop
charge_start_service:
service: select.select_option
entity_id: select.solinteg_inverter_working_mode
option: "UPS"
charge_stop_service:
service: select.select_option
entity_id: select.solinteg_inverter_working_mode
option: "General"
discharge_start_service:
service: select.select_option
entity_id: select.solinteg_inverter_working_mode
option: "Economic"
discharge_stop_service:
service: select.select_option
entity_id: select.solinteg_inverter_working_mode
option: "General"
https://github.com/springfall2008/batpred/discussions/2529
"
- Can we improve the config soft merge so any new added keys are added to the same place as they are in the default config file?
---

## 🔴 High Priority

### [AURORA] Support multiple MPPT strings / Panel arrays

**Goal:** Some users have multiple MPPT strings and panel arrays, we need to support this in the Aurora forecast.

---

### [Planner] Smart EV Integration

**Goal:** Prioritize home battery vs EV charging based on departure time and user preferences.

**Inputs Needed:**
- EV departure time (user input or calendar integration)
- EV target SoC
- EV charger entity (Home Assistant switch/sensor)
- EV battery capacity

**New Requirements (Beta Feedback):**
1. **Battery Guard (Source Isolation):**
   - prevent the House Battery from discharging *into* the EV.
   - Logic: `If EV_Charging == True, Then Battery_Discharge_Allowed = False` (unless PV > Load).
2. **Event-Driven Re-planning:**
   - Detect `sensor.ev_status` = "Connected" and trigger immediate re-plan.
   - Do not wait for 15-min cron.
3. **Proactive PV dump**
   -

**Implementation:**
- Add EV as second battery in Kepler MILP
- Constraint: EV must reach target SoC by departure time
- Policy: Prefer charging EV during cheap windows, home battery if surplus
- UI: EV configuration tab, departure time scheduler

**Complexity:** High (new subsystem, requires MILP solver changes)

**ROI:** High for EV owners

**Effort:** 2-3 weeks (design + implement + test)

**Notes:** Big feature. Requires careful UX design.

**Source:** Existing backlog item + expanded by Beta Feedback

---

### [Planner] Proactive PV Dump (Water Heating or EV!)

**Goal:** Schedule water heating to `temp_max` proactively when PV surplus is forecasted.

**Current State:** PV dump is only handled reactively via `excess_pv_heating` override in executor.

**Proposed Change:** Kepler solver should anticipate forecasted PV surplus at SoC=100% and pre-schedule water heating.

**Source:** Existing backlog item

---

## 🟡 Medium Priority

### [UI] Advisor Overhaul

**Goal:** Redesign and improve the Advisor feature to provide more actionable and reliable energy insights.

**Notes:** Current version is disabled/hidden as it needs a complete overhaul. Should integrate better with Kepler schedules and Aurora forecasts.

---

### [Refactor] Move inputs.py to Proper Module

**Goal:** Move `inputs.py` from project root to a proper module location (e.g., `planner/inputs.py` or `core/inputs.py`) for cleaner project structure.

**Current State:**
- `inputs.py` is a 42KB file in project root
- 29 files import from it across `backend/`, `bin/`, `tests/`, `ml/`
- Contains config loading, HA sensor fetching, Nordpool API, and data utilities

**Impact:**
- All 29 importing files need path updates
- Relative imports in tests and scripts need adjustment
- Python path considerations for different entry points

**Implementation:**
1. Create `core/` module with `__init__.py`
2. Move `inputs.py` → `core/inputs.py`
3. Update all imports: `from inputs import` → `from core.inputs import`
4. Update any relative path references
5. Verify all entry points work (`uvicorn`, `bin/run_planner.py`, tests)

**Effort:** 3-4 hours (careful refactor + testing all entry points)

---

### [Testing] Expand CI/CD Coverage (REVIEW-2026-01-04)

**Goal:** Expand CI/CD automation to include full unit tests, security audits, and built verification.

**Current State:**
- Basic CI exists (Linting + API tests)
- Missing: Full backend unit tests (pytest --cov)
- Missing: Frontend tests
- Missing: Security/Vulnerability scanning

**Proposed GitHub Actions Workflows:**

1. **`.github/workflows/test.yml`** (Run on every push/PR)
   ```yaml
   - Frontend: pnpm lint, pnpm test
   - Backend: ruff check ., pytest --cov
   - Report coverage to Codecov/Coveralls
   ```

2. **`.github/workflows/security.yml`** (Weekly + on PR)
   ```yaml
   - pip-audit (Python vulnerabilities)
   - pnpm audit (npm vulnerabilities)
   - ruff check --select=S (security lints)
   ```

3. **`.github/workflows/build.yml`** (On PR)
   ```yaml
   - Build Docker image
   - Verify startup (docker run + health check)
   ```

**Benefits:**
- Catch bugs before merge
- Enforce code quality standards
- Security vulnerability alerts

**Effort:** 2-3 hours (create workflows + test)

---

### [Backend] Split services.py Router (REVIEW-2026-01-04)

**Goal:** Improve maintainability by splitting the large `services.py` router (740 LOC) into focused modules.

**Current State:** `backend/api/routers/services.py` contains two distinct responsibilities:
1. Home Assistant integration endpoints (`/api/ha/*`)
2. Energy data endpoints (`/api/energy/*`, `/api/water/*`)

**Proposed Split:**

1. **`backend/api/routers/ha.py`** - Home Assistant Integration
   - `/api/ha/entity/{entity_id}`
   - `/api/ha/average`
   - `/api/ha/entities`
   - `/api/ha/services`
   - `/api/ha/connection/test`
   - `/api/ha/socket/status`

2. **`backend/api/routers/energy.py`** - Energy Data
   - `/api/energy/today`
   - `/api/energy/range`
   - `/api/water/today`
   - `/api/water/boost` (GET, POST, DELETE)
   - `/api/performance`

3. **Extract Shared Utilities:**
   - `_fetch_ha_history_avg()` → `backend/utils/ha.py`
   - Config loading helpers → reuse from `inputs.py`

**Benefits:**
- Easier to navigate
- Clearer separation of concerns
- Reduced merge conflicts

**Effort:** 2 hours (refactor + update imports + test)

---

### [ML] Add Model Versioning (REVIEW-2026-01-04)

**Goal:** Track which ML model version made which forecast for debugging and A/B testing.

**Current State:**
- LightGBM models stored as pickle files in `ml/models/`
- No version metadata
- No tracking of which model generated which forecast

**Implementation:**

1. **Model Metadata File:**
   ```python
   # ml/models/load_forecast_v3.metadata.json
   {
     "model_name": "load_forecast",
     "version": "3",
     "trained_at": "2026-01-04T12:00:00Z",
     "training_data_range": "2025-01-01 to 2026-01-01",
     "features": ["hour", "day_of_week", "temperature", ...],
     "metrics": {
       "mae": 0.45,
       "rmse": 0.67,
       "r2": 0.92
     },
     "git_commit": "abc123def",
     "config_hash": "md5hash"
   }
   ```

2. **Log Model Version:**
   - Add `model_version` column to `slot_forecasts` table
   - Log version when storing forecasts in `planner/observability/recorder.py`

3. **API Endpoint:**
   - `GET /api/aurora/models` - List available models with metadata
   - `GET /api/aurora/models/{name}/history` - Compare model versions over time

**Benefits:**
- Debug forecast accuracy regressions
- A/B test new models
- Rollback to previous model if needed

**Effort:** 3-4 hours (implement versioning + update recorder + add API)

---

---

### [Planner] Multiple Heating Sources/Deferrable Loads

**Goal:** Support control for multiple distinct heating sources (e.g., HVAC + Water Heater + Floor Heating) independently. A simple switch per each source to enable/disable it, and then the planner will decide when to turn them on/off based on the optimization problem. We need parameter for the kW consumption of each source and time/kWh goal.

**Notes:** Currently limited to a single water heater channel.

---

### [Testing] Add E2E Tests (IMPLEMENT PRE-STABLE RELEASE)

**Goal:** Add end-to-end tests to catch UI regressions and integration bugs.

**Current State:**
- Backend has 187 unit/integration tests
- Frontend has vitest configured but minimal usage
- No E2E tests for user flows

**Implementation:**

1. **Choose Framework:** Playwright (recommended) or Cypress
2. **Critical User Flows to Test:**
   - Dashboard loads and displays schedule
   - Executor pause/resume works
   - Settings save and validation
   - Water boost activation
   - Manual planner run

3. **Setup:**
   ```bash
   cd frontend
   pnpm add -D @playwright/test
   npx playwright install
   ```

4. **Example Test:**
   ```typescript
   test('dashboard displays schedule', async ({ page }) => {
     await page.goto('http://localhost:5173');
     await expect(page.locator('h1')).toContainText('Dashboard');
     await expect(page.locator('.chart-card')).toBeVisible();
   });
   ```

**Benefits:**
- Catch UI regressions
- Confidence in refactoring
- Documentation of expected behavior

**Effort:** 8 hours (setup + write initial tests)

---
