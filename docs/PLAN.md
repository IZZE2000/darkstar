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

### [DRAFT] REV // UI22 — Fix EV Plan "Actual" Dotted Line Showing in Future Slots

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

#### Phase 1: Backend - Add Actual EV Data Support [DRAFT]
* [ ] Add `actual_ev_charging_kw` field to slot response in `backend/api/routers/schedule.py`.
* [ ] Query execution database (LearningStore) for actual EV charging values from `SlotObservation` or execution history.
* [ ] Only populate `actual_ev_charging_kw` for historical slots where `is_executed=true`.
* [ ] Return `null` for future slots to ensure no actual data leaks into future periods.

#### Phase 2: Frontend - Add Actual EV Data Type and Mapping [DRAFT]
* [ ] Add `actualEvCharging?: (number | null)[]` to the `ChartValues` type in `ChartCard.tsx`.
* [ ] Update `buildLiveData()` function to populate `actualEvCharging` from `slot.actual_ev_charging_kw`.
* [ ] Ensure actual data is only pushed for historical slots (check `is_executed` flag).

#### Phase 3: Frontend - Fix Dotted Line Data Source [DRAFT]
* [ ] Update the "Actual EV (kW)" line dataset (lines 554-566) to use `values.actualEvCharging` instead of `values.evCharging`.
* [ ] Verify the dotted line only appears for historical slots with actual data.
* [ ] Ensure the line is hidden (null values) for future slots.

#### Phase 4: Testing and Verification [DRAFT]
* [ ] Run `pnpm lint` in `frontend/` directory to verify no TypeScript errors.
* [ ] Run `uv run ruff check .` to verify Python backend changes.
* [ ] Manual test: Verify dotted line appears only for past slots with executed EV charging.
* [ ] Manual test: Verify no dotted line appears in future scheduled slots.
* [ ] Verify the "Show Actual" toggle correctly shows/hides the EV actual line.

---

### [IN PROGRESS] REV // ARC17 — Inverter Profile System v2 (Declarative Mode-Action Architecture)

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
* [ ] **USER VERIFICATION AND COMMIT:** Verify all 4 profiles are correct and complete.

#### Phase 2: Python Dataclasses & Parser [PLANNED]
* [ ] Rewrite `executor/profiles.py` with new dataclasses: `EntityDefinition`, `ModeAction`, `ModeDefinition`, `ProfileMetadata`, `ProfileBehavior`, `InverterProfile`.
* [ ] Implement v2 YAML parser: `load_profile()`, `parse_profile()`.
* [ ] Implement entity resolution: `_resolve_entity_id()` (user override > standard config > profile default).
* [ ] Implement `get_missing_entities()` for config validation.
* [ ] Implement `get_required_entities()` and `get_entities_by_category()`.
* [ ] Add validation: all mode actions reference valid entity keys, all templates are valid, domains are valid.
* [ ] **USER VERIFICATION AND COMMIT.**

#### Phase 3: Controller Simplification [PLANNED]
* [ ] Simplify `ControllerDecision` dataclass: remove `work_mode`, `grid_charging` fields. Make `mode_intent` required primary field.
* [ ] Rewrite `Controller._follow_plan()` to use 4 mode intents only (charge, export, idle, self_consumption).
* [ ] Remove legacy Deye hardcoded fallback (`else` branch with `work_mode_export`/`work_mode_zero_export`).
* [ ] Remove `_get_mode_def_for_value()` method.
* [ ] Simplify `_apply_override()` to use 4 mode intents.
* [ ] Update `_generate_reason()` to use `mode_intent` directly.
* [ ] **USER VERIFICATION AND COMMIT.**

#### Phase 4: Executor Rewrite [PLANNED]
* [ ] Implement generic action loop in `executor/actions.py`: `execute_mode()`.
* [ ] Implement `_resolve_value()` for dynamic template resolution.
* [ ] Implement `_write_entity()` using domain-appropriate HA service calls.
* [ ] Implement idempotent checks (skip if entity already at target value).
* [ ] Implement `settle_ms` delay support.
* [ ] Implement shadow mode support in generic loop.
* [ ] Remove old per-action methods: `_set_work_mode`, `_apply_composite_entities`, `_set_grid_charging`, `_set_charge_limit`, `_set_discharge_limit`, `_set_soc_target`, `_set_max_export_power`.
* [ ] Remove `STANDARD_ENTITY_KEYS` constant and related lookups.
* [ ] Keep and adapt: safety guards, notification logic, action verification.
* [ ] Update `executor/engine.py` to use new `ControllerDecision` structure.
* [ ] Update `executor/override.py` override actions to use 4 mode intents.
* [ ] Update `executor/config.py` to simplify entity loading.
* [ ] **USER VERIFICATION AND COMMIT.**

#### Phase 5: Execution History & Logging [PLANNED]
* [ ] Update execution history format to log per-action results (entity_key, entity_id, value, success, skipped).
* [ ] Update `backend/api/routers/executor.py` history endpoint for new action log format.
* [ ] Ensure frontend executor history component renders the new format correctly.
* [ ] **USER VERIFICATION AND COMMIT.**

#### Phase 6: Settings UI — Dynamic Entity Fields [PLANNED]
* [ ] Add/extend backend API endpoint to return profile entity registry with categories.
* [ ] Update `backend/api/routers/config.py` validation to use v2 profile entity registry.
* [ ] Remove hardcoded entity fields with `showIf` per-profile from `systemSections` and `batterySections` in `types.ts`.
* [ ] Add dynamic field generation in Settings frontend: fetch profile entities, group by `category`, render entity fields dynamically for selected profile.
* [ ] Ensure only entities from the selected profile are displayed.
* [ ] Keep all non-profile fields (pricing, sensors, notifications, battery specs, etc.) unchanged.
* [ ] **USER VERIFICATION AND COMMIT.**

#### Phase 7: Comprehensive Testing [PLANNED]
* [ ] Create `tests/test_profiles_v2.py` with parametrized tests over ALL profiles:
    - All profiles load successfully (schema_version == 2).
    - All profiles have 4 required modes (charge, export, self_consumption, idle).
    - All mode actions reference valid entity keys.
    - All dynamic templates are valid (`{{charge_value}}`, etc.).
    - All entity domains are valid (select, number, switch, input_number).
    - All entity categories are valid (system, battery).
    - Profile roundtrip (YAML → dataclass → validation).
* [ ] Create `tests/test_executor_v2.py`:
    - Execute mode writes all actions in order.
    - Idempotent skip when entity already at target.
    - Dynamic template resolution.
    - Action ordering preserved.
    - Settle delay applied.
    - Shadow mode logs without writing.
    - Entity resolution order (user override > standard config > profile default).
* [ ] Update `tests/test_executor_controller.py`:
    - 4-mode selection (charge, export, idle, self_consumption) with parametrized inputs.
    - Override mode mapping.
* [ ] Delete obsolete test files: `test_executor_profiles.py`, `test_profile_validation.py`, `test_executor_fronius_profile.py`, `test_executor_composite_mode.py`.
* [ ] Update remaining test files: `test_executor_actions.py`, `test_executor_watt_control.py`.
* [ ] Run full test suite: `uv run python -m pytest -q`.
* [ ] Run linting: `uv run ruff check .` and `cd frontend && pnpm lint`.
* [ ] **USER VERIFICATION AND COMMIT.**

#### Phase 8: Final Cleanup & Documentation [PLANNED]
* [ ] Update `docs/architecture.md` (if it covers executor/profiles).
* [ ] Update `docs/inverter-profiles/CREATING_INVERTER_PROFILES.md` for v2 schema.
* [ ] Clean up any remaining v1 references in codebase.
* [ ] Final full test suite run.
* [ ] **USER VERIFICATION AND FINAL COMMIT.**

---
