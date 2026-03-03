## 1. Schema & Configuration

- [x] 1.1 Update `config.default.yaml` to include optional energy sensor keys under `input_sensors`.
- [x] 1.2 Update any relevant schema validation in `backend/api/routers/config.py` (if applicable).

## 2. Recorder Persistence

- [x] 2.1 Implement `RecorderStateStore` class in `backend/recorder.py` to manage JSON persistence.
- [x] 2.2 Add methods to `RecorderStateStore` for `load()`, `save()`, and `get_delta()`.

## 3. Core Logic Implementation

- [x] 3.1 Update `record_observation_from_current_state` to fetch cumulative energy sensors from HA.
- [x] 3.2 Implement delta-based calculation for `pv_kwh`, `load_kwh`, `import_kwh`, and `export_kwh`.
- [x] 3.3 Implement fallback to power-snapshots when energy sensors or previous state are missing.
- [x] 3.4 Handle meter reset/rollover logic (fallback to snapshot if delta is negative).

## 4. Testing & Verification

- [x] 4.1 Create `tests/backend/test_recorder_deltas.py` to verify delta logic and persistence.
- [x] 4.2 Test the power-snapshot fallback mechanism.
- [x] 4.3 Verify a manual run of `recorder.py` correctly updates the state file and database.
