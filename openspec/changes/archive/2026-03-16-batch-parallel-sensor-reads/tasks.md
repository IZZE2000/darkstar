## 1. Create Batch Helper Function

- [x] 1.1 Create `gather_sensor_reads()` helper in `backend/core/ha_client.py` with signature:
  ```python
  async def gather_sensor_reads(
      reads: list[tuple[str, Callable[[], Coroutine]]],
      context: str = "sensor_batch"
  ) -> dict[str, Any]
  ```
- [x] 1.2 Implement `return_exceptions=True` handling to catch individual failures
- [x] 1.3 Add context-aware logging for failed sensors (see `backend/health.py:686` for existing pattern)
- [x] 1.4 Write unit tests for `gather_sensor_reads()` covering:
  - All sensors succeed
  - Partial failures (some sensors unavailable)
  - All sensors fail
  - Proper logging output

## 2. Refactor Executor State Gathering

- [x] 2.1 Modify `_gather_system_state()` in `executor/engine.py` (~line 1476) to use batch helper
- [x] 2.2 Group independent sensor reads: SoC, PV power, load power, import, export, work mode, grid charging, water temp, manual override (9 reads)
- [x] 2.3 Update error handling to work with batch results (currently uses individual try/except blocks)
- [x] 2.4 Test executor tick timing - verify <200ms latency

## 3. Refactor Recorder Power Sensor Reads

- [x] 3.1 Modify `record_observation_from_current_state()` in `backend/recorder.py` (~line 187)
- [x] 3.2 Batch power sensors: pv_power, load_power, grid_import_power, grid_export_power, grid_power, battery_power, water_power (~line 280-312)
- [x] 3.3 Handle EV charger sensors in batch (variable number based on config, ~line 316-325)
- [x] 3.4 Keep cumulative energy sensor reads as-is (these have complex stateful logic with calculate_energy_from_cumulative)
- [x] 3.5 Verify recorder completes within 200ms per observation

## 4. Refactor Initial State Gathering

- [x] 4.1 Modify `get_initial_state()` in `backend/core/ha_client.py` (~line 130)
- [x] 4.2 Batch: battery SoC, water heater consumption, EV SoC, EV plug status (4 reads)
- [x] 4.3 Ensure critical SoC read still raises error if unavailable (maintain safety invariant)

## 5. Testing & Verification

- [x] 5.1 Run full test suite - ensure no regressions (`python -m pytest`)
- [x] 5.2 Add integration test verifying batch execution (mock timing)
- [x] 5.3 Add test for partial failure handling across all refactored locations
- [x] 5.4 Run `./scripts/lint.sh` - fix any issues
