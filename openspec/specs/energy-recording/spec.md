## Purpose

TBD - Energy recording capability for accurate historical energy tracking using cumulative meter sensors.

## Requirements

### Requirement: Support for Cumulative Energy Sensors
The system SHALL support configuring cumulative energy sensors (meter readings) in `input_sensors` for PV, Load, Grid, and Battery. These sensors represent total energy processed over the device's lifetime.

#### Scenario: User configures a total PV production sensor
- **WHEN** the user adds `total_pv_production: sensor.pv_energy_total` to `input_sensors` in `config.yaml`
- **THEN** the system SHALL recognize this as a cumulative source for PV energy calculation

### Requirement: Delta-based Energy Calculation
The recorder SHALL calculate the energy for a 15-minute slot by subtracting the cumulative meter reading at the start of the slot from the reading at the end of the slot.

#### Scenario: Recorder calculates energy during a continuous run
- **WHEN** the recorder has a previous reading of `1000.0 kWh` for PV at `12:00`
- **AND** the current reading at `12:15` is `1001.2 kWh`
- **THEN** the recorder SHALL store `1.2 kWh` as the `pv_kwh` for the `12:00` slot

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
