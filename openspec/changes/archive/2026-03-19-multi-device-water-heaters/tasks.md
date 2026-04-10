## 1. Solver Types & Adapter

- [x] 1.1 Create `WaterHeaterInput` dataclass in `planner/solver/types.py` with fields: `id: str`, `power_kw: float`, `min_kwh_per_day: float`, `max_hours_between_heating: float`, `min_spacing_hours: float`, `force_on_slots: list[int] | None = None`, `heated_today_kwh: float = 0.0`.
- [x] 1.2 Replace scalar water fields in `KeplerConfig` with `water_heaters: list[WaterHeaterInput]`. Remove `water_heating_power_kw`, `water_heating_min_kwh`, `water_min_spacing_hours`, `water_heated_today_kwh`, `force_water_on_slots`. Keep global fields: `water_heating_max_gap_hours`, `water_comfort_penalty_sek`, `water_block_penalty_sek`, `water_reliability_penalty_sek`, `max_block_hours`, `water_block_start_penalty_sek`, `defer_up_to_hours`.
- [x] 1.3 Add per-device water output to `KeplerResultSlot`: add `water_heater_results: dict[str, float]` (heater_id → kW) alongside existing aggregate `water_heat_kw` for compat.
- [x] 1.4 Replace `_aggregate_water_heaters()` in `planner/solver/adapter.py` with per-device config builder that creates `WaterHeaterInput` list from `water_heaters[]` config entries. Each enabled heater with `power_kw > 0` gets its own `WaterHeaterInput`.
- [x] 1.5 Update `config_to_kepler_config()` to populate `KeplerConfig.water_heaters` list instead of scalar fields. Pass global water settings (comfort penalties, block penalties, reliability penalty, deferral, max block hours) as scalar `KeplerConfig` fields.
- [x] 1.6 Write tests for adapter: verify per-device configs built correctly, disabled heaters excluded, empty array produces empty list, global settings still passed as scalars.

## 2. Kepler MILP Solver

- [x] 2.1 Refactor water heater variable creation in `kepler.py`: create `water_heat[d][t]` (binary) indexed by device ID and time slot. Only create for enabled heaters with `power_kw > 0`. Replace `water_enabled` boolean with check on `len(config.water_heaters) > 0`.
- [x] 2.2 Refactor `water_start[d][t]` (binary) creation: create per-device, only when spacing or block_start_penalty is enabled. Use same `needs_water_start` logic but per device.
- [x] 2.3 Update energy balance constraint: replace `water_heat[t] * config.water_heating_power_kw * h` with `sum(water_heat[d][t] * heater.power_kw * h for d, heater in water_heaters)`.
- [x] 2.4 Update per-day daily minimum constraint: for each heater `d` and each day, `sum(water_heat[d][t] for t in day_slots) * kwh_per_slot[d] >= min_kwh[d] - heated_today[d] - violation[d][day]`. Note: `kwh_per_slot` is now per-device since power differs.
- [x] 2.5 Update block duration constraint (sliding window): for each heater `d`, `sum(water_heat[d][t:t+window]) <= max_block_slots + overshoot[d][t]`. Window size from global `max_block_hours`.
- [x] 2.6 Update spacing constraint: for each heater `d`, use that heater's `min_spacing_hours`. Hard constraint: `sum(water_heat[d][j] for j in range(start, t)) + water_start[d][t] * M <= M`.
- [x] 2.7 Update block start detection: for each heater `d`, `water_start[d][0] == water_heat[d][0]` and `water_start[d][t] >= water_heat[d][t] - water_heat[d][t-1]` for t > 0.
- [x] 2.8 Update mid-block locking: for each heater `d`, if `heater.force_on_slots` is set, `water_heat[d][t_idx] == 1` for each index in that heater's `force_on_slots`.
- [x] 2.9 Update objective function: sum block overshoot penalty across all devices `sum(overshoot[d][t] * block_penalty for d, t)`. Sum block start penalty across all devices `sum(water_start[d][t] * start_penalty for d, t)`. Sum reliability penalty across all devices `sum(violation[d][day] * reliability_penalty for d, day)`. Add per-device symmetry breaker `sum(water_heat[d][t] * t * 1e-5 for d, t)`.
- [x] 2.10 Update result extraction: build `water_heater_results` dict from per-device `water_heat[d][t]` values. For each heater, if `water_heat[d][t] > 0.5`, result is `heater.power_kw`, else `0.0`. Set `water_heat_kw` to sum of all heaters for backward compat.
- [x] 2.11 Update `water_min_kwh_violation` slack variables to be per-device: `water_min_kwh_violation[d][day]` indexed by device and day.
- [x] 2.12 Update `block_overshoot` slack variables to be per-device: `block_overshoot[d][t]` indexed by device and time slot.
- [x] 2.13 Write solver tests: single heater equivalence with current system, two heaters with different power ratings get independent schedules, two heaters competing for grid budget get staggered, disabled heater gets no variables, empty heater list equals no water constraints, per-device spacing works independently.

## 3. Pipeline

- [x] 3.1 Update mid-block detection in `pipeline.py` to be per-device: for each enabled heater, check if the previous schedule has that specific heater active (from `water_heaters` dict in schedule slot). Build per-heater `force_on_slots` lists.
- [x] 3.2 Update `water_heated_today_kwh` tracking to be per-device: fetch each heater's daily energy from HA sensor or recorder state. Pass per-device values in each `WaterHeaterInput.heated_today_kwh`.
- [x] 3.3 Update `config_to_kepler_config()` call to pass `water_heaters` list instead of aggregated scalars. Remove `force_water_on_slots` parameter — it's now per-device in `WaterHeaterInput`.
- [x] 3.4 Update the "disable water heating if no water heater" logic to clear the `water_heaters` list instead of zeroing scalar fields.
- [x] 3.5 Write pipeline tests: per-device mid-block detection from previous schedule, per-device today's energy tracking, fallback when previous schedule has old format (no `water_heaters` dict).

## 4. Schedule Output

- [x] 4.1 Update `planner/output/formatter.py` to include `water_heaters` dict in each schedule slot alongside aggregate `water_heating_kw`. Read from `KeplerResultSlot.water_heater_results`.
- [x] 4.2 Update `planner/output/soc_target.py` to handle per-device water data: the SoC target calculation currently reads `water_heating_kw` — ensure it continues to use the aggregate.
- [x] 4.3 Write tests: verify schedule output contains per-device breakdown and correct aggregate, verify backward compat with consumers that only read `water_heating_kw`.

## 5. Executor Config

- [x] 5.1 Create `WaterHeaterDeviceConfig` dataclass in `executor/config.py` with fields: `id: str`, `name: str`, `target_entity: str | None = None`, `power_kw: float = 3.0`.
- [x] 5.2 Rename `WaterHeaterConfig` to `WaterHeaterGlobalConfig` (keeps `temp_normal`, `temp_off`, `temp_boost`, `temp_max`). Add `water_heater_devices: list[WaterHeaterDeviceConfig]` to `ExecutorConfig`.
- [x] 5.3 Update `load_executor_config()`: build `water_heater_devices` list from `water_heaters[]` entries (each enabled heater with `target_entity` gets a `WaterHeaterDeviceConfig`). Keep global temp loading from `executor.water_heater`.
- [x] 5.4 Write tests for executor config: verify per-device configs built from array, heaters without target_entity excluded, global temps still loaded.

## 6. Executor SlotPlan & Controller

- [x] 6.1 Add `water_heater_plans: dict[str, float]` to `SlotPlan` in `executor/override.py`. Default to empty dict. Update slot loading to parse per-device water data from schedule's `water_heaters` dict.
- [x] 6.2 Add fallback in slot loading: if schedule slot has `water_heating_kw` but no `water_heaters` dict (old format), set `water_kw` from aggregate and leave `water_heater_plans` empty (single-heater fallback).
- [x] 6.3 Add `water_temps: dict[str, int]` to `ControllerDecision` in `executor/controller.py`. Default to empty dict.
- [x] 6.4 Update controller `decide()` to populate `water_temps` from `SlotPlan.water_heater_plans`: for each heater, if planned kW > 0 set to `temp_normal`, else `temp_off`. Keep scalar `water_temp` as max of all per-device temps for backward compat.
- [x] 6.5 Write tests: SlotPlan parses per-device water data, old-format fallback works, controller produces per-device water temps.

## 7. Executor Engine & Actions

- [x] 7.1 Update `set_water_temp()` in `executor/actions.py` to accept a `target_entity` parameter instead of reading from `self.config.water_heater.target_entity`. Use the passed entity for the HA call. Keep `self.config.water_heater` (now `WaterHeaterGlobalConfig`) for temp thresholds only.
- [x] 7.2 Refactor water heater control in `executor/engine.py` `_tick()`: replace single `set_water_temp(decision.water_temp)` call with a loop over `decision.water_temps.items()`. For each heater ID, look up `target_entity` from `WaterHeaterDeviceConfig`, call `set_water_temp(target_entity, temp)`.
- [x] 7.3 Handle edge case: if `water_temps` is empty (old-format schedule or single heater fallback), fall back to single `set_water_temp(global_config.target_entity, decision.water_temp)` for backward compat.
- [x] 7.4 Update execution record to include `water_heater_plans` dict in addition to aggregate `water_kw`.
- [x] 7.5 Update `get_status()` to include per-device water heater plan in `current_slot_plan`.
- [x] 7.6 Write executor tests: per-device temperature control, each heater gets independent HA call, old-format schedule fallback, action results logged per heater with entity IDs.

## 8. Energy Recording

- [x] 8.1 Update `backend/recorder.py` to track per-device water energy: build a `water_heater_energy: dict[str, float]` keyed by heater ID alongside aggregate `water_kwh`.
- [x] 8.2 Store `water_heater_energy` dict in slot observation (as JSON field or in metadata).
- [x] 8.3 Maintain aggregate `water_kwh` as sum across heaters for backward compatibility.
- [x] 8.4 Write tests: per-device water recording, aggregate still correct, fallback to snapshot per device, empty dict when no heaters active.

## 9. Frontend Settings

- [x] 9.1 Review `waterSections` in `frontend/src/pages/settings/types.ts`: verify water heater entity array already has correct per-device fields (`target_entity`, `power_kw`, `min_kwh_per_day`, timing settings). No orphan sections to remove (Scheduling and Temperatures correctly reference global paths).
- [x] 9.2 If `target_entity` is not visible in the entity card editor, add it to the entity card fields in `EntityArrayEditor` component for water heaters.
- [x] 9.3 Verify settings save/load round-trip with per-device fields.

## 10. Remove `nominal_power_kw` from Water Heaters

- [x] 10.1 Remove `nominal_power_kw` field from the water heater entity card in `EntityArrayEditor.tsx` (the `isWaterHeater` block around line 568). Remove the corresponding default value from the water heater defaults object and the `WaterHeaterEntity` interface.
- [x] 10.2 Remove `nominal_power_kw` from the `WaterHeater` type in `frontend/src/lib/api.ts`.
- [x] 10.3 Update `backend/loads/service.py` water heater initialisation: replace `wh.get("nominal_power_kw", wh.get("power_kw", 0.0))` with `wh.get("power_kw", 0.0)` directly — `power_kw` is already the canonical field.
- [x] 10.4 Remove `nominal_power_kw` from `config.default.yaml` water heater entries and example comments.
- [x] 10.5 Update `tests/config/test_config_validation.py` to drop `nominal_power_kw` from water heater fixture dicts.
- [x] 10.6 Verify nothing else reads `nominal_power_kw` for water heaters (`grep -r nominal_power_kw` should only show EV charger / generic load paths, not water heater paths).

## 11. Integration & Validation

- [x] 11.1 Run full test suite and fix any regressions from KeplerConfig changes, KeplerResultSlot changes, SlotPlan changes, or executor config changes.
- [x] 11.2 Manual end-to-end test: configure two water heaters with different power ratings and daily minimums, verify schedule shows per-device plans, verify executor controls both target entities independently.
- [x] 11.3 Verify SoC target calculation, chart display, and status API all work with per-device water data (they should read aggregate `water_heating_kw` which is preserved).
