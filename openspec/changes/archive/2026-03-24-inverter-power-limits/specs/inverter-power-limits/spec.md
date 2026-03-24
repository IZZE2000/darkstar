## ADDED Requirements

### Requirement: Inverter AC Output Power Configuration

The system SHALL provide a `system.inverter.max_ac_power_kw` configuration key representing the maximum AC power output of the hybrid inverter. This is the combined ceiling for PV conversion and battery discharge on the AC bus.

#### Scenario: User configures inverter AC power limit
- **WHEN** user sets `system.inverter.max_ac_power_kw` to `10.0` in config
- **THEN** the value is stored and available to the planner adapter

#### Scenario: Config key exposed in Settings UI
- **WHEN** user navigates to Settings > System tab
- **THEN** an "Inverter Max AC Power (kW)" number field is visible in the system section
- **AND** the field has a tooltip: "Maximum AC power your inverter can produce. Limits combined PV + battery discharge output."
- **AND** the field saves to `system.inverter.max_ac_power_kw` in config

#### Scenario: Config key missing triggers validation warning
- **WHEN** `system.inverter.max_ac_power_kw` is not set in config
- **AND** user has `system.has_battery = true` or `system.has_solar = true`
- **THEN** config validation SHALL return a warning with guidance to set the inverter AC power limit

### Requirement: Inverter DC Input Power Configuration

The system SHALL provide a `system.inverter.max_dc_input_kw` configuration key representing the maximum DC power the inverter can accept from PV strings.

#### Scenario: User configures inverter DC input limit
- **WHEN** user sets `system.inverter.max_dc_input_kw` to `12.0` in config
- **THEN** the value is stored and available to the planner adapter

#### Scenario: Config key exposed in Settings UI
- **WHEN** user navigates to Settings > System tab
- **THEN** an "Inverter Max DC Input (kW)" number field is visible in the system section
- **AND** the field has a tooltip: "Maximum DC power from PV strings your inverter accepts. PV forecast is clipped to this value."
- **AND** the field saves to `system.inverter.max_dc_input_kw` in config

#### Scenario: Config key missing triggers validation warning
- **WHEN** `system.inverter.max_dc_input_kw` is not set in config
- **AND** user has `system.has_solar = true`
- **THEN** config validation SHALL return a warning with guidance to set the inverter DC input limit

### Requirement: Planner Clips PV Forecast by DC Input Limit

When `system.inverter.max_dc_input_kw` is configured, the planner adapter SHALL clip each slot's PV energy to `min(pv_kwh, max_dc_input_kw * slot_hours)` before passing it to the solver.

#### Scenario: PV forecast exceeds DC input limit
- **GIVEN** `system.inverter.max_dc_input_kw` is `12.0`
- **AND** a 15-minute slot has `pv_kwh = 4.5` (equivalent to 18kW average)
- **WHEN** the planner adapter builds solver input
- **THEN** the slot's `pv_kwh` SHALL be clipped to `3.0` (12.0 * 0.25)

#### Scenario: PV forecast below DC input limit
- **GIVEN** `system.inverter.max_dc_input_kw` is `12.0`
- **AND** a 15-minute slot has `pv_kwh = 2.0` (equivalent to 8kW average)
- **WHEN** the planner adapter builds solver input
- **THEN** the slot's `pv_kwh` SHALL remain `2.0` (no clipping needed)

#### Scenario: DC input limit not configured
- **WHEN** `system.inverter.max_dc_input_kw` is not set
- **THEN** no PV clipping SHALL occur (current behavior preserved)

### Requirement: Solver Enforces Inverter AC Output Constraint

When `max_inverter_ac_kw` is set in `KeplerConfig`, the solver SHALL constrain battery discharge plus PV contribution to not exceed the inverter's AC output capacity per slot.

#### Scenario: Battery discharge limited by AC ceiling during high PV
- **GIVEN** `max_inverter_ac_kw` is `10.0`
- **AND** a 15-minute slot has (already clipped) `pv_kwh = 2.25` (9kW average)
- **WHEN** the solver optimizes
- **THEN** `discharge[t] + pv_kwh <= 10.0 * 0.25 = 2.5 kWh`
- **AND** maximum discharge in this slot SHALL be `0.25 kWh` (1kW average)

#### Scenario: Full discharge capacity available at night
- **GIVEN** `max_inverter_ac_kw` is `10.0`
- **AND** a slot has `pv_kwh = 0.0`
- **WHEN** the solver optimizes
- **THEN** `discharge[t] <= 10.0 * 0.25 = 2.5 kWh`
- **AND** battery discharge is limited only by `min(max_discharge_power_kw, max_inverter_ac_kw)`

#### Scenario: AC output limit not configured
- **WHEN** `max_inverter_ac_kw` is not set in `KeplerConfig`
- **THEN** no inverter AC constraint SHALL be applied (current behavior preserved)

### Requirement: Config Migration for Removed Keys

The system SHALL migrate `system.inverter.max_power_kw` to `system.inverter.max_ac_power_kw` during config migration.

#### Scenario: Old max_power_kw key exists
- **GIVEN** config contains `system.inverter.max_power_kw: 10.0`
- **AND** config does not contain `system.inverter.max_ac_power_kw`
- **WHEN** config migration runs
- **THEN** `system.inverter.max_ac_power_kw` SHALL be set to `10.0`
- **AND** `system.inverter.max_power_kw` SHALL be removed

#### Scenario: New key already exists (no overwrite)
- **GIVEN** config contains both `system.inverter.max_power_kw: 8.0` and `system.inverter.max_ac_power_kw: 10.0`
- **WHEN** config migration runs
- **THEN** `system.inverter.max_ac_power_kw` SHALL remain `10.0`
- **AND** `system.inverter.max_power_kw` SHALL be removed

### Requirement: Remove Orphan Config Keys

The system SHALL remove the following unused config keys:
- `system.inverter.max_power_kw` (replaced by `max_ac_power_kw`)
- `executor.controller.inverter_ac_limit_kw` (never used in any code path)

#### Scenario: Default config does not contain removed keys
- **WHEN** `config.default.yaml` is inspected
- **THEN** it SHALL NOT contain `system.inverter.max_power_kw`
- **AND** it SHALL NOT contain `executor.controller.inverter_ac_limit_kw`
- **AND** it SHALL contain `system.inverter.max_ac_power_kw` and `system.inverter.max_dc_input_kw`
