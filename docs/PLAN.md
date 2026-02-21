# Darkstar Energy Manager: Active Plan

**Vision: From Calculator to Agent**
Darkstar is transitioning from a deterministic optimizer (v1) to an intelligent energy agent (v2). It does not just optimize based on static config; it observes context (Weather, Vacation, Prices), predicts outcomes (Aurora ML), and actively strategizes (Strategy Engine) to maximize efficiency and comfort.

---

| Prefix  | Area                 |
| ------- | -------------------- |
| **K**   | Kepler (MILP solver) |
| **E**   | Executor             |
| **A**   | Aurora (ML)          |
| **H**   | History/DB           |
| **O**   | Onboarding           |
| **UI**  | User Interface       |
| **DS**  | Design System        |
| **F**   | Fixes/Bugfixes       |
| **DX**  | Developer Experience |
| **ARC** | Architecture         |
| **IP**  | Inverter Profiles    |

Check this document or `docs/CHANGELOG_PLAN.md` for previous revisions.

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

### [DRAFT] REV // K25 — EV Discharge Protection via Actual Power Monitoring

**Goal:** Add real-time detection of actual EV power consumption to block battery discharge when EV is charging, regardless of whether the charging was triggered by Darkstar's schedule or external sources (manual HA trigger, Tesla app, etc.).

**Context:**
Currently, the executor only blocks battery discharge when the schedule indicates EV should be charging (`slot.ev_charging_kw > 0.1`). This means if a user manually starts EV charging through Home Assistant or another system, the battery can still discharge to the EV because Darkstar doesn't detect the actual power flow. This creates a safety gap where energy can leave the house battery to the car when it shouldn't.

**Current Implementation:**
- Planner level (`planner/solver/kepler.py:202-209`): Optimization ensures EV charging can only use grid + PV
- Executor level (`executor/engine.py:1137-1151`): Blocks discharge when schedule says EV should charge
- **Gap:** No detection of actual EV power draw from external sources

**Proposed Solution:**
Add a second layer of protection that monitors actual EV power consumption via the `LoadDisaggregator` (which already tracks all configured EV charger power sensors). When any EV is consuming power (> threshold), force battery discharge to 0 regardless of the schedule.

**Plan:**

#### Phase 1: Backend - Detect Actual EV Power [DRAFT]
* [ ] Add `get_total_ev_power()` method to `LoadDisaggregator` class to aggregate power from all registered EV chargers
* [ ] Update `executor/engine.py` to query actual EV power from disaggregator during decision making
* [ ] Modify discharge blocking logic to check: `if scheduled_ev_charge OR actual_ev_power > 0.1 kW: block_discharge()`
* [ ] Add logging: "EV detected consuming X kW - blocking battery discharge"

#### Phase 2: Testing [DRAFT]
* [ ] Create unit test: Manual EV trigger via HA sensor → discharge blocked
* [ ] Create unit test: Scheduled EV charging → discharge blocked (existing behavior)
* [ ] Create unit test: No EV charging → discharge allowed normally
* [ ] Run `uv run ruff check .` for linting
* [ ] Run `uv run python -m pytest tests/ -v -k ev` for EV-related tests

#### Phase 3: Documentation [DRAFT]
* [ ] Update executor architecture docs if they mention EV discharge blocking
* [ ] Add note about dual-layer protection (schedule + actual power detection)

---

### [DRAFT] REV // A25 — Fix Forecast Timestamp Alignment Bug

**Goal:** Fix the critical bug where load and PV forecasts show zeros and unexpected gaps due to timestamp misalignment between forecast generation and price slots.

**Context:**
A Fronius beta tester observes completely different load/PV forecasts between consecutive planning runs seconds apart. Load forecast shows huge gaps with zero values; PV forecast plummets unexpectedly. These should be identical between runs.

**Root Cause Analysis:**
The bug is in `ml/forward.py:94-98`. The code generates forecasts starting at the **next** 15-minute slot boundary (e.g., 09:15 if current time is 09:01), but price slots start at the **current** slot boundary (e.g., 09:00). When `inputs.py:build_db_forecast_for_slots()` looks up forecasts for price slots, the first slot (09:00) has no matching forecast → returns `pv=0.0, load=0.0`.

**Why it appears intermittent:**
- If planner runs at exactly 09:00:00, forecasts start at 09:00 → alignment OK
- If planner runs at 09:00:15, forecasts start at 09:15 → 09:00 slot has no forecast → zeros

**Plan:**

#### Phase 1: Fix Root Cause (Primary)
* [ ] Modify `ml/forward.py:94-98` to generate forecasts starting from the **current** 15-minute slot boundary instead of "next slot"
* [ ] Update comment to reflect the change: "Align to current slot boundary"
* [ ] Verify forecast timestamps now match price slot timestamps exactly

#### Phase 2: Add Defensive Fallback
* [ ] Modify `inputs.py:911` to implement fallback logic when exact timestamp match fails
* [ ] If `indexed.get(ts)` returns None, search for the closest forecast at or before the requested slot
* [ ] Only return 0.0 as absolute last resort (if no forecasts available at all)
* [ ] Add warning log when fallback is used: "No exact forecast match for {ts}, using fallback from {fallback_ts}"

#### Phase 3: Testing & Validation
* [ ] Run planner at various times within a 15-minute window and verify consistent forecasts
* [ ] Verify no zero values in load/PV forecasts when DB has valid data
* [ ] Run `uv run ruff check .` for linting
* [ ] Run `uv run python -m pytest tests/ -v -k forecast` for forecast-related tests

#### Phase 4: Documentation
* [ ] Add inline comments explaining timestamp alignment requirements
* [ ] Document the "belt and suspenders" approach (fix root cause + defensive fallback)

**Affected Files:**
- `ml/forward.py:94-98` - Forecast generation timestamp logic
- `inputs.py:909-914` - Forecast lookup with fallback needed

**Success Criteria:**
- Consecutive planner runs (seconds apart) produce identical load/PV forecasts
- No zero values in forecasts when the ML database contains valid predictions
- Graceful degradation with logged warnings if forecasts are ever stale/missing

---

### [DONE] REV // UI24 — Migrate SVG Charts to CSS Variables

**Goal:** Replace hardcoded hex colors in SVG charts and Chart.js configurations with dynamic CSS custom properties for proper Light/Dark mode adaptation.

**Context:**
Many SVG charts (Power Flow diagram, probabilistic forecasts, etc.) use hardcoded hex colors that don't adapt to theme changes. This causes poor visibility in certain modes - dark text on dark backgrounds or light text on light backgrounds. The `index.css` file already defines a comprehensive theme system with CSS variables like `--color-surface`, `--color-text`, `--color-muted`, and `--color-line` that automatically switch between light and dark modes.

**Files to Modify:**

| File | Hex Colors | Strategy |
|------|------------|----------|
| `CircuitNode.tsx` | 8 locations | SVG attribute replacements |
| `CircuitPath.tsx` | 1 location | SVG stroke color |
| `PowerFlowCard.tsx` | 2 locations | Tooltip inline styles |
| `ProbabilisticChart.tsx` | 10 locations | Chart.js options objects |
| `Aurora.tsx` | 12 locations | Chart.js scales configuration |
| `ContextRadar.tsx` | 4 locations | Chart.js tooltip config |
| `DecompositionChart.tsx` | 2 locations | Preserve OLED/Swiss logic |

**Color Mapping:**

| Current Hex | CSS Variable | Usage |
|-------------|--------------|-------|
| `#0f172a` | `rgb(var(--color-surface))` | Node backgrounds |
| `#334155` | `rgb(var(--color-line))` | Grid lines, borders |
| `#64748b` | `rgb(var(--color-muted))` | Secondary text, brackets |
| `#94a3b8` | `rgb(var(--color-muted))` | Labels, small text |
| `#e2e8f0` | `rgb(var(--color-text))` | Primary values |
| `#f1f5f9` | `rgb(var(--color-text))` | Active text state |
| `#1e293b` | `rgb(var(--color-surface))` | Trace backgrounds |
| `#cbd5e1` | `rgb(var(--color-muted))` | Tooltip body |
| `#f8fafc` | `rgb(var(--color-text))` | Tooltip titles |

**Plan:**

#### Phase 1: SVG Components [DONE]
* [x] Update `CircuitNode.tsx` - Replace 8 hardcoded hex colors
  - `fill="#0f172a"` → `fill="rgb(var(--color-surface))"`
  - `stroke={isActive ? color : '#334155'}` → `stroke={isActive ? color : 'rgb(var(--color-line))'}`
  - Style object colors for text and icon elements
* [x] Update `CircuitPath.tsx` - Replace background trace color
  - `stroke="#1e293b"` → `stroke="rgb(var(--color-surface))"`
* [x] Update `PowerFlowCard.tsx` - Replace tooltip styles
  - `#e2e8f0` → `rgb(var(--color-text))`
  - `#64748b` → `rgb(var(--color-muted))`

#### Phase 2: Chart.js Configurations [DONE]
* [x] Update `ProbabilisticChart.tsx`
  - Grid colors: `#334155` → `rgb(var(--color-line))`
  - Text colors: `#94a3b8`, `#e2e8f0`, `#cbd5e1` → theme variables
  - Tooltip styling: `#1e293b`, `#334155` → surface/line
* [x] Update `Aurora.tsx`
  - Chart scales: grid and tick colors
  - Legend labels
* [x] Update `ContextRadar.tsx`
  - Tooltip configuration
* [x] Update `DecompositionChart.tsx`
  - Maintain conditional OLED/Swiss logic
  - Replace default fallback colors only

#### Phase 3: Testing & Validation [DONE]
* [x] Verify Power Flow diagram in both Light and Dark modes
* [x] Verify all charts adapt correctly to theme toggle
* [x] Run `pnpm lint` in frontend/ directory - **PASSED**
* [x] Run `pnpm format` to ensure consistent formatting - **FORMATTED**
* [x] Check for any remaining hardcoded colors with grep - **NONE FOUND**

**Total Changes:** ~35 hex color references across 7 files → 4 CSS variables

---

### [DRAFT] REV // F72 — Fix Profile Suggestions API Crash

**Goal:** Fix the `FileNotFoundError` in the backend `get_profile_suggestions` endpoint that causes the `ProfileSetupHelper` UI to silently fail for new configs.

**Context:**
The frontend `ProfileSetupHelper.tsx` relies on `/api/profiles/{name}/suggestions` to present the user with standard configuration values for their selected inverter profile (e.g., Deye, Fronius) when onboarding or switching profiles.
Currently, this endpoint crashes with a 500 error on fresh installations because it calls `load_yaml("config.yaml")` using a relative path to calculate missing entities. If the backend is running from a different working directory, this file isn't found. Furthermore, the frontend component hides itself if `diffItems.length === 0`, interpreting an API crash (or a completely blank config failing to match keys) as "No differences found". This prevents the user from receiving necessary auto-configuration suggestions.

**Plan:**

#### Phase 1: Backend Fix [DRAFT]
* [ ] Modify `backend/api/routers/executor.py` -> `get_profile_suggestions` to resolve `config.yaml` robustly.
* [ ] Handle cases where `config.yaml` is completely empty or missing gracefully, ensuring the endpoint returns the full standard profile template as "missing" so the UI can populate.

#### Phase 2: Frontend Resilience [DRAFT]
* [ ] Modify `frontend/src/pages/settings/components/ProfileSetupHelper.tsx`
* [ ] Ensure errors from the backend fetch are displayed to the user rather than hiding the component.
* [ ] Fix the local diffing logic so that an entirely blank `currentForm` correctly registers all suggested keys as `is_different` or `is_missing` so the UI appears immediately.

---

### [DRAFT] REV // UI25 — Mandatory Startup Overlay Wizard

**Goal:** Create a mandatory, high-level "Setup Mode" overlay wizard that triggers on fresh installations (`config.system.inverter_profile == null`) to configure the minimal required settings before allowing dashboard interaction.

**Context:**
Currently, users with no data fall back to a perfectly flat dummy load profile in `inputs.py`, which ruins the Kepler solver's ability to plan for daily peaks. Furthermore, users are presented with a massive settings page and don't know where to begin.
We need a targeted Setup Wizard that triggers automatically. It should gather the 3 critical pieces of information needed for the system to function: The Inverter Profile, the Battery/PV capacities, and a Baseline Consumption (either fetching 7 days of real HA data or generating a scaled Synthetic Profile based on user estimation).

**Plan:**

#### Phase 1: Trigger & Infrastructure [DRAFT]
* [ ] Change the default `config.default.yaml` entry for `system.inverter_profile` to `null` (instead of `"generic"`) to serve as the trigger state.
* [ ] Create a robust check in `App.tsx` (or a layout wrapper) that forces the user into a full-screen `StartupWizard` modal if the profile is `null`.
* [ ] Implement an API call to save the minimal config upon wizard completion and trigger a backend `ExecutorEngine` reload to apply the new profile and hardware specs.

#### Phase 2: The Wizard Steps [DRAFT]
* [ ] **Step 1 (Equipment):** Present big buttons for Deye, Fronius, Generic, etc. Re-use the fixed `ProfileSetupHelper` logic from REV F72 to inject the standard entities.
* [ ] **Step 2 (Specs):** Ask for Battery Capacity (kWh) and Solar Array (kWp). Save to `config.system`.
* [ ] **Step 3 (Baseline):** Ask for the HA `total_load_consumption` sensor. If selected, instantly trigger the async 7-day data fetch. If not provided, ask for "Estimated Daily kWh" and implement a backend routine in `inputs.py` to generate a "Synthetic Heat Pump Profile" scaled to that kWh instead of the flat 0.5 kWh line.

#### Phase 3: Testing & Polish [DRAFT]
* [ ] Verify the wizard cannot be easily bypassed unless completed.
* [ ] Add a "Relaunch Setup Wizard" button in Settings -> System.
* [ ] Test the Synthetic Profile generation mathematically scales correctly.

---
