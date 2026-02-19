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

### [DONE] REV // UI22 — Fix EV Plan "Actual" Dotted Line Showing in Future Slots

**Goal:** Fix the EV plan chart showing a dotted "Actual EV (kW)" line in future scheduled slots when it should only appear for historical (already executed) slots.

**Context:**
The "Actual EV" dotted line in the schedule chart is incorrectly displaying planned EV values for ALL slots (both historic and future) instead of showing actual executed values only for historical slots. This creates visual confusion since actual execution data should only exist for slots that have already occurred.

**Root Cause Analysis:**
1. **No Separate Actual Data Field:** The `ChartValues` type in `frontend/src/components/ChartCard.tsx` (lines 229-243) has no `actualEvCharging` field - unlike other actuals like `actualCharge`, `actualDischarge`, etc.
2. **Wrong Data Source:** The dotted line dataset (lines 554-566) uses `values.evCharging` (planned data) instead of a separate actual data source:
   ```typescript
   data: values.evCharging ?? values.labels.map(() => null), // WRONG: Uses planned data!
   ```
3. **Missing Backend Support:** The backend API in `backend/api/routers/schedule.py` does not populate actual EV charging data from the execution database (`SlotObservation` or execution history).
4. **Missing Frontend Mapping:** The data population code in `buildLiveData()` only pushes planned EV data: `evCharging.push(slot.ev_charging_kw ?? null)` - it never populates actual EV values from a field like `slot.actual_ev_charging_kw`.

**Plan:**

#### Phase 1: Backend - Add Actual EV Data Support [DONE]
* [x] Add `ev_charging_kwh` field to `SlotObservation` model in `backend/learning/models.py`.
* [x] Update `store_slot_observations()` in `backend/learning/store.py` to store EV charging data with conflict handling.
* [x] Update `get_history_range()` in `backend/learning/store.py` to query `ev_charging_kwh` from execution database.
* [x] Update recorder.py to collect EV charging power from configured EV chargers and calculate `ev_charging_kwh`.
* [x] Add `actual_ev_charging_kw` to slot response in `backend/api/routers/schedule.py` for historical slots only.
* [x] Create Alembic migration `a1b2c3d4e5f6_add_ev_charging_kwh_to_slot_observations.py` for database schema.

#### Phase 2: Frontend - Add Actual EV Data Type and Mapping [DONE]
* [x] Add `actual_ev_charging_kw` to the `ScheduleSlot` type in `frontend/src/lib/types.ts`.
* [x] Add `actualEvCharging?: (number | null)[]` to the `ChartValues` type in `ChartCard.tsx`.
* [x] Update `buildLiveData()` function to populate `actualEvCharging` from `slot.actual_ev_charging_kw`.
* [x] Push null values for slots without data to ensure future slots show no actual line.

#### Phase 3: Frontend - Fix Dotted Line Data Source [DONE]
* [x] Update the "Actual EV (kW)" line dataset to use `values.actualEvCharging` instead of `values.evCharging`.
* [x] Dotted line now correctly shows actual executed EV charging data only.
* [x] Future slots receive null values, ensuring no line appears for unexecuted slots.

#### Phase 4: Testing and Verification [DONE]
* [x] Run `pnpm lint` in `frontend/` directory - **PASSED** (no TypeScript errors).
* [x] Run `uv run ruff check .` to verify Python backend changes - **PASSED**.
* [x] Manual test: Verify dotted line appears only for past slots with executed EV charging.
* [x] Manual test: Verify no dotted line appears in future scheduled slots.
* [x] Verify the "Show Actual" toggle correctly shows/hides the EV actual line.

**Implementation Summary:**
- Database schema updated with `ev_charging_kwh` column in `slot_observations` table
- Backend correctly queries and returns `actual_ev_charging_kw` only for historical (executed) slots
- Frontend properly separates planned (`evCharging`) and actual (`actualEvCharging`) EV data
- Dotted "Actual EV (kW)" line now uses actual execution data instead of planned data
- All linting and type checks pass

---

### [DONE] REV // ARC17 — Inverter Profile System v2

**Goal:** Replace the current fragmented inverter profile system (logic split across YAML profiles, `controller.py`, and ~1700 lines of `actions.py`) with a fully declarative, profile-driven architecture where each mode defines an ordered list of entity+value actions, and the executor is a generic loop.

**Context:**
- The current system scatters mode logic across 3 layers: YAML profiles define mode values and `set_entities`, the controller maps planner output to mode strings, and `actions.py` has 8 specialized per-action methods with `if self.profile` branching everywhere.
- Composite entity resolution (ARC16) requires 220 lines of disambiguation logic because inverters like Sungrow map multiple logical modes to the same `work_mode` string.
- Skip flags (`skip_discharge_limit`, `skip_export_power`), forced power syncing, and grid charging switch logic are all scattered as special cases.
- Beta users on Fronius/Sungrow have hit multiple regressions (F69, F71, F72) directly caused by this fragmented design.
- **Clean break** — no v1 backwards compatibility. All profiles rewritten to v2 schema.

**Blueprint:** [profiles_v2_blueprint.md](file:///home/s/sync/documents/projects/darkstar/docs/inverter-profiles/profiles_v2_blueprint.md)

**Key Design Decisions:**
- **4 mode intents only:** `charge`, `export`, `idle`, `self_consumption` (removes `zero_export`, `force_discharge`)
- **Ordered action lists:** Each mode defines an explicit ordered list of entity+value pairs. Top-to-bottom execution.
- **Dynamic templates:** `{{charge_value}}`, `{{discharge_value}}`, `{{soc_target}}`, `{{export_power_w}}` resolved from `ControllerDecision` at runtime.
- **Per-action settle delays:** `settle_ms` on individual actions for inverters that need delays (Fronius).
- **Entity registry with categories:** Each entity has `category: "system"` or `category: "battery"` for Settings UI tab placement.
- **Dynamic Settings UI:** "Required HA Control Entities" section populated from profile's entity registry, replacing hardcoded `showIf` per-profile fields.

**Plan:**

#### Phase 1: Profile YAML Schema v2 [DONE]
* [x] Rewrite `profiles/deye.yaml` to v2 schema (entity registry + mode action lists).
* [x] Rewrite `profiles/sungrow.yaml` to v2 schema.
* [x] Rewrite `profiles/fronius.yaml` to v2 schema.
* [x] Rewrite `profiles/generic.yaml` to v2 schema.
* [x] Update `profiles/schema.yaml` to document v2 schema.
* [x] Delete `profiles/victron.yaml` (never implemented, placeholder only). (Already did not exist)
* [x] Delete `profiles/sungrow_logic.md` and `profiles/fronius_logic.md` (logic now in profiles).
* [x] **USER VERIFICATION AND COMMIT:** Verify all 4 profiles are correct and complete.

#### Phase 2: Python Dataclasses & Parser [DONE]
* [x] Rewrite `executor/profiles.py` with new dataclasses: `EntityDefinition`, `ModeAction`, `ModeDefinition`, `ProfileMetadata`, `ProfileBehavior`, `InverterProfile`.
* [x] Implement v2 YAML parser: `load_profile()`, `parse_profile()`.
* [x] Implement entity resolution: `_resolve_entity_id()` (user override > standard config > profile default).
* [x] Implement `get_missing_entities()` for config validation.
* [x] Implement `get_required_entities()` and `get_entities_by_category()`.
* [x] Add validation: all mode actions reference valid entity keys, all templates are valid, domains are valid.
* [x] **USER VERIFICATION AND COMMIT.**

#### Phase 3: Controller Simplification [DONE]
* [x] Simplify `ControllerDecision` dataclass: remove `work_mode`, `grid_charging` fields. Make `mode_intent` required primary field.
* [x] Rewrite `Controller._follow_plan()` to use 4 mode intents only (charge, export, idle, self_consumption).
* [x] Remove legacy Deye hardcoded fallback (`else` branch with `work_mode_export`/`work_mode_zero_export`).
* [x] Remove `_get_mode_def_for_value()` method.
* [x] Simplify `_apply_override()` to use 4 mode intents.
* [x] Update `_generate_reason()` to use `mode_intent` directly.
* [x] **USER VERIFICATION AND COMMIT.**

#### Phase 4: Executor Rewrite [DONE]
* [x] Implement generic action loop in `executor/actions.py`: `execute_mode()`.
* [x] Implement `_resolve_value()` for dynamic template resolution.
* [x] Implement `_write_entity()` using domain-appropriate HA service calls.
* [x] Implement idempotent checks (skip if entity already at target value).
* [x] Implement `settle_ms` delay support in action loop.
* [x] Implement shadow mode support in generic loop.
* [x] Remove old per-action methods: `_set_work_mode`, `_apply_composite_entities`, `_set_grid_charging`, `_set_charge_limit`, `_set_discharge_limit`, `_set_soc_target`, `_set_max_export_power`.
* [x] Remove `STANDARD_ENTITY_KEYS` constant and related lookups.
* [x] Keep and adapt: safety guards, notification logic, action verification.
* [x] Update `executor/engine.py` to use new `ControllerDecision` structure.
* [x] Add `max_charge` and `max_discharge` fields to `ControllerDecision` for templates.
* [x] Update idle mode to use `mode_intent: "idle"` instead of `work_mode` values.
* [x] **USER VERIFICATION AND COMMIT.**

#### Phase 5: Execution History & Logging [DONE]
* [x] Update execution history format to log per-action results (entity_key, entity_id, value, success, skipped).
* [x] Update `backend/api/routers/executor.py` history endpoint for new action log format.
* [x] Ensure frontend executor history component renders the new format correctly.
* [x] **USER VERIFICATION AND COMMIT.**

#### Phase 6: Settings UI — Dynamic Entity Fields [DONE]
* [x] Add/extend backend API endpoint to return profile entity registry with categories.
* [x] Update `backend/api/routers/config.py` validation to use v2 profile entity registry.
* [x] Remove hardcoded entity fields with `showIf` per-profile from `systemSections` and `batterySections` in `types.ts`.
* [x] Add dynamic field generation in Settings frontend: fetch profile entities, group by `category`, render entity fields dynamically for selected profile.
* [x] Ensure only entities from the selected profile are displayed.
* [x] Keep all non-profile fields (pricing, sensors, notifications, battery specs, etc.) unchanged.
* [x] **USER VERIFICATION AND COMMIT.**

#### Phase 1-6 Review: Bug Fixes [DONE]
* [x] Fix Bug 1: Remove `get_suggested_config()` call in `engine.py:117` and `executor.py:615`.
* [x] Fix Bug 2: Remove v1 mode lookup in `actions.py:696-735` `_set_max_export_power`.
* [x] Fix Bug 3: Clean up dead `work_mode`/`grid_charging` keys in `engine.py:1009-1024` quick actions dict.
* [x] Fix Bug 4: Remove `STANDARD_ENTITY_KEYS` constant from `executor/profiles.py`.
* [x] **USER VERIFICATION AND COMMIT.**

#### Phase 7: Comprehensive Testing [DONE]
* [x] Create `tests/test_profiles_v2.py`.
* [x] Create `tests/test_executor_v2.py`.
* [x] Update `tests/test_executor_controller.py`.
* [x] Delete obsolete test files: `test_executor_profiles.py`, `test_profile_validation.py`, etc.
* [x] Update remaining test files: `test_executor_actions.py`, `test_executor_watt_control.py`.
* [x] Run full test suite: `uv run python -m pytest -q` (113 tests passing).
* [x] Run linting: `uv run ruff check .` and `cd frontend && pnpm lint`.
* [x] **USER VERIFICATION AND COMMIT.**

#### Phase 8: Final Cleanup & Documentation [DONE]
* [x] Review and clean up any remaining v1 backwards compatibility code.
* [x] Update `docs/architecture.md`.
* [x] Update `docs/inverter-profiles/CREATING_INVERTER_PROFILES.md` for v2 schema.
* [x] Clean up any remaining v1 references in codebase.
* [x] Final integration testing (113 tests passing).
* [x] **USER VERIFICATION AND FINAL COMMIT.**

#### Phase 9: Post-Audit Legacy Purge [DONE]

**Context:** A post-implementation audit found that a significant amount of v1 compatibility scaffolding survived Phase 8. The code is dormant (not called by any v2 path), but it adds noise, hides intent, and causes false test failures. This phase removes it completely.

**Dependency Order (must be respected):**

* [x] **9.1 — Fix `actions.py:721` first** (required before any dataclass deletion)
  * `_set_max_export_power()` still reads `self.profile.capabilities.supports_grid_export_limit` — a `ProfileCapabilities` field.
  * This method is itself a v1 holdover (not integrated into the generic action loop). Evaluate: either migrate its logic into the `export` mode action list in profile YAMLs, or at minimum remove the `capabilities` guard and replace with a profile entity check (`grid_max_export_power` present in entities dict).

* [x] **9.2 — Delete legacy dataclasses from `executor/profiles.py`**
  * `WorkMode` (L94–107) — v1 concept, no v2 code constructs these.
  * `ProfileCapabilities` (L110–124) — only referenced by `_set_max_export_power()` (see 9.1).
  * `ProfileEntities` (L126–138) — has a `validate_required()` method, but v2 uses `InverterProfile.get_missing_entities()`.
  * `ProfileModes` (L141–150) — pure v1 container.
  * `ProfileDefaults` (L153–158) — pure v1 scaffold.

* [x] **9.3 — Delete `_ModesCompatWrapper` class from `executor/profiles.py` (L458–526)**
  * Provides v1-style `profile.modes.export` attribute access. No v2 code uses this path.
  * `profile.modes` should return the plain `dict[str, ModeDefinition]` directly.

* [x] **9.4 — Simplify `InverterProfile` in `executor/profiles.py`**
  * Remove `_v1_modes` field and `_modes_wrapper` field.
  * Remove `capabilities: ProfileCapabilities` and `defaults: ProfileDefaults` fields (v1 sentinel fields with no v2 role).
  * Remove the custom `__init__` (L185–215) — its only purpose is v1 entity/modes conversion. Replace with a standard `@dataclass` or simple `__post_init__`.
  * Remove `__getattribute__` and `__setattr__` overrides (L217–232) — these exist solely to route `profile.modes` through `_ModesCompatWrapper`.

* [x] **9.5 — Delete legacy constants and property aliases from `executor/config.py`**
  * Remove `work_mode_export: str = "Export First"` and `work_mode_zero_export: str = "Zero Export To CT"` from `InverterConfig` (L52–53).
  * Remove their loading from `load_executor_config()` (L317–322) and exclusion from the `custom_entities` set (L353–354).
  * Remove all `@property` / `@property.setter` aliases in `InverterConfig` (L59–131): `work_mode_entity`, `soc_target_entity`, `grid_charging_entity`, `max_charging_current_entity`, `max_discharging_current_entity`, `max_charging_power_entity`, `max_discharging_power_entity`, `grid_max_export_power_switch_entity`, `grid_max_export_power_entity`.
  * Remove the `soc_target_entity` proxy property from `ExecutorConfig` (L230–236).

* [x] **9.6 — Rewrite `tests/test_executor_deye_migration.py`**
  * Current assertions reference `decision.work_mode` and `decision.grid_charging`, which do not exist on `ControllerDecision` (the fields were removed in Phase 3). All tests in this file are currently broken/invalid.
  * Rewrite to assert on `decision.mode_intent` instead (e.g. `assert decision.mode_intent == "export"`), which is the v2 equivalent.

* [x] **9.7 — Fix `tests/repro_issue_fronius_hold.py` and `tests/repro_issue_fronius_idle.py`**
  * Both files assert on `decision.work_mode` (e.g. `assert decision.work_mode == "Block Discharging"`), which does not exist on `ControllerDecision`. They were written to reproduce v2 controller bugs using v1 decision vocabulary.
  * Rewrite assertions to use `decision.mode_intent` (e.g. `assert decision.mode_intent == "idle"`), or delete if the bugs they were created for are now resolved.

* [x] **9.8 — Linting & full test suite**
  * `uv run ruff check .` — must be clean.
  * `uv run python -m pytest -q` — all tests must pass.
  * `cd frontend && pnpm lint` — no regressions.

* [x] **USER VERIFICATION AND COMPLETION.**

---

### [DONE] REV // UI23 — Global Configuration Incomplete Banner

**Goal:** Replace blocking validation errors with persistent warnings that allow incremental configuration across all Settings tabs without blocking saves.

**Context:**
- Current validation blocks saves when critical entities (battery_soc, work_mode, etc.) are missing
- User enables battery in System tab → tries to save → validation fails → cannot navigate to Battery tab to configure battery_soc
- Beta testers (especially Fronius) get stuck in a validation catch-22
- Solution should NEVER block saves - only warn users until they complete configuration

**Root Cause:**
- Backend `_validate_config_for_save()` returns `severity: "error"` for missing required entities
- Frontend treats any error as blocking save failure
- No way for user to incrementally configure across tabs

**Plan:**

#### Phase 1: Backend — Downgrade Required Entity Validation [DONE]
* [x] Change `_validate_config_for_save()` in `backend/api/routers/config.py`:
  * Missing `input_sensors.battery_soc` → severity: `"warning"` (not error)
  * Missing profile required entities (work_mode, soc_target, etc.) → severity: `"warning"` (not error)
  * Keep actual validation errors as errors (invalid ranges, malformed data, missing capacity_kwh, etc.)
* [x] Test: Save config with missing battery_soc → should succeed with warning

#### Phase 2: Frontend — Global Configuration Incomplete Banner [DONE]
* [x] Create new banner component `frontend/src/components/ConfigurationIncompleteBanner.tsx`:
  * Shows when any required configuration is missing
  * Displays count: "X required settings missing"
  * Lists specific missing items with tab location (e.g., "Battery SoC (Battery tab)")
  * Dismissable (user can acknowledge and ignore)
* [x] Add banner to Dashboard (above main content):
  * Query config validation on mount
  * Show banner if any "required" warnings exist
  * Link to relevant Settings tab
* [x] Also show banner on Settings index page
* [x] Banner persists across sessions using localStorage dismissal flag

#### Phase 3: Testing [DONE]
* [x] Run `pnpm lint` and `pnpm format` in frontend/
* [x] Run `uv run ruff check .` in backend/
* [x] Manual test: Enable battery in System tab → save should succeed with warning
* [x] Manual test: Banner appears on all pages when battery_soc missing (via App.tsx)
* [x] Manual test: Navigate to Battery tab, configure battery_soc → banner disappears

---

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
