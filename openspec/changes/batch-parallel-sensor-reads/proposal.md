## Why

Multiple locations in the codebase fetch Home Assistant sensor values sequentially, causing unnecessary latency. For example, `_gather_system_state()` makes 8-10 sequential HTTP calls (600-1000ms total) when they could run in parallel (150ms). This optimization was already applied to `/api/energy/today` in ARC5 with significant performance gains (6×100ms → 1×150ms), but 4+ other locations remain unoptimized.

## What Changes

- **New**: Create `gather_sensor_reads()` helper function with proper error handling (`return_exceptions=True`)
- **Refactor**: `executor/engine.py:_gather_system_state()` - batch 8-10 sensor reads
- **Refactor**: `backend/recorder.py:record_observation_from_current_state()` - batch 10+ sensor reads
- **Refactor**: `inputs.py:get_initial_state()` - batch 4 sensor reads
- **Refactor**: `backend/api/routers/services.py:get_energy_range()` - batch 7 sensor reads
- **Tests**: Add regression tests verifying parallel execution and graceful partial failures

## Capabilities

### New Capabilities
- `sensor-batch-operations`: Parallel batch reading of Home Assistant sensors with graceful error handling

### Modified Capabilities
- None (this is purely an optimization, no behavior changes)

## Impact

- **executor/engine.py**: System state gathering (called every 60s)
- **backend/recorder.py**: Observation recording (called every 15m)
- **inputs.py**: Initial state fetching (called during planning)
- **backend/api/routers/services.py**: Energy range API endpoint
- **Performance**: ~75% reduction in sensor read latency (600-1000ms → 150ms)
