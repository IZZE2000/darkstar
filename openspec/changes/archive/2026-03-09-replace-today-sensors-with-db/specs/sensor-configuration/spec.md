## ADDED Requirements

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
