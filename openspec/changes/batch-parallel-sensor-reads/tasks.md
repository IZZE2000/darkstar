## 1. Create Batch Helper Function

- [ ] 1.1 Create `gather_sensor_reads()` helper in `inputs.py` with signature:
  ```python
  async def gather_sensor_reads(
      reads: list[tuple[str, Callable[[], Coroutine]]],
      context: str = "sensor_batch"
  ) -> dict[str, Any]
  ```
- [ ] 1.2 Implement `return_exceptions=True` handling to catch individual failures
- [ ] 1.3 Add context-aware logging for failed sensors
- [ ] 1.4 Write unit tests for `gather_sensor_reads()` covering:
  - All sensors succeed
  - Partial failures (some sensors unavailable)
  - All sensors fail
  - Proper logging output

## 2. Refactor Executor State Gathering

- [ ] 2.1 Modify `_gather_system_state()` in `executor/engine.py` to use batch helper
- [ ] 2.2 Group independent sensor reads (SoC, PV power, load power, import, export, work mode, grid charging, water temp, manual override)
- [ ] 2.3 Update error handling to work with batch results
- [ ] 2.4 Test executor tick timing - verify <200ms latency

## 3. Refactor Recorder Observation

- [ ] 3.1 Modify `record_observation_from_current_state()` in `backend/recorder.py`
- [ ] 3.2 Batch power sensors: pv_power, load_power, grid_import_power, grid_export_power, grid_power, battery_power, water_power
- [ ] 3.3 Handle EV charger sensors in batch (variable number based on config)
- [ ] 3.4 Keep cumulative sensor reads as-is (these have complex logic, may need separate batch)
- [ ] 3.5 Verify recorder completes within 200ms per observation

## 4. Refactor Input State Gathering

- [ ] 4.1 Modify `get_initial_state()` in `inputs.py`
- [ ] 4.2 Batch: battery SoC, water heater consumption, EV SoC, EV plug status
- [ ] 4.3 Ensure critical SoC read still raises error if unavailable (maintain safety)

## 5. Refactor Energy Range API

- [ ] 5.1 Modify `get_energy_range()` in `backend/api/routers/services.py`
- [ ] 5.2 Batch the 7 "today" sensor reads when `period == "today"`
- [ ] 5.3 Maintain backward compatibility for other periods (yesterday, week, etc.)

## 6. Standardize Existing Implementation

- [ ] 6.1 Refactor `get_energy_today()` to use new `gather_sensor_reads()` helper
- [ ] 6.2 Verify no regression in `/api/energy/today` endpoint

## 7. Testing & Verification

- [ ] 7.1 Run full test suite - ensure no regressions
- [ ] 7.2 Add integration test verifying batch execution (mock timing)
- [ ] 7.3 Add test for partial failure handling across all refactored locations
- [ ] 7.4 Run `./scripts/lint.sh` - fix any issues
- [ ] 7.5 Manual verification: check logs for sensor read timing

## 8. Documentation

- [ ] 8.1 Update docstrings for all modified functions
- [ ] 8.2 Add inline comments explaining batch reading pattern
- [ ] 8.3 Update CHANGELOG.md with performance improvement metrics
