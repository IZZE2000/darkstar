## 1. Validation Utility

- [x] 1.1 Create `backend/validation.py` with `get_max_energy_per_slot(config: dict) -> float` function
- [x] 1.2 Add unit tests for `get_max_energy_per_slot` with various config scenarios
- [x] 1.3 Add `validate_energy_values(record: dict, max_kwh: float) -> dict` function that zeroes spikes
- [x] 1.4 Add unit tests for `validate_energy_values` function

## 2. Recorder Integration

- [x] 2.1 Import validation functions in `backend/recorder.py`
- [x] 2.2 Call `validate_energy_values` before `store.store_slot_observations` in `record_observation_from_current_state`
- [x] 2.3 Add integration test for recorder spike handling (covered by TestRecorderSpikeValidation in test_recorder_deltas.py)

## 3. Learning Engine Fix

- [x] 3.1 Update `backend/learning/engine.py` to import `get_max_energy_per_slot`
- [x] 3.2 Replace hardcoded `50.0` threshold in `etl_cumulative_to_slots` with config-derived value
- [x] 3.3 Add test for learning engine spike filtering with config-derived threshold
- [x] 3.4 Apply same spike filtering in `etl_power_to_slots` (power-sensor backfill path) and add corresponding test

## 4. Pipeline Hardening (existing data)

- [x] 4.1 Add spike filter to `Analyst._fetch_observations` — drop rows where `load_kwh` or `pv_kwh` exceeds threshold before bias calculation
- [x] 4.2 Add spike filter to `LearningStore.get_forecast_vs_actual` — add `WHERE actual_col <= max_kwh` to query so Reflex accuracy analysis excludes corrupted rows
- [x] 4.3 Add spike filter to `LearningStore.calculate_metrics` — exclude rows with spiked `pv_kwh` or `load_kwh` from MAE calculations
- [x] 4.4 Add tests for each hardened read path confirming spike rows are excluded

## 5. Verification

- [x] 5.1 Run full test suite to ensure no regressions
- [~] 5.2 Manual test: inject spike value via HA, verify it is zeroed in recorder and excluded from all pipeline reads (requires live HA environment)
- [x] 5.3 Run linting and type checking
