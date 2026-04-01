## MODIFIED Requirements

### Requirement: Regional weather coordinate data file
The system SHALL maintain a `ml/regions.json` file that maps Nordpool price areas to lists of named weather coordinate sets. Each coordinate set SHALL have a key name, latitude, longitude, and human-readable label.

#### Scenario: SE1 through SE4 populated
- **WHEN** the system reads `ml/regions.json`
- **THEN** it SHALL find entries for price areas SE1, SE2, SE3, and SE4
- **AND** each entry SHALL contain at least a "local" coordinate plus relevant cross-border influence coordinates

#### Scenario: Each coordinate has required fields
- **WHEN** parsing a coordinate entry
- **THEN** each entry SHALL have `lat` (float), `lon` (float), and `label` (string) fields

#### Scenario: Unknown price area handled gracefully
- **WHEN** the user's configured `price_area` is not found in `ml/regions.json`
- **THEN** the system SHALL fall back to using only the user's configured home coordinates (from `config.yaml` latitude/longitude)
- **AND** the system SHALL log a warning indicating the price area is not mapped

### Requirement: Coordinate loader
The system SHALL provide a function that loads `ml/regions.json`, looks up the user's configured `price_area`, and returns the list of coordinate sets for weather fetching.

#### Scenario: Loader returns coordinates for configured area
- **WHEN** the loader is called with `price_area: "SE4"` and `ml/regions.json` contains SE4
- **THEN** it SHALL return the list of coordinate dicts for SE4

#### Scenario: File not found handled gracefully
- **WHEN** `ml/regions.json` does not exist
- **THEN** the loader SHALL fall back to home coordinates and log a warning
