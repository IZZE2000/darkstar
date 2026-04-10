## MODIFIED Requirements

### Requirement: Grid Max Power Configuration UI

The system SHALL expose `system.grid.max_power_kw` in the Settings UI System tab, allowing users to configure their grid fuse hard limit.

#### Scenario: User configures grid max power
- **WHEN** user navigates to Settings > System tab
- **THEN** a "Grid Max Power (kW)" field is visible with helper text "HARD limit from your grid fuse. The planner will never exceed this for import or export."
- **AND** the field saves to `system.grid.max_power_kw` in config.yaml

#### Scenario: Planner respects grid max power limit
- **WHEN** planner generates a schedule
- **THEN** scheduled grid import SHALL NOT exceed `system.grid.max_power_kw`
- **AND** scheduled grid export SHALL NOT exceed `system.grid.max_power_kw`
- **AND** `max_import_power_kw` and `max_export_power_kw` in KeplerConfig are both set to this value
