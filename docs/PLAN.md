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

### [DRAFT] REV // F74 — Fix Initial Load Unit Normalization (W vs kW)

**Goal:** Ensure the initial dashboard load (`/api/status`) correctly normalizes all power sensors to kW by checking their Home Assistant `unit_of_measurement`, matching the behavior of the live WebSocket feed.

**Context:**
Currently, `get_system_status()` in `backend/api/routers/system.py` blindly divides Solar, Grid, Load, and Battery power by 1000 assuming they are in Watts, but it assumes EV sensors are already in Kilowatts. This causes massive spikes (e.g., 641.9 kW instead of 0.6 kW) on initial load if the user configured an EV sensor that outputs Watts. The live WebSocket correctly parses `unit_of_measurement` and fixes it after 30 seconds.

**Plan:**

#### Phase 1: Smart Sensor Helper (Backend) [DRAFT]
* [ ] Create a new async helper function in `inputs.py` named `get_ha_sensor_kw_normalized(entity_id: str)`.
* [ ] This function should fetch the full entity state using `get_ha_entity_state(entity_id)`.
* [ ] If the state exists, extract the numeric `state` value.
* [ ] Check `attributes.unit_of_measurement`. If it equals "W" (case-insensitive), divide the value by 1000.0. Return the final kW float.

#### Phase 2: Refactor Initial Hydration (Backend) [DRAFT]
* [ ] Update `get_system_status()` in `backend/api/routers/system.py`.
* [ ] Swap the `get_ha_sensor_float` calls for `pv_power`, `load_power`, `battery_power`, `grid_power`, and EV `sensor` to use the new `get_ha_sensor_kw_normalized`.
* [ ] Remove the hardcoded `/ 1000.0` divisions at the bottom of the function when constructing the `StatusResponse` (since the new helper already handles it).
* [ ] Leave `battery_soc`, EV `soc_sensor`, and EV `plug_sensor` alone, as they are not power metrics.
* [ ] Run `pytest` and `pyright` to ensure no regressions.
