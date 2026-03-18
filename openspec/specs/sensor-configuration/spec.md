# Sensor Configuration

## Purpose

Configuration for Home Assistant sensors and input sensors.

## Requirements

### Requirement: Configuration schema removes today_* sensors
The configuration schema SHALL NOT require or support `today_*` sensors in the `input_sensors` section.

#### Scenario: Config validation rejects today_* sensors
- **WHEN** a configuration file contains any `today_*` sensor keys
- **THEN** the validation system rejects the configuration with a descriptive error message
- **AND** the error message names the offending keys and instructs the user to remove them

#### Scenario: Default config excludes today_* sensors
- **WHEN** a new user installs Darkstar
- **THEN** the default config.yaml does NOT include any `today_*` sensors
- **AND** the default config only includes cumulative sensors

### Requirement: Settings UI removes today_* sensor configuration
The Settings user interface SHALL NOT display configuration fields for `today_*` sensors.

#### Scenario: Settings page shows only cumulative sensors
- **WHEN** a user navigates to Settings > Input Sensors
- **THEN** the UI displays configuration for cumulative sensors only
- **AND** does NOT display fields for today_grid_import, today_grid_export, today_pv_production, today_load_consumption, today_battery_charge, today_battery_discharge, or today_net_cost

### Requirement: Config help documentation updates
The configuration help documentation SHALL remove all references to `today_*` sensors.

#### Scenario: Help text updated
- **WHEN** a user views configuration help
- **THEN** the documentation describes cumulative sensors as the required configuration
- **AND** does NOT mention `today_*` sensors

### Requirement: EV charger energy_sensor configuration removed
The `energy_sensor` field is no longer supported for `ev_chargers[]` items. EV energy recording uses the HA History API with the existing power sensor (`sensor` field). Config migration silently removes `energy_sensor` from `ev_chargers[]` items — no user action required.

#### Scenario: Config migration removes energy_sensor from EV chargers
- **WHEN** an existing config contains `energy_sensor` in an `ev_chargers[]` item
- **THEN** the migration SHALL remove the `energy_sensor` field
- **AND** the migration SHALL NOT affect other fields in the EV charger config

#### Scenario: Default config excludes energy_sensor for EV chargers
- **WHEN** a new user installs Darkstar
- **THEN** the default config SHALL NOT include `energy_sensor` in `ev_chargers[]` items

### Requirement: Water heater energy_sensor configuration removed
The `energy_sensor` field is no longer supported for `water_heaters[]` items. Water heater energy recording uses the HA History API with the existing power sensor (`sensor` field). Config migration silently removes `energy_sensor` from `water_heaters[]` items — no user action required.

#### Scenario: Config migration removes energy_sensor from water heaters
- **WHEN** an existing config contains `energy_sensor` in a `water_heaters[]` item
- **THEN** the migration SHALL remove the `energy_sensor` field
- **AND** the migration SHALL NOT affect other fields in the water heater config

#### Scenario: Default config excludes energy_sensor for water heaters
- **WHEN** a new user installs Darkstar
- **THEN** the default config SHALL NOT include `energy_sensor` in `water_heaters[]` items

### Requirement: No health check warnings for missing energy_sensor (EV/Water)
The health check SHALL NOT warn about missing `energy_sensor` for EV chargers or water heaters, as this field no longer exists.

#### Scenario: No health warning for missing EV energy_sensor
- **WHEN** the health check evaluates an enabled EV charger
- **THEN** it SHALL NOT warn about missing `energy_sensor`

#### Scenario: No health warning for missing water heater energy_sensor
- **WHEN** the health check evaluates an enabled water heater
- **THEN** it SHALL NOT warn about missing `energy_sensor`

### Requirement: Settings UI removes energy_sensor for EV and Water
The Settings user interface SHALL NOT display the `energy_sensor` configuration field for EV chargers or water heaters.

#### Scenario: EV charger settings exclude energy_sensor
- **WHEN** a user navigates to Settings > EV
- **THEN** the entity array editor for EV chargers SHALL NOT display an `energy_sensor` field

#### Scenario: Water heater settings exclude energy_sensor
- **WHEN** a user navigates to Settings > Water
- **THEN** the entity array editor for water heaters SHALL NOT display an `energy_sensor` field
