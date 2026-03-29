## Purpose

Maintain regional weather coordinate mappings for Nordpool price areas and compute aggregated regional wind indices for price forecasting.

## Requirements

### Requirement: Regional weather coordinate data file
The system SHALL maintain a `data/regions.json` file that maps Nordpool price areas to lists of named weather coordinate sets. Each coordinate set SHALL have a key name, latitude, longitude, and human-readable label.

#### Scenario: SE1 through SE4 populated
- **WHEN** the system reads `data/regions.json`
- **THEN** it SHALL find entries for price areas SE1, SE2, SE3, and SE4
- **AND** each entry SHALL contain at least a "local" coordinate plus relevant cross-border influence coordinates

#### Scenario: Each coordinate has required fields
- **WHEN** parsing a coordinate entry
- **THEN** each entry SHALL have `lat` (float), `lon` (float), and `label` (string) fields

#### Scenario: Unknown price area handled gracefully
- **WHEN** the user's configured `price_area` is not found in `regions.json`
- **THEN** the system SHALL fall back to using only the user's configured home coordinates (from `config.yaml` latitude/longitude)
- **AND** the system SHALL log a warning indicating the price area is not mapped

### Requirement: Regional wind index computation
The system SHALL fetch wind speed data from all coordinates defined for the user's configured price area and compute a single averaged "regional wind index" feature for the ML pipeline.

#### Scenario: Wind index averaged from multiple coordinates
- **WHEN** the price area has 3 coordinate sets defined (e.g., local + 2 cross-border)
- **THEN** the system SHALL fetch `wind_speed_10m` from Open-Meteo for all 3 coordinates
- **AND** compute the regional wind index as the arithmetic mean of the 3 wind speed series

#### Scenario: Single coordinate fallback
- **WHEN** the price area has only 1 coordinate set (or falls back to home coordinates)
- **THEN** the regional wind index SHALL equal the single coordinate's wind speed values

#### Scenario: Partial fetch failure
- **WHEN** one coordinate's weather fetch fails but others succeed
- **THEN** the system SHALL compute the wind index from the available coordinates
- **AND** log a warning about the failed coordinate

### Requirement: Coordinate loader
The system SHALL provide a function that loads `data/regions.json`, looks up the user's configured `price_area`, and returns the list of coordinate sets for weather fetching.

#### Scenario: Loader returns coordinates for configured area
- **WHEN** the loader is called with `price_area: "SE4"` and `regions.json` contains SE4
- **THEN** it SHALL return the list of coordinate dicts for SE4

#### Scenario: File not found handled gracefully
- **WHEN** `data/regions.json` does not exist
- **THEN** the loader SHALL fall back to home coordinates and log a warning
