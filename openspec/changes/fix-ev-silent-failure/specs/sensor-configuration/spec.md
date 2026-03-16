## ADDED Requirements

### Requirement: Settings UI shows Energy sensor field for EV chargers
The Settings EV tab SHALL display an "Energy sensor" field for each EV charger entry, positioned immediately after the existing "Power sensor" field. The field SHALL use an HA entity dropdown (same pattern as other sensor fields). It SHALL include a "?" tooltip reading: "Cumulative energy counter for this charger. Used for accurate load isolation — how much energy the EV consumed each slot. Recommended for clean training data."

#### Scenario: Energy sensor field appears in EV tab
- **WHEN** the user navigates to Settings > EV
- **THEN** each EV charger entry SHALL show an "Energy sensor" field directly below the "Power sensor" field

#### Scenario: Energy sensor field is optional
- **WHEN** the user saves the EV configuration without filling in `energy_sensor`
- **THEN** the configuration SHALL save successfully with `energy_sensor: ''`
- **AND** no validation error SHALL be shown

#### Scenario: User fills in energy sensor entity
- **WHEN** the user selects an entity from the "Energy sensor" dropdown and saves
- **THEN** the config SHALL persist `energy_sensor: <entity_id>` on that `ev_chargers[]` entry

### Requirement: Settings UI shows Energy sensor field for water heaters
The Settings Water tab SHALL display an "Energy sensor" field for each water heater entry, positioned immediately after the existing "Power sensor" (sensor) field. The field SHALL use an HA entity dropdown and include a "?" tooltip reading: "Cumulative energy counter for this heater. Used for accurate load isolation — how much energy the heater consumed each slot. Recommended for clean training data."

#### Scenario: Energy sensor field appears in Water tab
- **WHEN** the user navigates to Settings > Water
- **THEN** each water heater entry SHALL show an "Energy sensor" field directly below the "Power sensor" field

#### Scenario: Energy sensor field is optional
- **WHEN** the user saves the Water configuration without filling in `energy_sensor`
- **THEN** the configuration SHALL save successfully with `energy_sensor: ''`

### Requirement: Power sensor tooltip updated for EV chargers
The "Power sensor" field tooltip for EV chargers SHALL be updated to reflect its specific role now that a separate "Energy sensor" exists for load isolation.

#### Scenario: Updated EV Power sensor tooltip
- **WHEN** the user hovers the "?" tooltip on the EV "Power sensor" field
- **THEN** the tooltip text SHALL read: "Real-time power reading for this charger. Used for live monitoring and dashboard display."
- **AND** the tooltip SHALL NOT mention load disaggregation

### Requirement: Power sensor tooltip updated for water heaters
The "Power sensor" field tooltip for water heaters SHALL be updated to reflect its specific role now that a separate "Energy sensor" exists for load isolation.

#### Scenario: Updated Water Power sensor tooltip
- **WHEN** the user hovers the "?" tooltip on the Water Heater "Power sensor" field
- **THEN** the tooltip text SHALL read: "Real-time power reading for this heater. Used for live monitoring and dashboard display."
- **AND** the tooltip SHALL NOT mention load disaggregation
