# Capability: Grid Power Limits

## Purpose

Provides UI configuration for grid fuse hard limit (`system.grid.max_power_kw`), ensuring the planner never schedules power imports that exceed the physical grid connection capacity.

## Requirements

### Requirement: Grid Max Power Configuration UI

The system SHALL expose `system.grid.max_power_kw` in the Settings UI System tab, allowing users to configure their grid fuse hard limit.

#### Scenario: User configures grid max power
- **WHEN** user navigates to Settings > System tab
- **THEN** a "Grid Max Power (kW)" field is visible with helper text "HARD limit from your grid fuse. The planner will never exceed this."
- **AND** the field saves to `system.grid.max_power_kw` in config.yaml

#### Scenario: Planner respects grid max power limit
- **WHEN** planner generates a schedule
- **THEN** scheduled grid import SHALL NOT exceed `system.grid.max_power_kw`
- **AND** `max_import_power_kw` in KeplerConfig is set to this value

### Requirement: PV Dump Threshold Field Visible

The system SHALL display `executor.override.excess_pv_threshold_kw` in the Settings Water tab when both solar and water heater are enabled.

#### Scenario: PV dump threshold visible when conditions met
- **WHEN** user has `system.has_solar = true` AND `system.has_water_heater = true`
- **AND** user navigates to Settings > Water tab > Temperatures section
- **THEN** "PV Dump Threshold (kW)" field is visible
- **AND** helper text explains "Surplus PV power required to trigger water heating"

#### Scenario: PV dump threshold hidden when conditions not met
- **WHEN** user has `system.has_solar = false` OR `system.has_water_heater = false`
- **THEN** "PV Dump Threshold (kW)" field is NOT visible
