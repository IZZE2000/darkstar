# Darkstar Energy Manager: Backlog

This document contains ideas, improvements, and tasks that are not yet scheduled for implementation.

---

## 🤖 AI Instructions (Read First)

1.  **Naming:** Use generic names (e.g., `Settings Cleanup`, `Chart Improvements`) until the item is promoted.

2.  **Categories:**
    - **Backlog** — Concrete tasks ready for implementation
    - **On Hold** — Paused work with existing code/design
    - **Future Ideas** — Brainstorming, needs design before implementation

3.  **Format:** Use the template below for new items.

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

### 🔴 High Priority (Ready to Plan)

### [PLANNED] Effekttariff (Power Tariff Guard)

**Goal:** Implement a dual-layer strategy (Planner + Executor) to minimize peak power usage ("Effekttariff").

**Notes:** Two paths identified during exploration. Start with KISS (V1) and evolve toward Advanced (V2).

#### Path A: The KISS "Ceiling & Fuse" (V1) [RECOMMENDED]
*   **Concept:** A simple time-windowed hard limit.
*   **Inputs:**
    *   `peak_power_limit` (kW)
    *   `peak_start_time` / `peak_stop_time` (e.g., 07:00-19:00)
    *   `current_month_peak_sensor` (Optional HA sensor to track the "Peak-to-Beat").
*   **Logic:** `Effective Limit = MAX(peak_power_limit, current_month_peak_sensor)`.
*   **Planner Role:** Treats the Effective Limit as a "Hard Wall" during the active window. No complex cost math, just a constraint.
*   **Executor Role:** Acts as a "Reactive Fuse." If real-time import crosses the limit during the window:
    1.  **Throttle EV** (if `has_ev` is true).
    2.  **Stop Water Heater** (if `has_water_heater` is true).
    3.  **Force Discharge** battery (if available).
*   **Sync:** Support reading/writing these values to HA entities (`input_number`, `input_datetime`) to keep UI in sync.

#### Path B: The "Advanced Tariff Profile" (V2)
*   **Concept:** Declarative YAML profiles for different Swedish providers (E.ON, Vattenfall, etc.).
*   **Planner Logic:** Uses MILP "Peak Variables" to perform economic negotiation.
    *   *Decision:* "Is the electricity cheap enough that paying the 60 SEK tariff peak fee is actually profitable?"
*   **Memory:** Tracks "Top 3 Peaks" or other complex monthly rules across the 36h planning horizon using a "Monthly State" input.
*   **KISS Benefit:** Users can share profiles for their specific region.

** See @/docs/designs/effekttariff-kiss.md and @/docs/designs/effekttariff-advanced.md for more details.

---

### [DRAFT] Inverter Clipping Support

**Goal:** Correctly model DC vs AC inverter limits in the Kepler solver to prevent over-optimistic planning on high-PV systems.
**Context:** User has a 15kWp array but a 10kW (AC) / 12kW (DC-Input) inverter. Current model assumes all PV is available at the AC bus.

**Plan:**

#### Phase 1: Configuration & Schema [DRAFT]
* [ ] Add `inverter.max_pv_input_kw` (DC limit) and `inverter.max_ac_output_kw` (AC limit) to `config.default.yaml`.
* [ ] Deprecate/Migration: Map old `system.inverter.max_power_kw` to `max_ac_output_kw`.
* [ ] **USER VERIFICATION:** Confirm schema covers all hardware limits (Access Power vs Input Power).

#### Phase 2: Solver Logic (DC Bus) [DRAFT]
* [ ] **Kepler Model:** Introduce `pv_to_ac[t]` and `discharge_to_ac[t]` variables.
* [ ] **Constraint:** `pv_actual[t] + discharge_dc[t] == charge_dc[t] + ac_produced[t]`.
* [ ] **Constraint:** `ac_produced[t] <= inverter_ac_limit`.
* [ ] **Constraint:** `pv_actual[t] <= inverter_pv_dc_limit`.
* [ ] Verify with test case (15kW PV, 10kW AC, 12kW DC battery charge).

#### Phase 3: Input Pipeline [DRAFT]
* [ ] **Inputs:** Update `inputs.py` to optionally clip forecasts early (for heuristic simplicity) or pass through raw data.
* [ ] **UI:** Show "Clipped Solar" in the dashboard forecast chart.

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

#### [Config] Inverter Max Power Config Orphan

**Goal:** Wire `system.inverter.max_power_kw` to the planner/executor or remove if superseded.

**Notes:** Config key is defined but never used in code. Related to "Inverter Clipping Support" backlog item. Either implement the feature or remove the config key to avoid confusion.

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
