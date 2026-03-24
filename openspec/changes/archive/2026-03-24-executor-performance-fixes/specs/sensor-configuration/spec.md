## MODIFIED Requirements

### Requirement: Default config does not include placeholder sensor entities
The default configuration template (`config.default.yaml`) SHALL NOT include placeholder sensor entity names for optional subsystems. The `water_heaters[].sensor` field SHALL default to an empty string (`''`) rather than a specific entity name like `sensor.vvb_power`.

#### Scenario: New installation has no phantom water heater sensor
- **WHEN** a new user installs Darkstar
- **AND** the default config is generated from `config.default.yaml`
- **THEN** the `water_heaters[0].sensor` field is `''` (empty string)
- **AND** no HTTP requests are made for non-existent water heater entities
