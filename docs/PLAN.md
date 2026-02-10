# Darkstar Energy Manager: Active Plan

**Vision: From Calculator to Agent**
Darkstar is transitioning from a deterministic optimizer (v1) to an intelligent energy agent (v2). It does not just optimize based on static config; it observes context (Weather, Vacation, Prices), predicts outcomes (Aurora ML), and actively strategizes (Strategy Engine) to maximize efficiency and comfort.

---

## Revision Naming Conventions

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

### [IN PROGRESS] REV // F53 — Fronius Auto Mode Entity Write Fixes

**Goal:** Prevent extraneous entity writes in Fronius "Auto" work mode. Only `minimum_reserve` (SoC target) should be written in Auto mode.
**Context:** Beta tester reports Fronius in "Auto" mode is receiving writes for `grid_charging`, `max_export_power`, and `discharge_limit` entities. Per `fronius_logic.md`, Auto mode ignores all controls except `minimum_reserve`.

**Plan:**

#### Phase 1: Fix Auto Mode Skip Logic [DONE]
* [x] Update `execute()` in `[executor/actions.py]` to check profile `skip_*` flags BEFORE calling `_set_grid_charging()`, `_set_discharge_limit()`, `_set_max_export_power()`
* [x] Fix generic optimization logic (lines 349-400) that only checks Charge/Idle modes, ignoring profile flags
* [x] Verify `self_consumption` and `zero_export` modes (both "Auto") properly skip all 3 entities
* [x] Test that only `soc_target` and `work_mode` are written in Auto mode

#### Phase 2: Fix Idle Status Display [DONE]
* [x] Update `_generate_reason()` in `[executor/controller.py]` to use profile mode descriptions instead of hardcoded "Hold/Idle" and "Zero-Export" labels
* [x] Use `profile.modes.*.description` for the reason string when available
* [x] Ensure "Auto" mode shows correct description, not "Idle"

#### Phase 3: Fix Config Reload on UI Save [DONE]
* [x] Add `executor.reload_config()` call in `[backend/api/routers/config.py]` after successful config save
* [x] Import `get_executor_instance` from executor router
* [x] Call reload_config() only if executor is running
* [x] Verify executor immediately picks up new settings without restart
* [x] Test with changing SoC target - should reflect immediately in executor status

---

### [DONE] REV // F54 — Sungrow Executor Display & Composite Mode Fixes

**Goal:** Fix three critical issues reported by Sungrow beta tester: Forced cmd not updating when work_mode unchanged, incorrect entity display in execution history, and unwanted SoC Target visibility.

**Context:** Sungrow profile uses composite mode entities (forced_charge_discharge_cmd, export_power_limit, max_discharge_power) that are set alongside work_mode changes. User reports that forced commands aren't updating and execution history shows confusing/misleading information.

**Issues Identified:**

1. **Forced cmd not written independently:** In `_set_work_mode()` (actions.py:462), composite mode entities are ONLY processed when work_mode changes. If Sungrow is already in "Forced mode" but needs to switch from "Forced discharge" to "Forced charge", the forced_charge_discharge_cmd is never updated because the composite loop is skipped when work_mode is already at target.

2. **Grid Charging shown incorrectly:** `_set_grid_charging()` returns ActionResult with "Handled by work_mode" message for Sungrow even though it's mode-based and shouldn't be displayed at all.

3. **SoC Target shown for unsupported profile:** `_set_soc_target()` returns ActionResult even when `supports_soc_target: false`, causing it to appear in execution history.

4. **Discharge Limit shown when skipped:** Even with `skip_discharge_limit: true`, an ActionResult is returned with "Skipped per mode setting" message.

5. **Max Export Power shown incorrectly:** Similar to discharge limit, this shows up even when it shouldn't for Sungrow modes.

**Plan:**

#### Phase 1: Fix Composite Mode Independent Updates [DONE]
* [x] Refactor `_set_work_mode()` in `[executor/actions.py]` to process composite mode entities even when work_mode is already at target
* [x] Extract composite entity processing into separate helper method `_apply_composite_entities()`
* [x] Call `_apply_composite_entities()` after the idempotency check for work_mode
* [x] Ensure forced_charge_discharge_cmd updates when charging intent changes (charge vs discharge) even if EMS mode stays "Forced mode"
* [x] All 28 executor action tests pass

#### Phase 2: Fix Grid Charging Silent Skip [DONE]
* [x] Modify `_set_grid_charging()` in `[executor/actions.py]` to return `None` when `separate_grid_charging_switch: false` or `grid_charging_control: false`
* [x] Update `execute()` method to handle `None` return values (filter out before appending to results)
* [x] Return type changed from `ActionResult` to `ActionResult | None`
* [x] All 28 executor action tests pass

#### Phase 3: Fix SoC Target Silent Skip [DONE]
* [x] Modify `_set_soc_target()` to return `None` when profile has `supports_soc_target: false`
* [x] Return `None` when entity not configured and not required by profile
* [x] Update `execute()` method to filter out `None` results
* [x] Return type changed from `ActionResult` to `ActionResult | None`
* [x] All 28 executor action tests pass

#### Phase 4: Fix Discharge Limit Silent Skip [DONE]
* [x] Modify `_set_discharge_limit()` to return `None` when `skip_discharge_limit: true` for current mode
* [x] Remove the "Skipped per mode setting" ActionResult for truly skipped actions
* [x] Update `execute()` method to filter out `None` results
* [x] Return type changed from `ActionResult` to `ActionResult | None`
* [x] All 28 executor action tests pass

#### Phase 5: Fix Max Export Power Silent Skip [DONE]
* [x] Add profile-aware skip logic to `_set_max_export_power()` to return `None`
* [x] Return `None` when mode has `skip_export_power: true` or profile doesn't support export limits
* [x] Return `None` when entity not configured and not required
* [x] Update `execute()` method to filter out `None` results
* [x] Return type changed from `ActionResult` to `ActionResult | None`
* [x] All 28 executor action tests pass

#### Phase 6: Execute Method Null Handling [DONE]
* [x] Update `execute()` method to filter out `None` results from all action methods
* [x] All action methods updated with `-> ActionResult | None` type hints
* [x] Verified no regression in action_results processing

#### Phase 7: Testing & Verification [DONE]
* [x] All 28 executor action tests pass
* [x] Linting checks pass (`uv run ruff check executor/actions.py`)
* [x] Grid charging, SoC target, discharge limit, and max export power now return `None` for silent skips
* [x] Composite mode entities are processed independently of work_mode changes
* [x] Execution history will be cleaner with fewer "Skipped" entries for unsupported features

---

### [DRAFT] REV // ARC15 — Entity-Centric Config Restructure for Load Disaggregation

**Goal:** Restructure configuration to eliminate duplication between `system.has_*` toggles, `input_sensors.*_power` entities, and `deferrable_loads` array. Create a single source of truth per entity with clear, expandable sections for Water Heating, EV Chargers, and future deferrable loads.

**Context:**
Current configuration duplicates the same information in 3 locations:
- `system.has_water_heater` / `system.has_ev_charger` (toggles)
- `input_sensors.water_power` / `input_sensors.ev_power` (sensors)
- `deferrable_loads[]` array (for LoadDisaggregator)

When users enable water heating in the UI, load disaggregation fails silently because the `deferrable_loads` array is never auto-populated. This causes the ML model to train on "dirty" total load (including deferrable loads) instead of "clean" base load, resulting in inaccurate forecasts.

The fix requires restructuring to entity-centric sections where each physical device (water heater, EV charger) has ONE config location containing all its settings, sensors, and load characteristics.

**Plan:**

#### Phase 1: Schema Design & Migration Strategy [DRAFT]
* [ ] Design new entity-centric schema for `water_heaters[]` array (plural, supporting multiple water heaters)
* [ ] Design new `ev_chargers[]` array schema (plural, supporting multiple EVs)
* [ ] Define category-based array structure (water_heaters[], ev_chargers[], pool_heaters[] - room for future expansion)
* [ ] Define migration path: old structure → new structure with automatic conversion
* [ ] Create migration script that runs on startup if old config detected
* [ ] Ensure backward compatibility during transition period (1-2 versions)
* [ ] Document new schema with clear examples and comments
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

#### Phase 2: Backend - Config Migration & Loading [DRAFT]
* [ ] Implement migration script `backend/config/migrate_arc15.py`
* [ ] Detect old config format and auto-convert to new format
* [ ] Update `backend/api/routers/config.py` to handle new schema
* [ ] Update config validation to support both old and new structures during transition
* [ ] Add config version tracking to detect migrations needed
* [ ] Ensure migration is idempotent (safe to run multiple times)
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

#### Phase 3: Backend - LoadDisaggregator Refactor [DRAFT]
* [ ] Refactor `backend/loads/service.py` to read from new entity-centric structure
* [ ] Iterate over `water_heaters[]` array to register multiple water heater loads
* [ ] Iterate over `ev_chargers[]` array to register multiple EV loads
* [ ] Remove dependency on `deferrable_loads` array entirely
* [ ] Ensure LoadDisaggregator initializes correctly with new config structure
* [ ] Update `backend/recorder.py` to use new LoadDisaggregator interface
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

#### Phase 4: Backend - Kepler Adapter Updates [DRAFT]
* [ ] Update `planner/solver/adapter.py` to read from new structure
* [ ] Iterate over `water_heaters[]` for water heating optimization parameters
* [ ] Iterate over `ev_chargers[]` for EV optimization parameters
* [ ] Ensure Kepler receives correct power ratings and constraints
* [ ] Handle multiple EVs in MILP solver input generation
* [ ] Handle multiple water heaters in MILP solver input generation
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

#### Phase 5: Frontend - Settings UI Redesign [DRAFT]
* [ ] Redesign System Settings UI to show entity-centric sections
* [ ] Water Heaters section: list view with add/edit/remove for multiple water heaters
* [ ] Each Water Heater card shows: name, power rating, sensor, spacing constraints
* [ ] EV Chargers section: list view with add/edit/remove for multiple EVs
* [ ] Each EV card shows: name, max power, battery capacity, sensor
* [ ] Remove confusing `deferrable_loads` references from UI
* [ ] Update form state management to handle new nested structure
* [ ] Ensure validation works for new schema
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

#### Phase 6: Frontend - API Integration [DRAFT]
* [ ] Update frontend API types to match new backend schema
* [ ] Ensure config save/load handles new structure correctly
* [ ] Test UI with multiple EVs configured
* [ ] Test UI with multiple water heaters configured
* [ ] Test migration detection and user notification
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

#### Phase 7: Documentation & Migration Guide [DRAFT]
* [ ] Update `docs/ARCHITECTURE.md` with new load disaggregation design
* [ ] Document entity-centric configuration philosophy
* [ ] Create migration guide for existing users
* [ ] Update config.default.yaml with new structure and extensive comments
* [ ] Update README with new configuration examples
* [ ] Document how to add future deferrable loads (pool heaters, heat pumps)
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

#### Phase 8: Testing & Validation [DRAFT]
* [ ] Write comprehensive tests for config migration scenarios
* [ ] Test LoadDisaggregator with new structure
* [ ] Test Kepler solver with multiple EVs
* [ ] Test frontend UI with various configurations
* [ ] Test migration from old to new format
* [ ] Test backward compatibility during transition
* [ ] Run full integration test suite
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

**New Config Structure (Target):**
```yaml
system:
  has_water_heater: true           # Global toggle (any water_heaters[] item enabled)
  has_ev_charger: true             # Global toggle (any ev_chargers[] item enabled)
  # ... other toggles

water_heaters:                     # Array for multiple water heaters (plural!)
  - id: main_tank                  # Unique identifier
    name: "Main Water Heater"      # Display name
    enabled: true                  # Can disable individual heaters
    power_kw: 3.0                  # Rated power
    min_kwh_per_day: 6.0           # Daily energy requirement
    max_hours_between_heating: 8   # Comfort constraint
    water_min_spacing_hours: 4     # Minimum gap between heating cycles
    sensor: sensor.vvb_power       # Power sensor for disaggregation
    type: binary                   # Load type (binary/modulating)
    nominal_power_kw: 3.0          # Nominal power for load calc

  - id: upstairs_tank              # Second water heater example
    name: "Upstairs Tank"
    enabled: false                 # Disabled for now
    power_kw: 3.0
    min_kwh_per_day: 4.0
    sensor: sensor.wh2_power
    type: binary
    nominal_power_kw: 3.0

ev_chargers:                       # Array for multiple EVs
  - id: tesla_model_3              # Unique identifier
    name: "Tesla Model 3"          # Display name
    enabled: true                  # Can disable individual EVs
    max_power_kw: 11.0             # Max charging power
    battery_capacity_kwh: 82.0     # EV battery size
    min_soc_percent: 20.0          # Minimum charge level
    target_soc_percent: 80.0       # Target charge level
    sensor: sensor.tesla_power     # Power sensor for disaggregation
    type: variable                 # Load type
    nominal_power_kw: 11.0         # Nominal power for load calc

  - id: fiat_500e                  # Second EV example
    name: "Fiat 500e"
    enabled: true
    max_power_kw: 7.4
    battery_capacity_kwh: 42.0
    sensor: sensor.fiat_power
    type: variable
    nominal_power_kw: 7.4

# Future expansion examples:
# pool_heaters: []
# heat_pumps: []
# dishwashers: []

# deferrable_loads[] REMOVED - no longer needed
```

**Acceptance Criteria:**
- [ ] User can add multiple water heaters with individual settings and load disaggregation works
- [ ] User can add multiple EV chargers with individual settings and load disaggregation works
- [ ] Config has single source of truth per entity (no duplication)
- [ ] Migration from old format happens automatically on startup
- [ ] All existing tests pass with new structure
- [ ] Documentation reflects new architecture
- [ ] Settings UI is intuitive and guides user clearly
- [ ] Schema is future-proof for pool heaters, heat pumps, etc.
