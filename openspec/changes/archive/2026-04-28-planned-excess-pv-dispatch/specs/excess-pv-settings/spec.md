## ADDED Requirements

### Requirement: Excess PV sink configuration in Advanced tab

The Settings UI SHALL provide an excess PV sink selector in the Advanced tab under "Excess PV Dispatch", allowing users to choose between "Water Heater Boost", "Custom Entity", or "Disabled".

#### Scenario: User with water heater sees all three options
- **WHEN** system configuration has `has_water_heater=true`
- **THEN** the sink selector SHALL offer "Water Heater Boost", "Custom Entity", and "Disabled"
- **AND** "Water Heater Boost" SHALL be the default selection

#### Scenario: User without water heater sees only two options
- **WHEN** system configuration has `has_water_heater=false`
- **THEN** the sink selector SHALL offer only "Custom Entity" and "Disabled"
- **AND** "Water Heater Boost" SHALL NOT appear

#### Scenario: Water heater boost selected shows boost reward and SoC threshold
- **WHEN** user selects "Water Heater Boost" as the sink
- **THEN** a `boost_reward_sek_per_kwh` field SHALL appear with SEK/kWh unit label
- **AND** a `soc_threshold_percent` field SHALL appear with % unit label
- **AND** boost is automatic — no per-device energy budget required

#### Scenario: Custom entity selected shows entity configuration, boost reward, and SoC threshold
- **WHEN** user selects "Custom Entity" as the sink
- **THEN** fields SHALL appear for entity ID, on-value, off-value, and power (kW)
- **AND** entity ID SHALL accept a valid Home Assistant entity ID (e.g., `switch.pool_pump`)
- **AND** entity ID validation SHALL reject empty values
- **AND** a `power_kw` field SHALL appear for estimated power consumption in kW (default 1.0)
- **AND** a `boost_reward_sek_per_kwh` field SHALL also appear with SEK/kWh unit label (same reward for both sink types)
- **AND** a `soc_threshold_percent` field SHALL appear with % unit label

#### Scenario: Disabled hides all configuration fields
- **WHEN** user selects "Disabled" as the sink
- **THEN** no additional excess PV configuration fields SHALL appear
- **AND** the system SHALL NOT schedule or execute any excess PV actions

### Requirement: Excess PV config saved and loaded from config.yaml

The excess PV sink configuration SHALL be persisted to `config.yaml` under `executor.excess_pv` and loaded at executor startup.

#### Scenario: Config saved on settings change
- **WHEN** user changes the excess PV sink from "Water Heater Boost" to "Custom Entity"
- **AND** saves the configuration
- **THEN** `executor.excess_pv.sink` SHALL be set to `custom_entity` in config.yaml

#### Scenario: Config loaded on executor startup
- **WHEN** executor starts and reads config.yaml
- **AND** `executor.excess_pv.sink` is set to `custom_entity`
- **THEN** the executor SHALL use the custom entity as the excess PV sink
- **AND** water heater boost SHALL be disabled regardless of `has_water_heater`
