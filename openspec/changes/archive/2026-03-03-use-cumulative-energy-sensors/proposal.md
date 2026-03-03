## Why

`recorder.py` currently estimates 15-minute energy slots using a single power snapshot every 15 minutes. This is a poor proxy for actual energy (kWh) because it misses all fluctuations between snapshots, leading to inaccurate historical data and poor Aurora ML training results.

## What Changes

- **Cumulative Sensor Support**: `input_sensors` in `config.yaml` will support optional cumulative energy sensors (e.g., `total_pv_production`, `total_load_consumption`).
- **Delta-based Recording**: `recorder.py` will transition to calculating energy as the difference between cumulative meter readings across 15-minute intervals.
- **Fallback Logic**: Maintain power-snapshot recording as a fallback when cumulative energy sensors are not provided.
- **State Persistence**: Implement a lightweight state file to persist the last known meter readings between recorder runs.

## Capabilities

### New Capabilities
- `energy-recording`: Precision energy recording using cumulative meter deltas for PV, Load, Grid, and Battery.

### Modified Capabilities
<!-- Existing capabilities whose REQUIREMENTS are changing -->

## Impact

- **`recorder.py`**: Core logic for calculating and storing observations.
- **`config.yaml` Schema**: New `input_sensors` keys for total energy entities.
- **`ml/train.py` & `ml/forward.py`**: Improved forecast accuracy due to high-fidelity training data.
- **Dashboard**: "Actual" PV and Load displays will reflect true energy integrated over the 15-minute slot.
