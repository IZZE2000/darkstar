# Darkstar Energy Manager: Active Plan

**Vision: From Calculator to Agent**
Darkstar is transitioning from a deterministic optimizer (v1) to an intelligent energy agent (v2). It does not just optimize based on static config; it observes context (Weather, Vacation, Prices), predicts outcomes (Aurora ML), and actively strategizes (Strategy Engine) to maximize efficiency and comfort.

---

| Prefix  | Area                 | Examples |
| ------- | -------------------- | -------- |
| **K**   | Kepler (MILP solver) | F41      |
| **E**   | Executor             | E1       |
| **A**   | Aurora (ML)          | A29      |
| **H**   | History/DB           | H1       |
| **O**   | Onboarding           | O1       |
| **UI**  | User Interface       | UI2      |
| **DS**  | Design System        | DS1      |
| **F**   | Fixes/Bugfixes       | F6       |
| **DX**  | Developer Experience | DX1      |
| **ARC** | Architecture         | ARC1     |
| **IP**  | Inverter Profiles    | IP1      |

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

### [DRAFT] REV // K26 — Inverter Clipping Support

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

### [DONE] REV // UI21 — Add Actual PV/Load to Schedule Chart

**Goal:** Display actual (observed) PV and load data in the ChartCard alongside forecasts when the "Actual" overlay is toggled.
**Context:** The frontend already supports showing "Actual PV/Load" datasets with dashed lines, but the backend schedule endpoint doesn't provide the actual data from `SlotObservation`. Users want to compare forecast vs actual.

**Plan:**

#### Phase 1: Backend - Add Observations Query [DONE]
* [x] Add method `get_observations_range()` to `backend/learning/store.py` that queries `SlotObservation` for `pv_kwh`, `load_kwh`, `water_kwh`, `slot_start` within a date range.
* [x] Import and call this method in `backend/api/routers/schedule.py` in `schedule_today_with_history()`.
* [x] Populate `actual_pv_kwh`, `actual_load_kwh`, `actual_water_kw` in the slot response for historical slots.

#### Phase 2: Frontend Verification [DONE]
* [x] Verify `buildLiveData()` in `frontend/src/components/ChartCard.tsx` correctly maps the new fields.
* [x] Test that toggling "📊 Actual" button shows dashed lines for actual PV and load.
* [x] Ensure actual data only appears for historical slots (where `is_executed=true`).

---

### [DONE] REV // F69 — Sungrow Beta Config Regression Fix

**Goal:** Fix two regressions affecting Sungrow beta testers: executor errors about missing max_discharge_power, and settings save failures for profile-specific entity keys.

**Context:**
- Issue 1: Executor error: "Profile requires setting 'max_discharge_power' to '10', but entity is not configured" - This happens because executor/actions.py only checks `custom_entities` but max_discharge_power is a standard key in `executor.inverter`.
- Issue 2: Settings save fails because profile-specific keys (ems_mode, forced_charge_discharge_cmd) are in wrong location (directly in executor.inverter instead of executor.inverter.custom_entities).
- Root cause: User's config has keys in legacy locations that worked before stricter validation was added. No migration exists to move them to correct location.

**Plan:**

#### Phase 1: Config Migration [COMPLETED]
* [x] Add `migrate_inverter_custom_entities()` function to `backend/config_migration.py`.
* [x] Detect profile-specific keys in wrong location: `ems_mode`, `ems_mode_entity`, `forced_charge_discharge_cmd`, `forced_charge_discharge_cmd_entity`.
* [x] Move these from `executor.inverter` → `executor.inverter.custom_entities`, stripping `_entity` suffix.
* [x] Register migration in `MIGRATION_STEPS` after existing inverter migrations.
* [ ] Test migration with user's config snippet to verify correct move.

#### Phase 2: Executor Actions Fix [COMPLETED]
* [x] In `executor/actions.py` line ~569, add fallback lookup for composite entity handling.
* [x] Check `custom_entities` FIRST.
* [x] If not found AND key is in STANDARD_ENTITY_KEYS, fall back to checking standard `executor.inverter` location.
* [x] Run ruff/format and verify no lint errors.

#### Phase 3: Validation & Testing [COMPLETED]
* [ ] Verify validation now passes with user's config after migration runs.
* [x] Run full test suite: `uv run python -m pytest -q`.
* [ ] Test that executor no longer errors on Sungrow idle mode.

---

### [PLANNED] REV // F70 — Fix Non-Deterministic PV Forecast Corrector

**Goal:** Make Aurora corrector model training deterministic by adding fixed random seeds, ensuring repeatable PV forecasts across planner runs.

**Context:**
The Aurora ML pipeline uses corrector models (`pv_error.lgb`, `load_error.lgb`) to adjust base forecasts based on historical errors. These models are trained using LightGBM with `feature_fraction: 0.9` and `bagging_fraction: 0.8` for robustness, but lack a fixed `seed` parameter. This causes:
- Slightly different corrector models every training run
- Different PV forecast corrections between planner executions
- Inconsistent scheduling decisions even with identical weather/pricing data

**Root Cause:** In `ml/corrector.py:167-178`, the `lgb.train()` call uses random sampling without a seed, making training non-deterministic.

**Plan:**

#### Phase 1: Add Fixed Seeds to Corrector Training [DONE]
* [x] Add `seed=42` and `bagging_seed=42` to LightGBM params in `_train_error_models()` function
* [x] Verify the change is minimal (2 lines) and consistent with existing `random_state=42` in `ml/train.py`
* [x] Run `uv run ruff check .` to ensure no lint errors
* [x] Run `uv run python -m pytest tests/test_corrector_clamp.py -v` to verify existing tests pass

#### Phase 2: Verification [DONE]
* [x] Run planner twice in succession and compare PV forecast curves
* [x] Verify forecasts are now identical between runs (with same Open-Meteo data)
* [x] Confirm corrector models produce consistent corrections at Graduate level (14+ days data)
* [x] Document the fix in code comments explaining the seed choice

---

### [DONE] REV // F71 — Sungrow Composite Entity Loading & EV Serialization Fix

**Goal:** Fix two bugs causing executor failures for Sungrow users: composite entity config not loading, and EV charger history crashes.

**Context:**
- **Bug 1 (Critical):** `executor/config.py` has a dict comprehension (lines 324–356) that collects all non-standard `inverter_data` keys into `custom_entities`. The key `"custom_entities"` itself is NOT in the exclusion set, so the nested YAML dict `{ems_mode: ..., forced_charge_discharge_cmd: ...}` gets passed through `_str_or_none()` which **stringifies the entire dict** instead of unpacking it. Result: `self.config.inverter.custom_entities.get("ems_mode")` returns `None`, causing "Entity not configured" errors for ALL Sungrow composite modes. REV F69 migration only handles legacy misplaced keys — it does not fix the loading path for correctly-structured configs.
- **Bug 2 (Medium):** `executor/engine.py` lines 1646–1657 and 1671–1682 store raw `ActionResult` dataclass objects in `action_results=[result]` for EV charger events. When the `ExecutionRecord` is serialized to JSON for the history DB, it crashes with `Object of type ActionResult is not JSON serializable`. The main execute path (line 1487–1501) correctly converts to dicts but the EV path does not.

**Plan:**

#### Phase 1: Fix custom_entities Loading [DONE]
* [x] In `executor/config.py`, add `"custom_entities"` to the exclusion set in the dict comprehension (line ~329).
* [x] After the comprehension, explicitly unpack `inverter_data.get("custom_entities", {})` and merge into `custom_entities` dict with `_str_or_none()` per value.
* [x] Verify the catch-all still works for other non-standard keys (e.g., `work_mode_export`).

#### Phase 2: Fix EV ActionResult Serialization [DONE]
* [x] In `executor/engine.py` lines ~1655 and ~1682, convert `ActionResult` to dict before storing in `action_results`, matching the pattern used in `_create_execution_record()` (lines 1487–1501).

#### Phase 3: Testing [DONE]
* [x] Write unit test: load a config with properly nested `custom_entities` and assert `InverterConfig.custom_entities["ems_mode"]` resolves correctly.
* [x] Write unit test: verify EV charger execution record serializes to JSON without error.
* [x] Run full test suite: `uv run python -m pytest -q`.
* [x] Run linting: `uv run ruff check .`.
