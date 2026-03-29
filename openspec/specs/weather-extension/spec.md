## Purpose

Support extended weather forecast horizons, wind speed parameters, and multi-coordinate fetching for advanced use cases like price forecasting.

## Requirements

### Requirement: Extended forecast horizon
The weather fetch SHALL support fetching up to 16-day forecasts from Open-Meteo (currently 2 days). The extended horizon is used by the price forecasting model; existing PV/load forecasts continue using their current horizon.

#### Scenario: 16-day forecast requested for price model
- **WHEN** the price forecasting pipeline requests weather data with `forecast_days=16`
- **THEN** the system SHALL fetch 16-day hourly weather data from Open-Meteo and return it at 15-minute resolution (interpolated)

#### Scenario: Existing PV forecast horizon unchanged
- **WHEN** the PV/load forecast pipeline requests weather data with default parameters
- **THEN** the system SHALL continue fetching the existing 2-day horizon (backward compatible)

### Requirement: Wind speed parameter
The weather fetch SHALL support fetching `wind_speed_10m` from Open-Meteo as a new hourly parameter, interpolated to 15-minute resolution alongside existing parameters.

#### Scenario: Wind speed included in weather response
- **WHEN** weather data is fetched with wind speed enabled
- **THEN** the response DataFrame SHALL include a `wind_speed_10m` column with values in m/s at 15-minute resolution

#### Scenario: Wind speed interpolated consistently
- **WHEN** hourly wind speed data is resampled to 15-minute resolution
- **THEN** the system SHALL use the same linear interpolation method used for existing parameters (temperature, cloud cover, radiation)

### Requirement: Multi-coordinate weather fetching
The weather module SHALL support fetching weather data for a list of coordinate sets (not just the single home location). Each coordinate produces its own weather DataFrame.

#### Scenario: Multiple coordinates fetched
- **WHEN** the system requests weather for 3 coordinate sets
- **THEN** the system SHALL make separate Open-Meteo requests for each coordinate
- **AND** return a weather DataFrame per coordinate

#### Scenario: Caching per coordinate
- **WHEN** weather is fetched for a coordinate that was recently fetched
- **THEN** the cached result SHALL be returned (using existing TTL-based caching pattern)
- **AND** the cache key SHALL distinguish between different coordinates

#### Scenario: Individual coordinate failure isolated
- **WHEN** one coordinate's Open-Meteo request fails (timeout, DNS, etc.)
- **THEN** the failure SHALL NOT prevent other coordinates from being fetched
- **AND** the failed coordinate SHALL return an empty DataFrame
