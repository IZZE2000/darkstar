## ADDED Requirements

### Requirement: Executor supports boost temperature from schedule

The executor SHALL set water heater target temperature to `temp_boost` (85°C) when the schedule indicates boost mode for that heater, instead of the normal `temp_normal` (60°C).

#### Scenario: Water heater boost scheduled
- **WHEN** the current slot has `water_heating_boost` with heater A set to true
- **AND** heater A has a configured target entity
- **WHEN** executor tick executes
- **THEN** heater A's temperature SHALL be set to `temp_max` (85°C, the PV dump target)

#### Scenario: Water heater normal heating scheduled
- **WHEN** the current slot has heater A's planned kW > 0
- **AND** `water_heating_boost` does not include heater A
- **WHEN** executor tick executes
- **THEN** heater A's temperature SHALL be set to `temp_normal` (60°C)

#### Scenario: Water heater boost takes precedence over normal
- **WHEN** the current slot has heater A in both normal heating and boost
- **WHEN** executor tick executes
- **THEN** heater A's temperature SHALL be set to `temp_max` (85°C, the PV dump target)
- **AND** boost SHALL override the normal temperature
- **NOTE**: `temp_boost` (70°C) is reserved for the manual dashboard boost button. Excess PV boost uses `temp_max` (85°C) to maximise thermal storage.

#### Scenario: Boost applied per-device independently
- **WHEN** the schedule has heater A in boost mode and heater B in normal mode
- **WHEN** executor tick executes
- **THEN** heater A SHALL be set to `temp_boost` (85°C)
- **AND** heater B SHALL be set to `temp_normal` (60°C)
