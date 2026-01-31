# Darkstar Energy Manager: Backlog

This document contains ideas, improvements, and tasks that are not yet scheduled for implementation. Items here are moved to [PLAN.md](PLAN.md) when they become active priorities.

---

- [Darkstar Energy Manager: Backlog](#darkstar-energy-manager-backlog)
  - [🤖 AI Instructions (Read First)](#-ai-instructions-read-first)
    - [Backlog Item Template](#backlog-item-template)
  - [📋 Backlog](#-backlog)
    - [📥 Inbox (User Added / Unsorted)](#-inbox-user-added--unsorted)
    - [🔴 High Priority (Ready to Plan)](#-high-priority-ready-to-plan)
      - [\[AURORA\] Support multiple MPPT strings / Panel arrays](#aurora-support-multiple-mppt-strings--panel-arrays)
      - [\[Planner\] Smart EV Integration](#planner-smart-ev-integration)
      - [\[Planner\] Proactive PV Dump (Water Heating or EV!)](#planner-proactive-pv-dump-water-heating-or-ev)
    - [🟡 Medium Priority (Needs Design)](#-medium-priority-needs-design)
      - [\[Planner\] Multiple Heating Sources/Deferrable Loads](#planner-multiple-heating-sourcesdeferrable-loads)
      - [\[Testing\] Add E2E Tests (IMPLEMENT PRE-STABLE RELEASE)](#testing-add-e2e-tests-implement-pre-stable-release)
    - [🔧 Technical Debt (Low User Impact)](#-technical-debt-low-user-impact)
      - [\[Refactor\] Move inputs.py to Proper Module](#refactor-move-inputspy-to-proper-module)
      - [\[Testing\] Expand CI/CD Coverage (REVIEW-2026-01-04)](#testing-expand-cicd-coverage-review-2026-01-04)
      - [\[Backend\] Split services.py Router (REVIEW-2026-01-04)](#backend-split-servicespy-router-review-2026-01-04)
    - [💡 Future Ideas (Brainstorming)](#-future-ideas-brainstorming)
      - [\[UI\] Advisor Overhaul](#ui-advisor-overhaul)


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

### 📥 Inbox (User Added / Unsorted)

<!-- Add new bugs/requests here. AI will wipe this section when processing. -->

---

### 🔴 High Priority (Ready to Plan)

Items with clear requirements that are ready for implementation planning.

#### [AURORA] Support multiple MPPT strings / Panel arrays

**Goal:** Some users have multiple MPPT strings and panel arrays, we need to support this in the Aurora forecast. Need to migrate config to use lists instead of singletons.

---

#### [Planner] Smart EV Integration

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

#### [Planner] Proactive PV Dump (Water Heating or EV!)

**Goal:** Schedule water heating to `temp_max` proactively when PV surplus is forecasted.

**Current State:** PV dump is only handled reactively via `excess_pv_heating` override in executor.

**Proposed Change:** Kepler solver should anticipate forecasted PV surplus at SoC=100% and pre-schedule water heating.

**Source:** Existing backlog item

---

### 🟡 Medium Priority (Needs Design)

Items that require design work or have unclear requirements before implementation.

#### [Planner] Multiple Heating Sources/Deferrable Loads

**Goal:** Support control for multiple distinct heating sources (e.g., HVAC + Water Heater + Floor Heating) independently. A simple switch per each source to enable/disable it, and then the planner will decide when to turn them on/off based on the optimization problem. We need parameter for the kW consumption of each source and time/kWh goal.

**Notes:** Currently limited to a single water heater channel.

---

#### [Testing] Add E2E Tests (IMPLEMENT PRE-STABLE RELEASE)

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

### 🔧 Technical Debt (Low User Impact)

Code quality improvements that don't directly affect user experience.

#### [Refactor] Move inputs.py to Proper Module

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

#### [Testing] Expand CI/CD Coverage (REVIEW-2026-01-04)

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

#### [Backend] Split services.py Router (REVIEW-2026-01-04)

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

### 💡 Future Ideas (Brainstorming)

Ideas that need requirements gathering and design work before implementation.

#### [UI] Advisor Overhaul

**Goal:** Redesign and improve the Advisor feature to provide more actionable and reliable energy insights.

**Notes:** Current version is disabled/hidden as it needs a complete overhaul. Should integrate better with Kepler schedules and Aurora forecasts.

---
