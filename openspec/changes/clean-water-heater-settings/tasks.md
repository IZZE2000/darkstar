## 1. Config Schema — `config.default.yaml`

- [x] 1.1 Add `target_entity: ""` field to the `water_heaters[0]` item (after `energy_sensor`)
- [x] 1.2 Add `target_entity` to the commented-out example second heater
- [x] 1.3 Remove `water_power` key from the `input_sensors:` section
- [x] 1.4 Remove `water_heater_consumption` key from the `input_sensors:` section
- [x] 1.5 Remove `target_entity` key from the `executor.water_heater:` section (keep `temp_off`, `temp_normal`, `temp_boost`, `temp_max`)

## 2. Config Migration — `backend/config_migration.py`

- [x] 2.1 Add migration function `_migrate_water_heater_fields(config)` that: (a) copies `input_sensors.water_power` → `water_heaters[0].sensor` if `sensor` is empty, (b) copies `input_sensors.water_heater_consumption` → `water_heaters[0].energy_sensor` if `energy_sensor` is empty, (c) copies `executor.water_heater.target_entity` → `water_heaters[0].target_entity` if `target_entity` is missing/empty, (d) deletes the three source keys after copying
- [x] 2.2 Call `_migrate_water_heater_fields` in `migrate_config()` after `remove_deprecated_keys` and before template merge
- [x] 2.3 Add unit test: legacy config with all three keys → values migrate into `water_heaters[0]`, old keys removed
- [x] 2.4 Add unit test: config with `sensor` already set → `input_sensors.water_power` is NOT copied (existing value preserved), old key still removed

## 3. Backend — Executor reads from array

- [x] 3.1 In `executor/config.py`: change `WaterHeaterConfig` loading (around line 281) to read `target_entity` from the first enabled `water_heaters[]` item with a non-empty `target_entity`, instead of from `executor_data["water_heater"]["target_entity"]`
- [x] 3.2 In `executor/engine.py` `_collect_metrics` (around line 384): replace `input_sensors.get("water_power")` with reading `sensor` from the first enabled `water_heaters[]` item. Sum across all enabled heaters with a configured `sensor`.
- [x] 3.3 Verify all other `self.config.water_heater.target_entity` references in `executor/engine.py` still work (they read from `WaterHeaterConfig` which is now array-sourced — no code changes needed, just verify)

## 4. Backend — Recorder, HA Socket, HA Client

- [x] 4.1 In `backend/recorder.py` (around line 300): replace the `water_power` read from `input_sensors` with reading `sensor` from enabled `water_heaters[]` items and summing
- [x] 4.2 In `backend/ha_socket.py` (around line 110): replace `sensors["water_power"]` mapping with reading `sensor` from enabled `water_heaters[]` items
- [x] 4.3 In `backend/core/ha_client.py` (around line 237): replace `input_sensors.get("water_heater_consumption")` with reading `energy_sensor` from enabled `water_heaters[]` items and summing
- [x] 4.4 In `backend/learning/backfill.py` (around line 144): replace `water_heater_consumption` reference with reading `energy_sensor` from `water_heaters[]`

## 5. Backend — Health Checks

- [x] 5.1 In `backend/health.py` (around line 560): remove `water_power` and `water_heater_consumption` from the `input_sensors` required-key check
- [x] 5.2 Add per-heater health check: for each enabled `water_heaters[]` item, warn if `sensor` is empty

## 6. Frontend — Settings UI

- [x] 6.1 In `frontend/src/pages/settings/types.ts`: delete the "HA Sensors" section (lines ~1093-1112) from `waterSections`
- [x] 6.2 In `frontend/src/pages/settings/types.ts`: delete the "Control" section (lines ~1113-1125) from `waterSections`
- [x] 6.3 In `frontend/src/pages/settings/components/EntityArrayEditor.tsx`: add `target_entity` to the `WaterHeaterEntity` interface
- [x] 6.4 In `EntityArrayEditor.tsx`: add a `target_entity` entity-picker field inside the water heater accordion item (after the existing sensor fields)
- [x] 6.5 In `EntityArrayEditor.tsx`: add `target_entity` to the water heater default values object

## 7. Tests — Update Existing

- [x] 7.1 Update `tests/test_inputs_ha_client.py`: fixture configs use `water_heaters[].energy_sensor` instead of `input_sensors.water_heater_consumption`
- [x] 7.2 Update `tests/backend/test_recorder_deltas.py`: fixture configs use `water_heaters[].sensor` instead of `input_sensors.water_power`
- [x] 7.3 Update `tests/planner/test_load_disaggregation.py` if it references `input_sensors.water_power`
- [x] 7.4 Run full test suite, fix any remaining references to the removed config keys
