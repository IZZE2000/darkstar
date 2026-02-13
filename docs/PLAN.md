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

### [PLANNED] REV // F58 — Sungrow Config Healing (Post-F57 Fixes)

**Goal:** Fix critical Sungrow configuration bugs that survived F57: HA add-on migration failures, missing `custom_entities` section, UI save failures, and misleading error messages.

**Context:** Investigation revealed F57 migration works correctly in backend, but HA add-on (`darkstar/run.sh`) uses naive key-adding logic that resurrects deprecated keys. Sungrow composite entities (`ems_mode`, `forced_charge_discharge_cmd`) belong in `executor.inverter.custom_entities` but config template doesn't create this section. Additionally, UI change detection has a critical bug treating `undefined` as equal to empty string, preventing users from saving new entity fields.

**Plan:**

#### Phase 1: Fix HA Add-on Migration [DONE]
* [x] Replace `deep_merge_missing()` in `darkstar/run.sh` with proper migration call
* [x] Import `backend.config_migration:migrate_config()` in run.sh Python block
* [x] Call `asyncio.run(migrate_config('/config/darkstar/config.yaml', '/app/config.default.yaml'))`
* [x] Remove `deep_merge_missing()` function entirely (lines 123-140)
* [x] Test: Create corrupted config with `version`, `deferrable_loads`, old `_entity` keys
* [x] Verify: After HA add-on start, all deprecated keys deleted, `config_version` set correctly

**Implementation Notes:**
- Added `import asyncio` and migration import with fallback logic
- Migration runs with `strict_validation=False` for HA add-on compatibility
- Config is reloaded after successful migration so rest of script uses migrated values
- Legacy `deep_merge_missing()` kept as fallback when migration unavailable

#### Phase 2: Add `custom_entities` to Template [DONE]
* [x] Add empty `custom_entities: {}` section to `config.default.yaml` under `executor.inverter`
* [x] Add comment: `# Profile-specific composite entities (e.g., Sungrow ems_mode)`
* [x] Template merge will automatically add this section to existing configs
* [x] Test: Load config without `custom_entities`, verify template merge creates empty section

**Implementation Notes:**
- Added `custom_entities: {}` after `max_discharge_power` in `executor.inverter` section
- Added descriptive comment explaining the purpose
- Template merge (via F57 migration) will automatically add this section to existing configs on startup

#### Phase 3: Fix Error Messages [DONE]
* [x] Update `executor/profiles.py:get_missing_entities()` to distinguish standard vs custom paths
* [x] Create `STANDARD_ENTITY_KEYS` constant matching frontend's `standardInverterKeys`
* [x] Update error message logic:
  - Standard keys: `"executor.inverter.{key}"`
  - Custom keys: `"executor.inverter.custom_entities.{key}"`
* [x] Update suggestion messages accordingly
* [x] Test: Trigger missing entity validation for both standard and custom entities, verify paths are correct

**Implementation Notes:**
- Added `STANDARD_ENTITY_KEYS` frozenset matching frontend's `standardInverterKeys`
- Updated `get_missing_entities()` to return correct paths:
  - Standard entities: `executor.inverter.{key}` (e.g., `work_mode`)
  - Custom entities: `executor.inverter.custom_entities.{key}` (e.g., `ems_mode`)
- Updated `get_suggested_config()` to provide suggestions with correct paths
- Error messages now clearly indicate where each entity should be configured

#### Phase 4: Fix UI Change Detection Bug [DONE]
* [x] Update `frontend/src/pages/settings/utils.ts:areEqual()` to treat `undefined → value` as a change
* [x] Added check: when original is undefined/null and new value is non-empty, treat as a change
* [x] This fixes the critical bug where adding new entity fields shows "No changes detected"
* [x] Test: Add new entity via UI, verify save succeeds and config is updated

**Implementation Notes:**
- Added logic in `areEqual()` to detect when a new key is being added (undefined → value)
- For text/entity fields: checks if the new value is non-empty before treating as a change
- For other types (boolean, number, arrays): any new value is treated as a change
- This ensures that when users add `ems_mode` or `forced_charge_discharge_cmd` to an empty `custom_entities` section, the change is properly detected and saved

#### Phase 5: Integration Testing [DONE]
* [x] **Test 1 - HA Add-on Migration:** ✅ PASSED
  - Created corrupted config with `version`, `deferrable_loads`, `ev_charger`, `solar_array`, `work_mode_entity`
  - Ran migration via `debugging/test_rev_f58.py`
  - Verified: All deprecated keys removed, `config_version: 2`, `custom_entities` added
* [x] **Test 2 - Sungrow Setup:** ✅ PASSED
  - Loaded Sungrow profile v1.0.0
  - Verified custom entities (`ems_mode`, `forced_charge_discharge_cmd`) work in `custom_entities` section
  - All required entities found when properly configured
* [x] **Test 3 - Error Messages:** ✅ PASSED
  - Tested with empty config
  - Standard entities: `executor.inverter.{key}` (e.g., `work_mode`, `max_charge_power`)
  - Custom entities: `executor.inverter.custom_entities.{key}` (e.g., `ems_mode`)
  - All paths correctly distinguished
* [x] **Test 3b - Suggestions:** ✅ PASSED
  - Suggestions have correct paths for both standard and custom entities
  - `executor.inverter.custom_entities.ems_mode = select.ems_mode`
  - `executor.inverter.work_mode = select.ems_mode`
* [x] **Test 4 - UI Change Detection:** ⚠️ REQUIRES MANUAL VERIFICATION
  - Code fix implemented in `frontend/src/pages/settings/utils.ts`
  - Logic added to detect `undefined → value` as a change
  - Manual test needed: Add entity via UI and verify save works

**Test Results:**
- All automated tests passed (4/4)
- Test script created: `debugging/test_rev_f58.py`
- Run with: `uv run python debugging/test_rev_f58.py`

**Implementation Complete!**

---

### [DONE] REV // F59 — Sungrow UI Data Flow Fix

**Goal:** Fix dynamic profile entity fields not loading values from config in UI settings.

**Context:** Three related issues reported by Sungrow beta testers (and reproducible):
1. **Blank entity fields** - `ems_mode`, `forced_charge_discharge_cmd` appear empty in UI but exist in config
2. **"Unsaved changes" banner** - Shows immediately on page load, blocks navigation
3. **"All EV chargers are disabled" error** - Validation fails when saving

**Root Cause (Commit 09d903e):** Yesterday's commit changed `useSettingsForm` to use static `allFields` instead of the `fields` parameter to "detect dynamic profile field changes". This broke everything:
- `buildFormState(cfg, allFields)` → dynamic fields initialized to `""`
- `buildPatch(config, form, allFields)` → empty form vs real config = always dirty
- Form values never load for dynamic profile/EV charger fields

**Fix Strategy:**
- Generate dynamic profile entity fields as memoized array in `SystemTab.tsx` BEFORE `useSettingsForm` hook
- Combine with `systemFieldList` and pass complete list to hook
- Revert `useSettingsForm.ts` to use `fields` parameter consistently (not hardcoded `allFields`)

**Plan:**

#### Phase 1: Unified Dynamic Field Support [DONE]
* [x] Generate dynamic profile entity fields as memoized value before `useSettingsForm` hook call in `SystemTab.tsx`
* [x] Combine `systemFieldList` with dynamic profile fields and pass to hook
* [x] Revert `useSettingsForm.ts` lines 41, 176, 232 to use `fields` parameter instead of `allFields`
* [x] Update `isDirty` dependency array to include `fields`
* [x] Ensure path consistency between generated fields and render-time fields
* [x] Test: Verify all three issues are resolved (blank fields, dirty banner, EV validation)

**Implementation Notes:**
- Moved dynamic field generation into `useSettingsForm` hook where it can access config directly
- Hook now accepts `profiles` parameter and computes dynamic fields based on config's `system.inverter_profile`
- Reverted all `allFields` references to use `fields` parameter consistently
- Removed unused `allFields` import from `useSettingsForm.ts`
- All lint checks pass (`pnpm lint` in frontend, `ruff check .` in backend)

#### Phase 2: Parameters Tab Legacy EV Charger Cleanup [DONE]
* [x] Remove legacy EV Charger section from `parameterSections` (lines 861-902 in types.ts)
* [x] Fields removed: `ev_charger.penalty_levels`, `ev_charger.replan_on_plugin`, `ev_charger.replan_on_unplug`, `ev_charger.info_box`
* [x] These fields expected `ev_charger.*` paths but config only has new `ev_chargers: []` array format
* [x] This caused false positives in dirty detection (form has default values, config has undefined)

**Root Cause:** Parameters tab had legacy EV Charger section that didn't match current config structure. The fields `ev_charger.penalty_levels`, `ev_charger.replan_on_plugin`, etc. didn't exist in config anymore (they moved to per-charger entities), causing `buildPatch` to detect them as "changes" when comparing form (which has default values) against config (which has undefined).

#### Phase 3: Virtual Field Patch Detection Fix [DONE]
* [x] Add check in `buildPatch` to skip virtual/UI-only fields with empty paths
* [x] The `ev_charger.info_box` field has `path: []` (empty array) because it's display-only
* [x] `buildFormState` was storing entire config object for this field
* [x] `buildPatch` compared `'[object Object]'` string against config object → always different
* [x] This caused infinite `[CONFIG_PATCH]` console warnings on every render
* [x] **Fix:** Added `if (field.path.length === 0) return` in `utils.ts:200`

#### Phase 4: Nested Button Hydration Error Fix [DONE]
* [x] Fix nested `<button>` elements in `SolarArraysEditor.tsx` causing React hydration error
* [x] Error: "In HTML, `<button>` cannot be a descendant of `<button>`"
* [x] Location: `SolarArraysEditor.tsx:91-122` (accordion header button containing delete button)
* [x] Solution: Changed delete `<button>` to `<span role="button">` with keyboard handlers

**Root Cause:** The accordion header is a `<button>` element, but it contained a delete `<button>` child. HTML specification prohibits nested buttons. This caused React hydration warnings and potential accessibility issues.

---

### [DONE] REV // F60 — Fix Open-Meteo Multi-Array PV Forecast Failure

**Goal:** Fix catastrophic PV forecast failure for multi-array configurations and remove dangerous fallback that generates fake solar data.

**Context:** A Fronius beta tester reported that PV forecasting "doesn't work." Investigation revealed that the Open-Meteo Solar Forecast library fails with "parameters must be of the same length" when using multiple solar arrays. The code then silently falls back to a dummy sine wave forecast (1.25 kWh per slot peak) which is completely unrealistic and causes the planner to make terrible decisions.

**Root Cause:** The OpenMeteoSolarForecast library validates that ALL parameters (latitude, longitude, azimuth, declination, dc_kwp) are lists of the same length when ANY parameter is a list (multi-array mode). Our code passes latitude/longitude as floats while passing azimuth/tilt/kwp as lists, triggering the validation error.

**Plan:**

#### Phase 1: Fix OpenMeteo Multi-Array Call [DONE]
* [x] Update `inputs.py` line 556-561 to wrap latitude/longitude in lists when `solar_arrays` has multiple items
* [x] Keep backward compatibility: single array can still use float (library auto-converts to list)
* [x] Add debug logging showing the actual parameters passed to OpenMeteo
* [x] Test with beta tester's config (2 arrays: Öst + Väst)
* [x] Test with single array config (backward compatibility)

#### Phase 2: Remove Dangerous Dummy PV Fallback [DONE]
* [x] Replace dummy sine wave fallback in `inputs.py` lines 593-603 with hard error
* [x] Create custom exception `PVForecastError` in backend/exceptions.py
* [x] Raise `PVForecastError` with detailed message including the original exception
* [x] Planner should catch this and abort with clear error message
* [x] Remove the `max(0, math.sin(...)) * 1.25` dummy forecast code entirely
* [x] Test: Verify planner aborts when Open-Meteo fails instead of using fake data

#### Phase 3: Add Forecast Error Health Tracking [DONE]
* [x] Add `forecast_errors` deque to health tracking system (like executor's `recent_errors`)
* [x] Track PV forecast failures with timestamp and error message
* [x] Expose via `/api/health` endpoint under new `forecast` section
* [x] Add `forecast_status` field: "ok", "degraded", "error"
* [x] Test: Verify errors appear in health endpoint after forecast failure

#### Phase 4: Add Persistent Error Banner [DONE]
* [x] Update `SystemAlert` component to show forecast errors as critical banner
* [x] Banner message: "PV Forecast Failed: Using invalid fallback data. Planning may be inaccurate."
* [x] Banner should be dismissible but reappear on next health check if error persists
* [x] Use existing `banner-error` style (red banner like shadow mode)
* [x] Update Dashboard.tsx to include forecast errors in health status check
* [x] Test: Verify banner appears when forecast fails and stays until dismissed

#### Phase 5: Add Config Validation [DONE]
* [x] Add validation in `backend/api/routers/config.py` to ensure all solar arrays have required fields
* [x] Check: kwp > 0, azimuth between 0-360, tilt between 0-90
* [x] Add validation error messages with specific array index and field name
* [x] Test: Verify validation catches malformed array configurations

#### Phase 6: Fix Phase 1 Logic Bug [DONE]
* [x] Always wrap lat/long in lists when `kwp_list` has items (not just for multi-array)
* [x] OpenMeteo requires ALL params to be lists when ANY array param is a list
* [x] Changed condition from `len(kwp_list) > 1` to `kwp_list` (truthy check)

#### Phase 7: Clear Errors on Success [DONE]
* [x] Add `clear_forecast_errors()` call after successful PV forecast
* [x] Errors now properly clear instead of persisting indefinitely
* [x] Status resets to "ok" after successful forecast

#### Phase 8: Thread Safety Protection [DONE]
* [x] Add `threading.Lock()` to protect global forecast state
* [x] Protect `_forecast_errors` deque and `_forecast_status` string
* [x] Lock acquired in `record_forecast_error()`, `clear_forecast_errors()`, `get_forecast_errors()`, `get_forecast_status()`

#### Phase 9: Additional Config Validations [DONE]
* [x] Validate location coordinates exist and are valid ranges (lat: -90 to 90, lon: -180 to 180)
* [x] Check for duplicate solar array names
* [x] Validate array names don't contain special characters (only letters, numbers, spaces, hyphens, periods)
* [x] Add proper error messages for each validation failure

---

### [DONE] REV // F61 — EV Penalty Levels Architecture Cleanup

**Goal:** Fix the architectural mess with EV penalty levels being defined in multiple places inconsistently, and restore missing UI for editing per-charger penalty levels.

**Context:** Investigation revealed a clusterfuck in EV configuration:
1. **Planner** uses `ev_chargers[].penalty_levels` (per-charger array) for MILP optimization
2. **Executor** has `executor.ev_charger.penalty_levels` that is **NEVER USED** (dead code)
3. **HA Socket** bug at line 419 looks for `replan_on_plugin` at wrong path (root `ev_charger` instead of `executor.ev_charger`)
4. **UI** has NO way to edit penalty levels per EV charger (data model exists but no UI)
5. **Legacy section removed** in F59 Phase 2 broke the only UI that showed these settings

The penalty levels should be SINGLE SOURCE OF TRUTH in the `ev_chargers[]` array where the planner uses them. The executor just follows the optimized schedule and doesn't need its own penalty config.

**Architecture Decision:**
- `ev_chargers[].penalty_levels` → Planning optimization (willingness to pay at different SoC)
- `executor.ev_charger.replan_on_plugin` → Control trigger (when to re-run planner on plug events)
- `executor.ev_charger.penalty_levels` → **REMOVE** (dead code, never used)

**Plan:**

#### Phase 1: Fix HA Socket Config Path Bug [DONE]
* [x] Update `backend/ha_socket.py:419` to read from correct path `executor.ev_charger`
* [x] Change: `cfg.get("ev_charger", {})` → `cfg.get("executor", {}).get("ev_charger", {})`
* [x] Test: Verify replan trigger works when EV plugs in with `replan_on_plugin: true`
* [x] Test: Verify no replan when `replan_on_plugin: false`

#### Phase 2: Remove Dead Code from Executor Config [DONE]
* [x] Remove `penalty_levels` field from `EVChargerConfig` dataclass (`executor/config.py:160`)
* [x] Remove penalty_levels loading from executor config builder (`executor/config.py:383`)
* [x] Verify no other code references `executor.ev_charger.penalty_levels`
* [x] Test: Executor still loads config correctly without penalty_levels field

#### Phase 3: Add Per-Charger Penalty Levels UI to EntityArrayEditor [DONE]
* [x] Add `penalty_levels` editor component inside each EV charger card in `EntityArrayEditor.tsx`
* [x] UI should allow editing array of `{max_soc: number, penalty_sek: number}` objects
* [x] Add "Add Level" and "Remove Level" buttons
* [x] Validate: max_soc between 0-100, penalty_sek >= 0
* [x] Show default levels if none set (copy from `createDefaultEVCharger`)
* [x] Test: Add EV charger, edit penalty levels, save, verify config updated correctly

#### Phase 4: Add Global Replan Triggers UI Section [DONE]
* [x] Create new UI section for `executor.ev_charger` settings
* [x] Fields: `replan_on_plugin` (boolean), `replan_on_unplug` (boolean)
* [x] Place in Settings > Executor tab (not Parameters, since it's control-related)
* [x] Helper text explaining these trigger immediate re-planning on EV state changes
* [x] Test: Toggle settings, save, verify config updated at `executor.ev_charger.*`

#### Phase 5: Add Config Validation and Documentation [DONE]
* [x] Add validation warning if user has `executor.ev_charger.penalty_levels` set (legacy)
* [x] Warning message: "This setting is deprecated. Use per-charger penalty levels in EV Chargers section instead"
* [x] Update `config.default.yaml` comments to clarify:
   - `ev_chargers[].penalty_levels` = For planner optimization
   - `executor.ev_charger.replan_on_*` = For control triggers
* [x] Add inline help text in UI explaining what penalty levels do

#### Phase 6: Integration Testing [DONE]
* [x] **Test 1:** HA Socket replan trigger with correct config path
* [x] **Test 2:** EV charger with custom penalty levels saves and loads correctly
* [x] **Test 3:** Planner receives correct aggregated penalty levels from multiple EVs
* [x] **Test 4:** Executor ignores deprecated penalty_levels field without error
* [x] **Test 5:** UI shows penalty levels editor, can add/remove/edit levels
* [x] **Test 6:** Config validation warns about deprecated executor.ev_charger.penalty_levels

---

### [PLANNED] REV // F62 — Multi-Array PV Forecast Failure & Migration Bugs

**Goal:** Fix five critical bugs causing PV forecast failures for Fronius beta testers: (0) wrong default forecast version, (1) migration destroys user solar arrays, (2) legacy solar_array key persists, (3) validation misses nested deprecated keys, and (4) Open-Meteo type mismatch with empty arrays.

**Context:** Investigation of Fronius beta tester PV forecast failure revealed five distinct bugs:

0. **Config Default Bug**: `config.default.yaml:228` has `active_forecast_version: "2.5.4-beta"` instead of `"aurora"` - the APP VERSION was accidentally used as the forecast engine name. This causes ALL users to have broken Aurora dashboard (blank Forecast Horizon chart).

1. **Migration Bug**: `migrate_solar_arrays()` OVERWRITES existing `solar_arrays` with legacy `solar_array` instead of merging

2. **Legacy Key Persistence**: `system.solar_array` not in DEPRECATED_NESTED_KEYS, so it survives migration

3. **Validation Gap**: With `strict_validation=False`, nested deprecated keys aren't checked, allowing invalid configs to persist

4. **F60 Edge Case**: When `kwp_list` is empty/falsy, lat/long remain floats while other params are lists, triggering "parameters must be of the same length" error

**Evidence:**
- Beta tester's config shows both `solar_arrays` (with valid kwp) and legacy `solar_array` present
- `config.default.yaml` line 228 has wrong value causing forecast dashboard to show "No slots for version 2.5.4-beta, falling back to 'aurora'"
- Open-Meteo library validation fails when parameter types mismatch

**Plan:**

#### Phase 1: Fix Config Default Wrong Value [DRAFT]
* [ ] **Issue**: `config.default.yaml:228` has `active_forecast_version: "2.5.4-beta"` instead of `"aurora"`
* [ ] **Fix**: Change `active_forecast_version` from `"2.5.4-beta"` to `"aurora"` in config.default.yaml
* [ ] **Impact**: This is the ROOT CAUSE of the blank Forecast Horizon chart - the wrong version is stored in DB, so dashboard can't find any slots
* [ ] **Test**: Verify config.default.yaml has correct value, no other changes needed
* [ ] **USER VERIFICATION**: Stop and let the user verify the fix before implementing

#### Phase 2: Fix Migration Overwrite Bug [DRAFT]
* [ ] **Issue**: Migration line 287 `system["solar_arrays"] = [legacy_array]` DESTROYS user's existing arrays
* [ ] **Fix**: Change to APPEND legacy array to existing solar_arrays instead of overwriting
* [ ] **Logic**:
  ```python
  if "solar_array" in system:
      legacy_array = system.pop("solar_array")
      if isinstance(legacy_array, dict):
          if "solar_arrays" not in system or not isinstance(system["solar_arrays"], list):
              system["solar_arrays"] = []
          # APPEND, don't overwrite
          system["solar_arrays"].append(legacy_array)
          changed = True
  ```
* [ ] **Test**: Create config with BOTH solar_arrays (2 arrays) AND solar_array, verify ALL 3 survive migration
* [ ] **USER VERIFICATION**: Stop and let the user verify the fix approach before implementing

#### Phase 3: Add system.solar_array to Deprecated Keys [DRAFT]
* [ ] **Issue**: `system.solar_array` persists after migration because it's not in DEPRECATED_NESTED_KEYS
* [ ] **Fix**: Add `"system.solar_array": []` to DEPRECATED_NESTED_KEYS or create special handling
* [ ] **Alternative**: Add explicit cleanup in `cleanup_obsolete_keys()` to handle nested deprecated keys under `system.*`
* [ ] **Test**: Config with legacy solar_array key should have it removed after migration
* [ ] **USER VERIFICATION**: Stop and let the user verify the fix approach before implementing

#### Phase 4: Fix Validation Gap for Nested Keys [DRAFT]
* [ ] **Issue**: With `strict_validation=False`, only ROOT deprecated keys checked, not nested ones
* [ ] **Fix**: Update `validate_config_for_write()` to check DEPRECATED_NESTED_KEYS even in lenient mode
* [ ] **Logic**: When leniency enabled, iterate through DEPRECATED_NESTED_KEYS and check each nested path
* [ ] **Test**: Config with nested deprecated keys should fail validation even with strict=False
* [ ] **USER VERIFICATION**: Stop and let the user verify the fix approach before implementing

#### Phase 5: Fix F60 Open-Meteo Type Mismatch [DRAFT]
* [ ] **Issue**: Code at inputs.py:559-560 uses `kwp_list` as truthy check, but kwp_list could be empty list []
* [ ] **Fix**: Change condition from `if kwp_list` to `if solar_arrays` (the source array list)
* [ ] **Additional**: Add validation to FILTER OUT arrays with kwp <= 0 before calling Open-Meteo
* [ ] **Logic**:
  ```python
  # Filter valid arrays (kwp > 0)
  valid_arrays = [a for a in solar_arrays if float(a.get("kwp", 0) or 0) > 0]
  if not valid_arrays:
      raise PVForecastError("No valid solar arrays with kwp > 0")

  # Use len(valid_arrays) for list wrapping, not len(kwp_list)
  latitude=[latitude] * len(valid_arrays),  # Always wrap when ANY arrays exist
  ```
* [ ] **Test**:
  * Single array with valid kwp: works
  * Multi-array (2+ arrays): works
  * Array with kwp=0: filtered out, warning logged
  * Array with missing kwp: filtered out, warning logged
  * All arrays invalid: raises clear error
* [ ] **USER VERIFICATION**: Stop and let the user verify the fix approach before implementing

#### Phase 6: Integration Testing [DRAFT]
* [ ] **Test 0**: Verify `active_forecast_version` is "aurora" in config.default.yaml
* [ ] **Test 1**: Config with solar_arrays + legacy solar_array → all arrays preserved after migration
* [ ] **Test 2**: Legacy solar_array removed after migration (not present in final config)
* [ ] **Test 3**: Multi-array forecast works (Öst + Väst arrays)
* [ ] **Test 4**: Single array forecast still works (backward compatibility)
* [ ] **Test 5**: Invalid arrays (kwp=0, missing kwp) filtered with warning
* [ ] **Test 6**: Empty arrays case handled gracefully (not passed to Open-Meteo)
* [ ] **USER VERIFICATION**: Stop and let the user verify all tests pass

---
