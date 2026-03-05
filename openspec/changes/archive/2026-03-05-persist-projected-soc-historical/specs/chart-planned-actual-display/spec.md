## ADDED Requirements

### Requirement: Chart lines use consistent smooth rendering style

ChartCard SHALL render all chart lines with a consistent smooth style using Chart.js tension parameter. Lines SHALL NOT use stepped rendering for power/energy values that represent continuous measurements.

#### Scenario: Actual PV line renders smoothly
- **WHEN** the Actual PV overlay line is displayed
- **THEN** the line SHALL use `tension: 0.4` for smooth Bezier curve rendering
- **AND** the line SHALL NOT use `stepped` property

#### Scenario: PV Forecast line renders smoothly
- **WHEN** the PV Forecast line is displayed
- **THEN** the line SHALL use `tension: 0.4` for smooth Bezier curve rendering
- **AND** the visual style SHALL match the Actual PV line

#### Scenario: Other power lines follow consistent style
- **WHEN** any power or energy line is rendered in the chart
- **THEN** the line SHALL use smooth rendering (`tension: 0.4`) unless a stepped display is semantically appropriate
