## ADDED Requirements

### Requirement: Kepler plans water heater boost from forecast excess PV

The Kepler solver SHALL schedule water heater boost (binary on/off per slot) only in slots where forecast PV exceeds all forecast consumption (load + minimum water heating + minimum EV charging). Excess slots are pre-calculated from raw forecasts before the MILP runs and passed in as fixed parameters. No daily energy budget — the solver's energy balance naturally handles economics (boost competes with grid export), and the executor's thermostat handles physics.

#### Scenario: Excess PV slot gets water heater boost
- **WHEN** slot 14 has forecast excess PV
- **AND** the excess PV sink is `water_heater_boost`
- **THEN** the MILP SHALL create a boost binary variable for each water heater in that slot
- **AND** boost SHALL NOT appear in slots without forecast excess PV

#### Scenario: No excess PV means no boost
- **WHEN** there are zero excess PV slots across the horizon
- **AND** the excess PV sink is `water_heater_boost`
- **THEN** no boost slots appear in the schedule output

#### Scenario: Boost disabled when sink is not water_heater_boost
- **WHEN** the excess PV sink is `custom_entity` or `disabled`
- **THEN** no boost variables are created
- **AND** water heaters only get their normal minimum kWh

### Requirement: Boost constrained to forecast excess PV slots

Before the MILP runs, the solver SHALL pre-calculate per-slot excess PV flags from raw forecasts: `excess[t] = max(0, pv_forecast[t] - load_forecast[t] - min_water_heat_forecast[t] - min_ev_forecast[t]) > 0`. Boost decision variables are then constrained to slots where this flag is true. A single MILP solve is sufficient — no re-solve required.

#### Scenario: Boost competes with export in energy balance
- **WHEN** slot 14 has 1.5 kWh of forecast excess PV
- **AND** export price is 1.0 SEK/kWh
- **THEN** the solver SHALL decide whether to boost the water heater or export based on economics

#### Scenario: Boost shares slot with normal heating
- **WHEN** a water heater already has normal heating scheduled in slot 14
- **AND** slot 14 has additional excess PV
- **THEN** the heater SHALL run continuously (already on) and the boost flag SHALL be set

### Requirement: Schedule output includes water heater boost flag

The schedule output SHALL include a `water_heating_boost` field in each slot indicating which heaters are in boost mode.

#### Scenario: Boost slot in schedule output
- **WHEN** heater A has boost scheduled in slot 14
- **THEN** the slot output SHALL contain `water_heating_boost: {"main_tank": true}`
- **AND** the normal `water_heating_kw` field SHALL include both normal and boost energy

#### Scenario: No boost in slot output
- **WHEN** no heater has boost in slot 8
- **THEN** the slot output SHALL contain `water_heating_boost: {}` or no boost entries

### Requirement: Custom HA entity toggles during excess PV slots

The executor SHALL toggle a user-configured HA entity on during slots where the schedule indicates excess PV and off otherwise.

#### Scenario: Custom entity turned on during excess PV slot
- **WHEN** the schedule has excess PV in slot 14
- **AND** the excess PV sink is configured as `custom_entity`
- **WHEN** executor processes slot 14
- **THEN** the configured entity SHALL be set to `on_value`

#### Scenario: Custom entity turned off during non-excess slot
- **WHEN** the schedule has no excess PV in slot 8
- **AND** the excess PV sink is configured as `custom_entity`
- **WHEN** executor processes slot 8
- **THEN** the configured entity SHALL be set to `off_value`

#### Scenario: Custom entity skipped when sink is disabled
- **WHEN** the excess PV sink is configured as `disabled`
- **WHEN** executor processes any slot
- **THEN** no custom entity actions are performed

#### Scenario: Custom entity set to off_value on slot failure
- **WHEN** the executor enters `SLOT_FAILURE_FALLBACK`
- **AND** the excess PV sink is configured as `custom_entity`
- **THEN** the configured entity SHALL be set to `off_value`
- **AND** the entity SHALL NOT be left in an active state
