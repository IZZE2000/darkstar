## MODIFIED Requirements

### Requirement: Executor sets water heater temperature during scheduled operation

The executor SHALL set each water heater's target temperature based on the controller decision during each tick execution. For each enabled heater with a `target_entity`, the executor SHALL independently determine the temperature from the per-device plan.

#### Scenario: Water heating is scheduled for one heater
- **GIVEN** system has `has_water_heater=true`
- **AND** heater A has a configured target entity
- **AND** current slot has heater A's planned kW > 0 in `water_heater_plans`
- **WHEN** executor tick executes
- **THEN** heater A's temperature is set to `temp_normal` (e.g., 60°C)
- **AND** action result is logged to execution history

#### Scenario: Water heating is not scheduled for a heater
- **GIVEN** system has `has_water_heater=true`
- **AND** heater B has a configured target entity
- **AND** current slot has heater B's planned kW = 0 in `water_heater_plans`
- **WHEN** executor tick executes
- **THEN** heater B's temperature is set to `temp_off` (e.g., 40°C)
- **AND** action result is logged to execution history

#### Scenario: Multiple heaters controlled in same tick
- **GIVEN** two enabled heaters with target entities
- **AND** current slot has heater A heating and heater B idle
- **WHEN** executor tick executes
- **THEN** the executor SHALL set heater A to `temp_normal` AND heater B to `temp_off`
- **AND** both action results are logged to execution history

#### Scenario: Water heater not configured
- **GIVEN** system has `has_water_heater=false`
- **OR** no water heater has a configured target entity
- **WHEN** executor tick executes
- **THEN** water temperature actions are skipped
- **AND** no error is logged

### Requirement: Water temperature action is idempotent

The executor SHALL skip setting water temperature for a heater if the current temperature already matches the target.

#### Scenario: Temperature already at target for one heater
- **GIVEN** heater A's current temperature is 60°C
- **AND** controller decision sets heater A to `temp_normal=60`
- **WHEN** executor executes water temp action for heater A
- **THEN** action is skipped with `skipped=True`
- **AND** result message indicates "Already at 60°C"

### Requirement: Water temperature action respects shadow mode

The executor SHALL NOT actually set water temperature for any heater when shadow mode is enabled.

#### Scenario: Shadow mode enabled with multiple heaters
- **GIVEN** executor is in shadow mode
- **AND** two heaters have per-device plans
- **WHEN** water temp actions would execute
- **THEN** temperatures are NOT sent to Home Assistant for either heater
- **AND** action results have `skipped=True` for each heater

### Requirement: Water temperature action is logged to execution history

Each water temperature action result SHALL be included in the execution history record, with the heater ID included in the action metadata.

#### Scenario: Per-device actions logged to history
- **GIVEN** two water heaters have temperature actions executed
- **WHEN** execution record is created
- **THEN** `action_results` includes entries for each heater with:
  - `type: "water_temp"`
  - `success: true/false`
  - `previous_value: <old temp>`
  - `new_value: <target temp>`
  - `entity_id: <heater's target entity>`
  - `skipped: true/false`

### Requirement: Water temperature follows EV charger control pattern

Water heater control SHALL be implemented as a per-device control loop outside the inverter profile system, consistent with the EV charger per-device pattern.

#### Scenario: Architecture alignment with per-device EV charger
- **GIVEN** executor controls multiple device types with per-device loops
- **WHEN** water heater control is executed
- **THEN** it follows the same pattern as per-device EV charger:
  - Iterates over configured heaters in `_tick()` after inverter profile execution
  - Uses `dispatcher.set_water_temp(target_entity, temp)` per heater
  - Results appended to `action_results`
  - Conditioned on `has_water_heater` and per-device entity configuration
