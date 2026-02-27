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

### [DONE] REV // F75 — Fix Fronius Export Profile: Include House Load in grid_discharge_power

**Goal:** Fix the Fronius export mode to correctly calculate `grid_discharge_power` by including the house load, preventing export capping issues. This is a **Fronius-only fix** - Deye, Sungrow, and Generic profiles do NOT have this issue and must remain unaffected.

**Context:**
Beta testers (Kristofer, Cmon89) discovered that Fronius GEN24's `grid_discharge_power` entity must be set to **house load + desired export power**, not just the export power. The current profile sets only `{{discharge_value}}` (which equals export power), causing the battery to deliver insufficient power to the grid.

Additionally, the profile incorrectly sets `export_power_limit_enable` and `export_power_limit` during export mode - these entities limit PV surplus feed-in, not battery discharge, and were capping exports unexpectedly.

**Key Finding from Testing:**
- House draws 500W, want to export 1000W → must set `grid_discharge_power = 1500W`
- Current code: set 2kW but battery only delivered 527W because `export_limit` was at 520W
- Setting `export_limit` to 10kW allowed full 2kW export

**Implementation Approach:**
Use Option 1: Pre-calculate the total discharge value in the Controller to avoid template expression security risks and complexity.

**Plan:**

#### Phase 1: Backend Changes [DONE]
* [x] Add `export_with_load_w` field to `ControllerDecision` dataclass in `executor/controller.py` (default=0.0)
* [x] In `Controller._follow_plan()` method, calculate and populate:
  - `export_with_load_w = export_power_w + (slot.load_kw * 1000)`
  - Round to nearest `round_step_w` (100W default for Fronius)
* [x] Add `export_with_load_w` to `VALID_TEMPLATES` frozenset in `executor/profiles.py`
* [x] Ensure calculation only happens when `slot.export_kw > 0`, otherwise `export_with_load_w = 0`

#### Phase 2: Profile Update [DONE]
* [x] Update `profiles/fronius.yaml` export mode:
  - Change `grid_discharge_power` from `{{discharge_value}}` to `{{export_with_load_w}}`
  - Remove `export_power_limit_enable` and `export_power_limit` actions entirely

#### Phase 3: Safety & Testing [DONE]
* [x] Verify Deye, Sungrow, Generic profiles still use `{{discharge_value}}` (unchanged)
* [x] Update `VALID_TEMPLATES` in `tests/executor/test_profiles_v2.py` to include `export_with_load_w`
* [x] Add unit test: Controller calculates `export_with_load_w` correctly for export slots
* [x] Add unit test: `export_with_load_w = 0` for non-export slots
* [x] Run `uv run ruff check .` for linting
* [x] Run `uv run python -m pytest tests/executor/test_profiles_v2.py -v` for profile validation
* [x] Run `uv run python -m pytest tests/executor/test_executor_controller.py -v` for controller tests

**Important:** This change only affects Fronius profile. Other profiles continue to use `{{discharge_value}}` which remains the raw export power without house load compensation.

---

### [DRAFT] REV // F76 — Fix Battery Discharge During EV Charging

**Goal:** Fix three critical bugs that allow battery discharge when EV is charging, even when source isolation should block it.

**Context:**
Beta testers reported battery discharging while EV is charging (observed at 06:45). Investigation revealed three separate bugs in the source isolation logic:

**Bug #1: Source Isolation Drops EV Data (executor/engine.py:1156-1163)**
When source isolation blocks discharge, it creates a new SlotPlan but does NOT copy `ev_charging_kw`, causing it to default to 0.0. This breaks downstream tracking and logging.
```python
slot = SlotPlan(
    charge_kw=slot.charge_kw,
    discharge_kw=0.0,  # Blocks discharge ✓
    # MISSING: ev_charging_kw=slot.ev_charging_kw  ✗
)
```

**Bug #2: No Actual EV Power Monitoring (Most Critical)**
The executor only blocks discharge based on SCHEDULED EV charging (`slot.ev_charging_kw > 0.1`), not ACTUAL power draw. If user manually starts EV charging via Home Assistant, Tesla app, or physical button, battery WILL discharge to EV because Darkstar doesn't detect actual power flow.

**Bug #3: `self_consumption` Mode Allows Discharge**
When SoC > target, controller uses `self_consumption` mode which relies on inverter "Auto" mode. Unlike `idle` mode (which sets discharge=0), `self_consumption` can still discharge. From CSV data: battery was in `self_consumption` mode during all discharge periods.

**Plan:**

#### Phase 1: Fix Source Isolation Data Loss [DRAFT]
* [ ] Fix `executor/engine.py:1156-1163` to include `ev_charging_kw=slot.ev_charging_kw` when reconstructing SlotPlan
* [ ] Verify `ev_charging_kw` is preserved through all SlotPlan operations
* [ ] Run `uv run ruff check .`

#### Phase 2: Monitor Actual EV Power [DRAFT]
* [ ] Add `get_total_ev_power()` method to `LoadDisaggregator` class
* [ ] Update `executor/engine.py` to query actual EV power during decision making
* [ ] Modify discharge blocking logic: `if scheduled_ev_charge OR actual_ev_power > 0.1 kW: block_discharge()`
* [ ] Add logging: "EV detected consuming X kW - blocking battery discharge"
* [ ] Run `uv run python -m pytest tests/ -v -k ev` for EV-related tests

#### Phase 3: Fix self_consumption Mode [DRAFT]
* [ ] Modify `executor/controller.py` to use `idle` mode instead of `self_consumption` when EV charging is active
* [ ] Alternative: Set `discharge_kw=0` and mode to `idle` when `ev_should_charge=True`
* [ ] Verify `idle` mode correctly blocks discharge in all inverter profiles
* [ ] Run `uv run python -m pytest tests/executor/test_executor_controller.py -v`

#### Phase 4: Integration Testing [DRAFT]
* [ ] Create test: Manual EV trigger via HA → discharge blocked
* [ ] Create test: Scheduled EV charging → discharge blocked
* [ ] Create test: High house load + EV charging → battery stays idle
* [ ] Run full test suite: `uv run python -m pytest -q`

---
