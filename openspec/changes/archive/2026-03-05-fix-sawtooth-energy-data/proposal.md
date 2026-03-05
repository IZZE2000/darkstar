## Why

Energy data stored in `slot_observations` shows a sawtooth pattern where consecutive 15-minute slots alternate between HIGH (~20 min of production) and LOW (~10 min of production) values. This occurs because cumulative sensors update every 10 minutes while the recorder runs every 15 minutes, causing timing misalignment. The corrupted data feeds ML forecasting models, degrading prediction accuracy.

## What Changes

- Implement time-proportional scaling for cumulative sensor deltas using the sensor's `last_updated` timestamp
- When the actual time span differs from the target 15 minutes, scale the energy delta proportionally
- Three surgical changes to correct live recording and backfill:
  1. `RecorderStateStore.get_delta()` - add `sensor_timestamp` parameter for scaling
  2. `calculate_energy_from_cumulative()` - extract and pass `last_updated` from HA entity state
  3. `etl_cumulative_to_slots()` - replace forward-fill with linear interpolation for backfill

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `energy-recording`: Delta-based energy calculation now includes time-proportional scaling when sensor update timing differs from recording interval. The requirement for "subtracting cumulative meter reading at start from reading at end" is refined to also scale the result to represent exactly 15 minutes of energy.

## Impact

**Code Changes**:
- `backend/recorder.py` - `RecorderStateStore.get_delta()` and `calculate_energy_from_cumulative()`
- `backend/learning/engine.py` - `etl_cumulative_to_slots()` interpolation logic

**State File Schema**:
- `data/recorder_state.json` - new optional `sensor_timestamp` field per key

**Backward Compatibility**:
- Old state files without `sensor_timestamp` work unchanged (first recording after deploy uses raw delta)
- HA setups without `last_updated` field skip scaling gracefully
- No sensor reconfiguration required

**Affected Data**:
- All cumulative energy sensors (PV, load, import, export) will produce consistent 15-minute normalized values
- Historical data can be corrected by re-running backfill
