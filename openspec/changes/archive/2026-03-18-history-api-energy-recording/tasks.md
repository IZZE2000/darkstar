## 1. Generic Power History Function

- [x] 1.1 Add `get_energy_from_power_history(entity_id, start, end) -> float | None` to `backend/core/ha_client.py`. Fetch `/api/history/period/{start}?filter_entity_id={entity}&end_time={end}`. Filter out "unknown", "unavailable", and non-numeric states. Detect `unit_of_measurement` from the first valid state's attributes and normalize W/kW/MW. Compute `mean(kw_values) × duration_hours`. Return `None` on empty data. Use 10-15s timeout. Catch all exceptions, return `None`, log warning. No internal retry.
- [x] 1.2 Add unit tests for `get_energy_from_power_history`. Test cases: normal data (15 points averaging 5kW → 1.25kWh), sparse data (3 points), empty response → `None`, HTTP timeout → `None`, connection error → `None`, W→kW normalization, mixed numeric/"unavailable" states filtered, all-unavailable → `None`.

## 2. Remove Cumulative Energy Sensor Code from Recorder

- [x] 2.1 Remove `ev_charger_energy_sensors` collection loop from `backend/recorder.py` (lines ~323-338 where it iterates `ev_chargers` and extracts `energy_sensor`)
- [x] 2.2 Remove `water_heater_energy_sensors` collection loop from `backend/recorder.py` (lines ~304-316 where it iterates `water_heaters` and extracts `energy_sensor`)
- [x] 2.3 Remove the cumulative EV energy calculation block in `backend/recorder.py` (lines ~466-506, the `if ev_charger_energy_sensors:` branch and its delta logic)
- [x] 2.4 Remove the cumulative water energy calculation block in `backend/recorder.py` (lines ~508-534, the `if water_heater_energy_sensors:` branch and its delta logic)

## 3. Add Power History Recording for EV and Water

- [x] 3.1 Add EV energy calculation using `get_energy_from_power_history` in `backend/recorder.py`. For each enabled EV charger, call the function with the charger's `sensor` entity and the slot window (slot_start, slot_end). If it returns `None`, fall back to `power_kw × 0.25` from the already-fetched power reading. Sum across all chargers.
- [x] 3.2 Add water heater energy calculation using `get_energy_from_power_history` in `backend/recorder.py`. Same approach as 3.1 but for water heaters.
- [x] 3.3 Update load isolation logic in `backend/recorder.py` (lines ~536-546). Remove the `if used_cumulative_load:` condition. Always subtract EV and water energy from total load when non-zero.

## 4. Update Recorder Tests

- [x] 4.1 Remove these tests from `tests/backend/test_recorder_deltas.py`: `test_ev_energy_sensor_cumulative_delta`, `test_water_energy_sensor_cumulative_delta`, `test_energy_sensor_fallback_to_snapshot_when_no_prior_state`
- [x] 4.2 Add recorder tests for EV power history recording: mock `get_energy_from_power_history` to return a value, verify `ev_charging_kwh` is set correctly. Test multiple chargers summing.
- [x] 4.3 Add recorder tests for water heater power history recording: same approach as 4.2
- [x] 4.4 Add recorder test for snapshot fallback: mock `get_energy_from_power_history` to return `None`, verify recorder uses `power_kw × 0.25`
- [x] 4.5 Add recorder test for load isolation: verify EV + water energy is always subtracted from total load regardless of source (history or snapshot)

## 5. Backfill Engine

- [x] 5.1 Remove the water heater `energy_sensor` lookup in `backend/learning/backfill.py` (lines ~151-158, the loop that iterates `water_heaters` and adds `energy_sensor` to `raw_map`)
- [x] 5.2 Update backfill tests if any reference water heater energy_sensor handling

## 6. Config Changes

- [x] 6.1 Remove `energy_sensor: ''` from `ev_chargers[]` items in `config.default.yaml` (line ~129 and any commented examples)
- [x] 6.2 Remove `energy_sensor: ''` from `water_heaters[]` items in `config.default.yaml` (line ~99 and any commented examples)
- [x] 6.3 Add config migration step in `backend/config_migration.py` that removes the `energy_sensor` key from all items in `ev_chargers[]` and `water_heaters[]` arrays if present
- [x] 6.4 Add test for the new config migration: verify `energy_sensor` is removed from both arrays, verify other fields are untouched, verify migration is idempotent (no error if field already absent)

## 7. Health Checks

- [x] 7.1 Remove the EV charger `energy_sensor` missing warning from `backend/health.py` (lines ~406-413)
- [x] 7.2 Remove the water heater `energy_sensor` missing warning from `backend/health.py` (lines ~420-427)
- [x] 7.3 Update health check tests if any assert on energy_sensor warnings

## 8. Frontend

- [x] 8.1 Remove `energy_sensor: string` from `WaterHeaterEntity` interface in `frontend/src/pages/settings/components/EntityArrayEditor.tsx` (line ~21)
- [x] 8.2 Remove `energy_sensor: string` from `EVChargerEntity` interface in `EntityArrayEditor.tsx` (line ~35)
- [x] 8.3 Remove `energy_sensor: ''` from the default water heater entity object in `EntityArrayEditor.tsx` (line ~63)
- [x] 8.4 Remove `energy_sensor: ''` from the default EV charger entity object in `EntityArrayEditor.tsx` (line ~76)
- [x] 8.5 Remove the `energy_sensor` UI input field for water heaters in `EntityArrayEditor.tsx` (around lines ~312-315)
- [x] 8.6 Remove the `energy_sensor` UI input field for EV chargers in `EntityArrayEditor.tsx` (around lines ~385-390)
- [x] 8.7 Search for any other frontend references to `energy_sensor` for EV/water and remove them

## 9. Documentation

- [x] 9.1 Update `docs/ARCHITECTURE.md` section 5.5 — in the ASCII diagram, change the flow to show "Power HA Sensors → HA History API (avg power) → SlotObservation" for EV/water instead of "Cumulative HA Sensors → Recorder (15-min deltas)"

## 10. Verification

- [x] 10.1 Run full test suite (`pytest`) and fix any breakage from removed `energy_sensor` references
- [x] 10.2 Grep codebase for remaining references to `energy_sensor` in EV/water contexts and clean up any stragglers
