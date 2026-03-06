## Why

When EV charging or water heating occurs, the power consumption appears in the recorded `load_kwh` observation, contaminating the "base load" measurement used for ML training and forecasting. This is a regression introduced when cumulative energy sensors were added (Mar 3) - the new delta-based calculation bypassed the existing LoadDisaggregator that correctly isolates controllable loads for power snapshots. The result: ML models learn polluted patterns, and the analyst calculates incorrect bias adjustments.

## What Changes

- **Recorder**: Subtract EV charging and water heating energy from total load before storing `load_kwh`
- **LoadDisaggregator**: No changes needed - already correctly isolates power snapshots
- **energy-recording spec**: Add requirement for load isolation from deferrable loads

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `energy-recording`: Add requirement that `load_kwh` SHALL represent base load (total load minus deferrable loads like EV charging and water heating).

## Impact

- **backend/recorder.py**: Modify `record_observation_from_current_state()` to subtract EV and water energy from load before storage
- **backend/learning/analyst.py**: No changes - will automatically use corrected data
- **ML models**: Will train on clean base load data going forward (historical data remains contaminated but will be overwritten naturally)
- **Energy-recording spec**: New requirement section for load isolation
