## REMOVED Requirements

### Requirement: Global water heater sensor configuration
**Reason**: `input_sensors.water_power` and `input_sensors.water_heater_consumption` are redundant — the same sensors already exist per-device in `water_heaters[]` as `sensor` and `energy_sensor`. All subsystems now read from the array.
**Migration**: Config migration copies `input_sensors.water_power` into `water_heaters[0].sensor` (if empty) and `input_sensors.water_heater_consumption` into `water_heaters[0].energy_sensor` (if empty) before the old keys are removed by template merge.

## ADDED Requirements

### Requirement: All water heater sensors live in the array

Each `water_heaters[]` item uses its existing `sensor` field (power) and `energy_sensor` field (daily energy) for all subsystems — load disaggregation, recorder metrics, executor metrics, and websocket feed. The global `input_sensors.water_power` and `input_sensors.water_heater_consumption` keys SHALL NOT exist in the config schema.

#### Scenario: New install has no global water sensor keys
- **WHEN** a new user installs Darkstar
- **THEN** `config.default.yaml` does NOT contain `input_sensors.water_power` or `input_sensors.water_heater_consumption`
- **AND** each `water_heaters[]` item has `sensor` and `energy_sensor` fields

#### Scenario: Existing config migrates global sensors into array
- **GIVEN** a user config has `input_sensors.water_power: "sensor.boiler_power"` and `water_heaters[0].sensor` is empty
- **WHEN** config migration runs
- **THEN** `water_heaters[0].sensor` is set to `"sensor.boiler_power"`
- **AND** `input_sensors.water_power` is removed

#### Scenario: Existing config with sensor already set skips migration
- **GIVEN** a user config has `input_sensors.water_power: "sensor.boiler_power"` and `water_heaters[0].sensor: "sensor.vvb_power"`
- **WHEN** config migration runs
- **THEN** `water_heaters[0].sensor` remains `"sensor.vvb_power"` (not overwritten)
- **AND** `input_sensors.water_power` is removed

### Requirement: Water heater target_entity lives in the array

Each `water_heaters[]` item SHALL support a `target_entity` field for thermostat control. The global `executor.water_heater.target_entity` SHALL NOT exist in the config schema.

#### Scenario: New install has target_entity in array
- **WHEN** a new user installs Darkstar
- **THEN** each `water_heaters[]` item has a `target_entity` field
- **AND** `executor.water_heater` does NOT contain `target_entity`

#### Scenario: Existing config migrates target_entity into array
- **GIVEN** a user config has `executor.water_heater.target_entity: "climate.boiler"`
- **WHEN** config migration runs
- **THEN** `water_heaters[0].target_entity` is set to `"climate.boiler"`
- **AND** `executor.water_heater.target_entity` is removed

### Requirement: Settings UI configures water sensors inside array accordion

The Settings UI SHALL NOT render separate "HA Sensors" or "Control" cards for water heater sensors. These fields SHALL be configurable within each water heater's expandable accordion item.

#### Scenario: Water tab shows no orphaned sensor cards
- **WHEN** user navigates to Settings > Water
- **THEN** there is no "HA Sensors" card
- **AND** there is no "Control" card
- **AND** each water heater accordion item contains `target_entity`, `sensor`, and `energy_sensor` fields

### Requirement: Health checks validate per-device water sensors

The health check system SHALL validate `sensor` and `energy_sensor` from `water_heaters[]` items instead of from `input_sensors`.

#### Scenario: Health check reports missing water power sensor
- **GIVEN** a water heater has `enabled=true` and `sensor` is empty
- **WHEN** health check runs
- **THEN** a warning is reported for that heater's missing power sensor
