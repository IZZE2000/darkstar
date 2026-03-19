## MODIFIED Requirements

### Requirement: Executor sets water heater temperature during scheduled operation

The executor SHALL read the water heater `target_entity` from the `water_heaters[]` array (first enabled heater with a configured `target_entity`) instead of from `executor.water_heater.target_entity`. Temperature setpoints (`temp_normal`, `temp_off`, etc.) remain in `executor.water_heater` until a future change moves them into the array.

#### Scenario: Water heating is scheduled
- **GIVEN** system has `has_water_heater=true`
- **AND** at least one entry in `water_heaters[]` has `enabled=true` and a non-empty `target_entity`
- **AND** current slot has `water_kw > 0`
- **WHEN** executor tick executes
- **THEN** water heater temperature is set to `temp_normal` on the first enabled heater's `target_entity`
- **AND** action result is logged to execution history

#### Scenario: Water heating is not scheduled
- **GIVEN** system has `has_water_heater=true`
- **AND** at least one entry in `water_heaters[]` has `enabled=true` and a non-empty `target_entity`
- **AND** current slot has `water_kw = 0`
- **WHEN** executor tick executes
- **THEN** water heater temperature is set to `temp_off` on the first enabled heater's `target_entity`
- **AND** action result is logged to execution history

#### Scenario: No water heater has target_entity configured
- **GIVEN** system has `has_water_heater=true`
- **AND** no entry in `water_heaters[]` has a non-empty `target_entity`
- **WHEN** executor tick executes
- **THEN** water temperature action is skipped
- **AND** no error is logged

### Requirement: Executor reads water power metrics from array

The executor SHALL read the live water power from `water_heaters[].sensor` instead of from `input_sensors.water_power`. When multiple heaters are enabled, power readings SHALL be aggregated (summed).

#### Scenario: Single water heater power metrics
- **GIVEN** one entry in `water_heaters[]` has `enabled=true` and `sensor` configured
- **WHEN** executor collects metrics
- **THEN** `water_kw` metric equals the reading from that heater's `sensor`

#### Scenario: Multiple water heaters power metrics
- **GIVEN** two entries in `water_heaters[]` have `enabled=true` and `sensor` configured
- **WHEN** executor collects metrics
- **THEN** `water_kw` metric equals the sum of both heaters' `sensor` readings

#### Scenario: No sensor configured
- **GIVEN** no entry in `water_heaters[]` has a `sensor` configured
- **WHEN** executor collects metrics
- **THEN** `water_kw` metric is 0.0

### Requirement: Daily energy tracking reads from array

The backend SHALL read `energy_sensor` from `water_heaters[]` items instead of from `input_sensors.water_heater_consumption`. When multiple heaters are enabled, energy values SHALL be aggregated (summed).

#### Scenario: Single water heater daily energy
- **GIVEN** one entry in `water_heaters[]` has `enabled=true` and `energy_sensor` configured
- **WHEN** backend reads daily water heater consumption
- **THEN** the value comes from that heater's `energy_sensor`

#### Scenario: Multiple water heaters daily energy
- **GIVEN** two entries in `water_heaters[]` have `enabled=true` and `energy_sensor` configured
- **WHEN** backend reads daily water heater consumption
- **THEN** the value equals the sum of both heaters' `energy_sensor` readings
