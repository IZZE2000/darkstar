## Purpose

TBD - Energy recording capability for accurate historical energy tracking using cumulative meter sensors.

## Requirements

### Requirement: Support for Cumulative Energy Sensors
The system SHALL support configuring cumulative energy sensors (meter readings) in `input_sensors` for PV, Load, Grid, and Battery. These sensors represent total energy processed over the device's lifetime.

#### Scenario: User configures a total PV production sensor
- **WHEN** the user adds `total_pv_production: sensor.pv_energy_total` to `input_sensors` in `config.yaml`
- **THEN** the system SHALL recognize this as a cumulative source for PV energy calculation

### Requirement: Delta-based Energy Calculation
The recorder SHALL calculate the energy for a 15-minute slot by subtracting the cumulative meter reading at the start of the slot from the reading at the end of the slot, then scaling the result proportionally to represent exactly 15 minutes of energy when the sensor's update timing differs from the recording interval.

#### Scenario: Recorder calculates energy during a continuous run
- **WHEN** the recorder has a previous reading of `1000.0 kWh` for PV at `12:00`
- **AND** the current reading at `12:15` is `1001.2 kWh`
- **THEN** the recorder SHALL store `1.2 kWh` as the `pv_kwh` for the `12:00` slot

#### Scenario: Recorder calculates energy with matching timing
- **WHEN** the recorder has a previous reading of `1000.0 kWh` for PV at `12:00`
- **AND** the current reading at `12:15` is `1001.2 kWh`
- **AND** the sensor's `last_updated` timestamp indicates exactly 15 minutes elapsed
- **THEN** the recorder SHALL store `1.2 kWh` as the `pv_kwh` for the `12:00` slot

#### Scenario: Recorder scales energy when timing differs
- **WHEN** the recorder reads PV cumulative `1000.0 kWh` at `11:00:05` with sensor timestamp `10:53`
- **AND** the previous reading was `998.0 kWh` with sensor timestamp `10:43`
- **AND** the raw delta is `2.0 kWh` over 10 actual minutes
- **THEN** the recorder SHALL scale to `3.0 kWh` (2.0 × 15/10) for the 15-minute slot

#### Scenario: Recorder handles missing sensor timestamp gracefully
- **WHEN** the sensor's `last_updated` field is unavailable
- **THEN** the recorder SHALL use the raw delta without scaling

#### Scenario: Recorder skips scaling for extreme time gaps
- **WHEN** the time between sensor timestamps is less than 5 minutes or greater than 60 minutes
- **THEN** the recorder SHALL use the raw delta without scaling

### Requirement: Persistent Recorder State
The recorder SHALL persist its last known meter readings to a local state file to allow accurate delta calculation across service restarts.

#### Scenario: Recorder resumes after a restart
- **WHEN** the recorder service starts up
- **AND** it finds a state file containing a PV reading of `500.0 kWh` from 15 minutes ago
- **AND** the current HA reading is `500.5 kWh`
- **THEN** it SHALL record `0.5 kWh` for the missing slot instead of defaulting to 0 or snapshots

### Requirement: Automatic Unit Normalization
The system SHALL automatically normalize cumulative energy sensor values to kWh, supporting Wh, kWh, and MWh units based on the sensor's `unit_of_measurement` attribute.

#### Scenario: Sensor reports in Watt-hours
- **WHEN** a cumulative sensor reports `500000` with `unit_of_measurement: "Wh"`
- **THEN** the system SHALL normalize to `500.0 kWh`
- **AND** delta calculations SHALL use the normalized value

#### Scenario: Sensor reports in kilowatt-hours
- **WHEN** a cumulative sensor reports `500.0` with `unit_of_measurement: "kWh"`
- **THEN** the system SHALL use the value as-is

#### Scenario: Sensor reports in megawatt-hours
- **WHEN** a cumulative sensor reports `0.5` with `unit_of_measurement: "MWh"`
- **THEN** the system SHALL normalize to `500.0 kWh`

### Requirement: Snapshot Fallback
The recorder SHALL fall back to power-snapshot based estimation (kW * 0.25h) only when a cumulative energy sensor is not provided for a specific metric.

#### Scenario: Missing total energy sensor
- **WHEN** `input_sensors` only contains `pv_power: sensor.pv_current_kw` (no total energy sensor)
- **THEN** the recorder SHALL continue to use `pv_power * 0.25` to estimate energy for the slot

### Requirement: Energy value validation before storage
The recorder SHALL validate all energy values against physical limits before storing to `slot_observations`.

#### Scenario: Valid energy values stored
- **WHEN** all energy values in a record are within the calculated `max_kwh_per_slot`
- **THEN** the recorder SHALL store the values unchanged

#### Scenario: Spike values zeroed before storage
- **WHEN** an energy value exceeds `max_kwh_per_slot`
- **THEN** the recorder SHALL set that value to `0.0` before storage
- **AND** the recorder SHALL log a warning identifying the spiked field

### Requirement: Backfill uses config-derived threshold
The learning engine's `etl_cumulative_to_slots` and `etl_power_to_slots` functions SHALL use the config-derived threshold for spike filtering instead of a hardcoded value.

#### Scenario: Backfill filters spikes using config threshold
- **WHEN** backfill processes cumulative or power sensor data
- **AND** a delta exceeds `max_kwh_per_slot`
- **THEN** the delta SHALL be set to `0.0`

### Requirement: Analytical pipelines filter spike rows at read time
All analytical read paths that consume `pv_kwh` or `load_kwh` from `slot_observations` SHALL exclude rows where those values exceed `max_kwh_per_slot`.

#### Scenario: Analyst bias calculation excludes spike rows
- **WHEN** `Analyst._fetch_observations` fetches rows for bias analysis
- **THEN** rows where `load_kwh` or `pv_kwh` exceeds `max_kwh_per_slot` SHALL be excluded

#### Scenario: Reflex accuracy analysis excludes spike rows
- **WHEN** `LearningStore.get_forecast_vs_actual` returns rows for Reflex
- **THEN** rows where the actual energy column exceeds `max_kwh_per_slot` SHALL be excluded

#### Scenario: MAE metrics exclude spike rows
- **WHEN** `LearningStore.calculate_metrics` computes forecast MAE
- **THEN** the query SHALL exclude rows where `pv_kwh` or `load_kwh` exceeds `max_kwh_per_slot`

#### Scenario: ML model training excludes spike rows
- **WHEN** `ml/train.py` `_load_slot_observations` loads data for Aurora model training
- **THEN** rows where `pv_kwh` or `load_kwh` exceeds `max_kwh_per_slot` SHALL be excluded from training data

#### Scenario: ML error correction training excludes spike rows
- **WHEN** `ml/corrector.py` `_load_training_frame` loads data for error correction model training
- **THEN** rows where `pv_kwh` or `load_kwh` exceeds `max_kwh_per_slot` SHALL be excluded

#### Scenario: ML evaluation metrics exclude spike rows
- **WHEN** `ml/evaluate.py` `_compute_mae` calculates forecast accuracy metrics
- **THEN** rows where `pv_kwh` or `load_kwh` exceeds `max_kwh_per_slot` SHALL be excluded from MAE calculation

### Requirement: Persistent Sensor Timestamp Storage
The recorder SHALL store the sensor's `last_updated` timestamp alongside each cumulative meter reading in the state file to enable time-proportional scaling on subsequent recordings.

#### Scenario: State file includes sensor timestamp
- **WHEN** the recorder successfully reads a cumulative sensor value
- **THEN** the state file entry SHALL include `sensor_timestamp` with the ISO format timestamp from the sensor's `last_updated` field

#### Scenario: Backward compatible with old state files
- **WHEN** the recorder reads a state file entry without `sensor_timestamp`
- **THEN** the recorder SHALL proceed without scaling for that recording cycle

### Requirement: Backfill Interpolation for Cumulative Sensors
The learning engine's `etl_cumulative_to_slots` function SHALL use linear interpolation to estimate cumulative values at exact slot boundaries, ensuring consistent delta calculations across all slots.

#### Scenario: Backfill interpolates to slot boundaries
- **WHEN** backfill processes cumulative sensor data with readings at irregular times
- **THEN** the function SHALL interpolate cumulative values at `:00, :15, :30, :45` boundaries
- **AND** delta calculations SHALL use these interpolated boundary values

#### Scenario: Backfill handles edge cases with fill
- **WHEN** interpolation leaves NaN values at series edges
- **THEN** the function SHALL apply forward-fill then backward-fill to ensure complete coverage
