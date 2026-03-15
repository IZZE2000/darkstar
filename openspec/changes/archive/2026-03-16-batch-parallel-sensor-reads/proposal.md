## Why

Multiple locations in the codebase fetch Home Assistant sensor values sequentially, causing unnecessary latency. For example, `_gather_system_state()` makes 8-10 sequential HTTP calls (600-1000ms total) when they could run in parallel (~150ms). Three locations remain unoptimized after the inputs.py and services.py refactoring.

Note: The original `/api/energy/today` endpoint (ARC5) and `get_energy_range()` now use database queries instead of sensor reads, so they no longer need this optimization.

## What Changes

- **New**: Create `gather_sensor_reads()` helper function in `backend/core/ha_client.py` with proper error handling (`return_exceptions=True`)
- **Refactor**: `executor/engine.py:_gather_system_state()` - batch 9 sequential sensor reads
- **Refactor**: `backend/recorder.py:record_observation_from_current_state()` - batch power sensor reads (6+ sequential awaits)
- **Refactor**: `backend/core/ha_client.py:get_initial_state()` - batch 4 sequential sensor reads
- **Tests**: Add regression tests verifying parallel execution and graceful partial failures

## Capabilities

### New Capabilities
- `sensor-batch-operations`: Parallel batch reading of Home Assistant sensors with graceful error handling

### Modified Capabilities
- None (this is purely an optimization, no behavior changes)

## Impact

- **executor/engine.py**: System state gathering (called every 60s)
- **backend/recorder.py**: Observation recording (called every 15m)
- **backend/core/ha_client.py**: Initial state fetching (called during planning)
- **Performance**: ~75% reduction in sensor read latency per call site
