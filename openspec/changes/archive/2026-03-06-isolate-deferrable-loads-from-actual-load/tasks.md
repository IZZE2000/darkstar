## 1. Core Implementation

- [x] 1.1 Modify `backend/recorder.py` to calculate base load energy: subtract `ev_charging_kwh` and `water_kwh` from `load_kwh` before storing
- [x] 1.2 Add clamping logic to prevent negative base load (max with 0.0)
- [x] 1.3 Add warning log when base load is clamped (similar to existing power snapshot logic)

## 2. Testing

**CRITICAL**: Existing tests all use `water_power: 0.0` and `ev_chargers: []`. New tests MUST:
- Mock `ev_chargers` config with a valid EV charger entity (e.g., `sensor.ev_charger_power`)
- Mock `water_power > 0` in the power sensor responses
- Verify `load_kwh == total_load_delta - ev_kwh - water_kwh` (not just "load_kwh stored")

- [x] 2.1 Add test case: EV charging subtracted from total load
  - Mock `ev_chargers: [{ power_sensor: "sensor.ev_power" }]` in config
  - Mock `sensor.ev_power` returning 4.0 kW, `total_load_consumption` delta = 3.0 kWh
  - Assert `load_kwh == 2.0` (3.0 - 4.0*0.25)
- [x] 2.2 Add test case: Water heating subtracted from total load
  - Mock `water_power` returning 3.0 kW, `total_load_consumption` delta = 2.0 kWh
  - Assert `load_kwh == 1.25` (2.0 - 3.0*0.25)
- [x] 2.3 Add test case: Both EV and water subtracted together
  - Mock EV 4.0 kW, water 3.0 kW, `total_load_consumption` delta = 5.0 kWh
  - Assert `load_kwh == 3.25` (5.0 - 1.0 - 0.75)
- [x] 2.4 Add test case: Negative base load clamped to zero with warning
  - Mock EV 8.0 kW, water 4.0 kW, `total_load_consumption` delta = 2.0 kWh
  - Assert `load_kwh == 0.0` (clamped from -1.0)
  - Assert warning logged about negative base load
- [x] 2.5 Add test case: Power snapshot fallback path still works (no cumulative sensor)
  - Remove `total_load_consumption` from config, mock water_power > 0
  - Verify base load calculated via power snapshot isolation

## 3. Verification

- [x] 3.1 Run `./scripts/lint.sh` - all checks pass
- [x] 3.2 Run recorder tests: `uv run python -m pytest tests/backend/test_recorder_deltas.py -v`
- [x] 3.3 Verify log output shows disaggregation values correctly
