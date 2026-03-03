## Context

`recorder.py` currently estimates 15-minute energy slots by taking a single power snapshot (kW) and multiplying by 0.25h. This creates a "shitty snapshot" problem where any fluctuations between the 15-minute intervals are lost. This results in inaccurate historical data for PV and Load, which in turn degrades the Aurora ML model's forecasting accuracy.

## Goals / Non-Goals

**Goals:**
- Update `input_sensors` schema to support cumulative energy entities (meter readings).
- Modify `recorder.py` to calculate energy as a delta between meter readings.
- Implement state persistence for meter readings to handle recorder restarts.
- Ensure 100% backward compatibility with snapshot-only configurations.

**Non-Goals:**
- Modifying the SQLite database schema (`slot_observations` already stores `kWh`).
- Modifying the ML model architecture itself (only the training data quality is improved).
- Handling long-term energy history backfills (limited to immediate delta calculation).

## Decisions

### 1. New Configuration Schema
Add optional cumulative energy sensor keys to the `input_sensors` section of `config.yaml`:
- `total_pv_production`
- `total_load_consumption`
- `total_grid_import`
- `total_grid_export`

**Rationale**: Allows users to provide high-fidelity energy data without breaking existing power-based setups.

### 2. State Persistence (`data/recorder_state.json`)
Store the last seen meter readings and their timestamps in a simple JSON file.
- **Why over Database?**: This is transient operational state, not historical observation data. A JSON file is faster to read/write and easier to debug during development.

### 3. Delta Logic & Fallback
If a cumulative sensor (e.g., `total_pv_production`) is defined, use it. If the delta is negative (meter reset) or the sensor is unavailable, log a warning and fall back to the power snapshot (`_power * 0.25`).

**Alternatives Considered**:
- *Always require energy sensors*: Rejected, as many users only have power snapshots from their inverters.
- *Store previous state in the DB*: Rejected, as it would require querying the DB for every 15-minute tick just to get one row, which is overkill for a state tracker.

## Risks / Trade-offs

- **[Risk] Meter Reset / Rollover** → **Mitigation**: Detect negative deltas. If `current < previous`, assume a reset and use the power snapshot fallback for that specific slot.
- **[Risk] State File Corruption** → **Mitigation**: Wrap state file operations in try/except; if corrupted, delete and start fresh (missing only one slot's delta).
- **[Risk] High Latency in HA** → **Mitigation**: Continue using snapshots if the energy sensor hasn't updated its value within a reasonable window.
