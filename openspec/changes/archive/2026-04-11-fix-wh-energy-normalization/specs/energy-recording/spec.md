## MODIFIED Requirements

### Requirement: Automatic Unit Normalization
The system SHALL automatically normalize cumulative energy sensor values to kWh, supporting Wh, kWh, and MWh units based on the sensor's `unit_of_measurement` attribute. When no unit is specified, the system SHALL use a magnitude-based heuristic to detect Wh values and convert accordingly.

#### Scenario: Sensor reports in Watt-hours
- **WHEN** a cumulative sensor reports `500000` with `unit_of_measurement: "Wh"`
- **THEN** the system SHALL normalize to `500.0 kWh`
- **AND** delta calculations SHALL use the normalized value

#### Scenario: Sensor reports in kilowatt-hours
- **WHEN** a cumulative sensor reports `500.0` with `unit_of_measurement: "kWh"`
- **THEN** the system SHALL use the value as-is

#### Scenario: Sensor reports in megawatt-hours
- **WHEN** a cumulative sensor reports `0.5` with `unit_of_measurement: "MWh"`
- **THEN** the system SHALL normalize to `500.0 kWh`

#### Scenario: Sensor reports in Wh with non-standard unit string
- **WHEN** a cumulative sensor reports `5675983` with `unit_of_measurement: "W·h"` or `"W h"` or `"watthour"` or any case variant of Wh
- **THEN** the system SHALL normalize to `5675.983 kWh`

#### Scenario: Sensor reports large value with no unit attribute
- **WHEN** a cumulative sensor reports `5675983` with no `unit_of_measurement` attribute (None or missing)
- **AND** the value exceeds the Wh detection threshold (default 100,000)
- **THEN** the system SHALL assume Wh and normalize to `5675.983 kWh`
- **AND** the system SHALL log an info message: "Energy normalization: X (no unit) → Y kWh (Wh inferred from magnitude)"

#### Scenario: Sensor reports small value with no unit attribute
- **WHEN** a cumulative sensor reports `500.0` with no `unit_of_measurement` attribute
- **AND** the value is at or below the Wh detection threshold
- **THEN** the system SHALL assume kWh and use `500.0` as-is

## ADDED Requirements

### Requirement: Unit Propagation in History Processing

The `get_load_profile_from_ha` function SHALL propagate the `unit_of_measurement` from the first HA history state entry to all subsequent entries that lack attributes. The HA history API only includes attributes on the first entry in a response series — the function MUST NOT rely on every state entry having its own `unit_of_measurement`.

#### Scenario: HA history returns attributes only on first entry
- **WHEN** the first state entry has `attributes: {"unit_of_measurement": "Wh"}` and all subsequent entries have `attributes: {}`
- **THEN** the function SHALL apply the `"Wh"` unit to ALL state entries when normalizing
- **AND** all cumulative values SHALL be consistently divided by 1000

#### Scenario: No state entry has attributes
- **WHEN** all state entries have `attributes: {}` (no `unit_of_measurement` anywhere)
- **THEN** the function SHALL pass `None` as the unit to normalization
- **AND** the magnitude-based heuristic SHALL apply as fallback

#### Scenario: Unit changes mid-series
- **WHEN** a later state entry introduces a different `unit_of_measurement` (e.g., sensor reconfigured)
- **THEN** the function SHALL adopt the new unit from that entry onward

### Requirement: Load Profile Sanity Bound
The `get_load_profile_from_ha` function SHALL validate the computed daily total before returning. If the daily total exceeds a reasonable residential threshold, the function SHALL discard the profile and return the dummy fallback.

#### Scenario: Normal daily total passes validation
- **WHEN** `get_load_profile_from_ha` computes a daily total of `25.0 kWh/day`
- **THEN** the function SHALL return the computed profile normally

#### Scenario: Absurd daily total triggers fallback
- **WHEN** `get_load_profile_from_ha` computes a daily total exceeding `500 kWh/day`
- **THEN** the function SHALL log a warning with the computed total and entity ID
- **AND** the function SHALL return the dummy load profile instead

### Requirement: Unit Detection Logging
The normalization function SHALL log the detected unit and conversion result at debug level for every cumulative sensor read, enabling diagnosis of sensor configuration issues.

#### Scenario: Unit detected from attribute
- **WHEN** the normalization function processes a value of `500000` with `unit_of_measurement: "Wh"`
- **THEN** the function SHALL log at debug level: "Energy normalization: 500000 Wh → 500.0 kWh (from unit_of_measurement)"

#### Scenario: Unit inferred from magnitude
- **WHEN** the normalization function processes a value of `5675983` with no `unit_of_measurement`
- **THEN** the function SHALL log at info level: "Energy normalization: 5675983 (no unit) → 5675.983 kWh (Wh inferred from magnitude)"
