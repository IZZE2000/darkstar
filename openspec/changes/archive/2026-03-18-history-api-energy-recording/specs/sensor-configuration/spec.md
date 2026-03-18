## REMOVED Requirements

### Requirement: EV charger energy_sensor configuration
**Reason**: EV energy recording now uses the HA History API with the existing power sensor (`sensor` field). The `energy_sensor` field is no longer needed.
**Migration**: Config migration silently removes `energy_sensor` from `ev_chargers[]` items. No user action required.

#### Scenario: Config migration removes energy_sensor from EV chargers
- **WHEN** an existing config contains `energy_sensor` in an `ev_chargers[]` item
- **THEN** the migration SHALL remove the `energy_sensor` field
- **AND** the migration SHALL NOT affect other fields in the EV charger config

#### Scenario: Default config excludes energy_sensor for EV chargers
- **WHEN** a new user installs Darkstar
- **THEN** the default config SHALL NOT include `energy_sensor` in `ev_chargers[]` items

### Requirement: Water heater energy_sensor configuration
**Reason**: Water heater energy recording now uses the HA History API with the existing power sensor (`sensor` field). The `energy_sensor` field is no longer needed.
**Migration**: Config migration silently removes `energy_sensor` from `water_heaters[]` items. No user action required.

#### Scenario: Config migration removes energy_sensor from water heaters
- **WHEN** an existing config contains `energy_sensor` in a `water_heaters[]` item
- **THEN** the migration SHALL remove the `energy_sensor` field
- **AND** the migration SHALL NOT affect other fields in the water heater config

#### Scenario: Default config excludes energy_sensor for water heaters
- **WHEN** a new user installs Darkstar
- **THEN** the default config SHALL NOT include `energy_sensor` in `water_heaters[]` items

### Requirement: Health check warnings for missing energy_sensor (EV/Water)
**Reason**: The `energy_sensor` field no longer exists for EV chargers and water heaters.
**Migration**: Remove health check warnings that suggest configuring `energy_sensor` for EV chargers and water heaters.

#### Scenario: No health warning for missing EV energy_sensor
- **WHEN** the health check evaluates an enabled EV charger
- **THEN** it SHALL NOT warn about missing `energy_sensor`

#### Scenario: No health warning for missing water heater energy_sensor
- **WHEN** the health check evaluates an enabled water heater
- **THEN** it SHALL NOT warn about missing `energy_sensor`

## MODIFIED Requirements

### Requirement: Settings UI removes energy_sensor for EV and Water
The Settings user interface SHALL NOT display the `energy_sensor` configuration field for EV chargers or water heaters.

#### Scenario: EV charger settings exclude energy_sensor
- **WHEN** a user navigates to Settings > EV
- **THEN** the entity array editor for EV chargers SHALL NOT display an `energy_sensor` field

#### Scenario: Water heater settings exclude energy_sensor
- **WHEN** a user navigates to Settings > Water
- **THEN** the entity array editor for water heaters SHALL NOT display an `energy_sensor` field
