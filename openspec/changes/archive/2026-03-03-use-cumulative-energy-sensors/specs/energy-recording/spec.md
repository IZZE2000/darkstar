## ADDED Requirements

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

### Requirement: Snapshot Fallback
The recorder SHALL fall back to power-snapshot based estimation (kW * 0.25h) only when a cumulative energy sensor is not provided for a specific metric.

#### Scenario: Missing total energy sensor
- **WHEN** `input_sensors` only contains `pv_power: sensor.pv_current_kw` (no total energy sensor)
- **THEN** the recorder SHALL continue to use `pv_power * 0.25` to estimate energy for the slot
