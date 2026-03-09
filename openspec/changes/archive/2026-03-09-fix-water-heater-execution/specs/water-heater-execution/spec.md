## ADDED Requirements

### Requirement: Executor sets water heater temperature during scheduled operation

The executor SHALL set the water heater target temperature based on the controller decision during each tick execution.

#### Scenario: Water heating is scheduled
- **GIVEN** system has `has_water_heater=true`
- **AND** water heater target entity is configured
- **AND** current slot has `water_kw > 0`
- **WHEN** executor tick executes
- **THEN** water heater temperature is set to `temp_normal` (e.g., 50°C)
- **AND** action result is logged to execution history

#### Scenario: Water heating is not scheduled
- **GIVEN** system has `has_water_heater=true`
- **AND** water heater target entity is configured
- **AND** current slot has `water_kw = 0`
- **WHEN** executor tick executes
- **THEN** water heater temperature is set to `temp_off` (e.g., 40°C)
- **AND** action result is logged to execution history

#### Scenario: Water heater not configured
- **GIVEN** system has `has_water_heater=false`
- **OR** water heater target entity is not configured
- **WHEN** executor tick executes
- **THEN** water temperature action is skipped
- **AND** no error is logged

### Requirement: Water temperature action is idempotent

The executor SHALL skip setting water temperature if the current temperature already matches the target.

#### Scenario: Temperature already at target
- **GIVEN** water heater current temperature is 50°C
- **AND** controller decision sets `water_temp=50`
- **WHEN** executor executes water temp action
- **THEN** action is skipped with `skipped=True`
- **AND** result message indicates "Already at 50°C"

### Requirement: Water temperature action respects shadow mode

The executor SHALL NOT actually set water temperature when shadow mode is enabled.

#### Scenario: Shadow mode enabled
- **GIVEN** executor is in shadow mode
- **WHEN** water temp action would execute
- **THEN** temperature is NOT sent to Home Assistant
- **AND** action result has `skipped=True`
- **AND** result message indicates "[SHADOW] Would change..."

### Requirement: Water temperature action is logged to execution history

The water temperature action result SHALL be included in the execution history record.

#### Scenario: Action logged to history
- **GIVEN** water temperature action is executed
- **WHEN** execution record is created
- **THEN** `action_results` includes entry with:
  - `type: "water_temp"`
  - `success: true/false`
  - `previous_value: <old temp>`
  - `new_value: <target temp>`
  - `entity_id: <water heater entity>`
  - `skipped: true/false`

### Requirement: Water temperature follows EV charger control pattern

Water heater control SHALL be implemented as a separate control path outside the inverter profile system.

#### Scenario: Architecture alignment with EV charger
- **GIVEN** executor controls multiple device types
- **WHEN** water heater control is implemented
- **THEN** it follows the same pattern as EV charger:
  - Called in `_tick()` after inverter profile execution
  - Uses `dispatcher.set_water_temp()` method
  - Result appended to `action_results`
  - Conditioned on `has_water_heater` and entity configuration
