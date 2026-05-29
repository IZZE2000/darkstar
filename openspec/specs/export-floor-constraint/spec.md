## Purpose

TBD — Export SoC floor constraint for the Kepler MILP solver.

## Requirements

### Requirement: Export SoC Floor Constraint in Kepler MILP
The Kepler solver SHALL enforce an export-floor SoC constraint: grid export SHALL only be allowed in slot `t` when `soc[t]` is at or above `export_floor_kwh` (derived from `export_floor_soc_percent`). This SHALL be implemented as a soft constraint using a per-slot binary variable `is_exporting[t]` and a per-slot slack variable `export_floor_violation[t] >= 0`, penalized in the objective at `EXPORT_FLOOR_PENALTY` (1000 SEK/kWh).

The constraint SHALL only be active when both `enable_export == True` AND `export_floor_soc_percent is not None`. When inactive, no additional variables or constraints SHALL be added.

#### Scenario: Export blocked when projected SoC is below floor
- **GIVEN** `export_floor_soc_percent = 20`, `capacity_kwh = 34.2` (floor = 6.84 kWh), `min_soc_percent = 10`
- **AND** projected `soc[t] = 5.0 kWh` (below floor)
- **WHEN** the solver optimizes slot `t`
- **THEN** `is_exporting[t]` SHALL be 0
- **AND** `grid_export[t]` SHALL be 0

#### Scenario: Export allowed when projected SoC is above floor
- **GIVEN** `export_floor_soc_percent = 20`, `capacity_kwh = 34.2` (floor = 6.84 kWh)
- **AND** projected `soc[t] = 10.0 kWh` (above floor)
- **WHEN** the solver optimizes slot `t` and export is economically optimal
- **THEN** `is_exporting[t]` SHALL be 1
- **AND** `grid_export[t]` SHALL be allowed up to `max_export_power_kw`

#### Scenario: Soft violation allowed under extreme economic pressure
- **GIVEN** `export_floor_soc_percent = 20`, `capacity_kwh = 34.2` (floor = 6.84 kWh)
- **AND** projected `soc[t] = 5.0 kWh` (below floor)
- **AND** export price is 10 SEK/kWh (extreme spike)
- **WHEN** the solver determines the export revenue exceeds the floor penalty
- **THEN** the solver MAY allow `export_floor_violation[t] > 0`
- **AND** the penalty SHALL be reflected in the total cost

#### Scenario: Constraint inactive when enable_export is False
- **GIVEN** `enable_export = False`
- **WHEN** the solver builds constraints
- **THEN** no `is_exporting[t]` binary variable SHALL be created
- **AND** the existing `grid_export[t] == 0` constraint SHALL apply unchanged

#### Scenario: Constraint inactive when export_floor_soc_percent is None
- **GIVEN** `export_floor_soc_percent = None`
- **WHEN** the solver builds constraints
- **THEN** no export-floor constraint SHALL be added
- **AND** export decisions SHALL be based solely on economics and `min_soc`

#### Scenario: Floor higher than min_soc preserves battery buffer
- **GIVEN** `export_floor_soc_percent = 20`, `min_soc_percent = 5`
- **WHEN** the solver plans exports
- **THEN** exports SHALL only occur when `soc[t] >= export_floor_kwh`
- **AND** non-export discharge (self-consumption) SHALL still respect `min_soc_kwh` only
