## ADDED Requirements

### Requirement: Optional energy_sensor field on EV charger config entries
Each entry in the `ev_chargers[]` configuration array SHALL support an optional `energy_sensor` field. When set to a non-empty string, it specifies the HA entity ID of a cumulative energy sensor (lifetime kWh counter) for that charger.

#### Scenario: User configures an energy sensor for their EV charger
- **WHEN** a user sets `energy_sensor: sensor.easee_home_energy` on an `ev_chargers[]` entry
- **THEN** the recorder SHALL use cumulative delta from this sensor to compute `ev_charging_kwh` for each slot

#### Scenario: Energy sensor field is absent or empty
- **WHEN** `energy_sensor` is absent or set to `''` on an `ev_chargers[]` entry
- **THEN** the recorder SHALL fall back to snapshot × 0.25h for `ev_charging_kwh`

### Requirement: Optional energy_sensor field on water heater config entries
Each entry in the `water_heaters[]` configuration array SHALL support an optional `energy_sensor` field. When set to a non-empty string, it specifies the HA entity ID of a cumulative energy sensor for that heater.

#### Scenario: User configures an energy sensor for their water heater
- **WHEN** a user sets `energy_sensor: sensor.vvb_energy` on a `water_heaters[]` entry
- **THEN** the recorder SHALL use cumulative delta from this sensor to compute `water_kwh` for each slot

#### Scenario: Energy sensor field is absent or empty
- **WHEN** `energy_sensor` is absent or set to `''` on a `water_heaters[]` entry
- **THEN** the recorder SHALL fall back to snapshot × 0.25h for `water_kwh`

### Requirement: Health check warns when energy sensor is missing on an enabled device
The health check (`/api/health`) SHALL emit a WARNING issue for each enabled EV charger or water heater that has no `energy_sensor` configured.

#### Scenario: Enabled EV charger with no energy sensor
- **WHEN** an `ev_chargers[]` entry has `enabled: true` and `energy_sensor: ''`
- **THEN** `GET /api/health` SHALL include an issue with `severity: "warning"` and `category: "config"`
- **AND** the message SHALL identify the charger by name and state that load isolation accuracy is reduced
- **AND** the guidance SHALL instruct the user to configure `energy_sensor` in Settings > EV

#### Scenario: Enabled water heater with no energy sensor
- **WHEN** a `water_heaters[]` entry has `enabled: true` and `energy_sensor: ''`
- **THEN** `GET /api/health` SHALL include an issue with `severity: "warning"` and `category: "config"`
- **AND** the message SHALL identify the heater by name and state that load isolation accuracy is reduced
- **AND** the guidance SHALL instruct the user to configure `energy_sensor` in Settings > Water

#### Scenario: Disabled device with no energy sensor
- **WHEN** a device entry has `enabled: false` and `energy_sensor: ''`
- **THEN** `GET /api/health` SHALL NOT emit a warning for that device

#### Scenario: All enabled devices have energy sensors configured
- **WHEN** all enabled EV chargers and water heaters have a non-empty `energy_sensor`
- **THEN** `GET /api/health` SHALL NOT include any energy-sensor-related warning issues

### Requirement: energy_sensor in default config template
The `config.default.yaml` SHALL include `energy_sensor: ''` in both the `ev_chargers[]` and `water_heaters[]` default entries so it appears automatically in all existing user configs via template-aware merge.

#### Scenario: Existing user receives energy_sensor field on next startup
- **WHEN** a user's existing config has an `ev_chargers[]` entry with `id: ev_charger_1` but no `energy_sensor` key
- **THEN** after the next startup, the saved config SHALL include `energy_sensor: ''` for that entry
- **AND** the user's existing values for all other fields SHALL be unchanged

### Requirement: Energy sensor unit normalization
The recorder SHALL normalize cumulative energy sensor values to kWh using the sensor's `unit_of_measurement` attribute, consistent with existing normalization for other cumulative sensors.

#### Scenario: Energy sensor reports in Wh
- **WHEN** the `energy_sensor` entity reports a value with `unit_of_measurement: "Wh"`
- **THEN** the recorder SHALL convert to kWh by dividing by 1000 before computing the delta

#### Scenario: Energy sensor reports in kWh
- **WHEN** the `energy_sensor` entity reports a value with `unit_of_measurement: "kWh"`
- **THEN** the recorder SHALL use the value as-is

### Requirement: ev_charging_kwh included in recorder observation log
The recorder SHALL include `ev_charging_kwh` in the "Recording observation" log line emitted for each slot.

#### Scenario: Recorder logs ev_charging_kwh
- **WHEN** the recorder stores a slot observation
- **THEN** the log line SHALL include `EV=<value>kWh` alongside the existing PV, Load, Water, and Battery fields
