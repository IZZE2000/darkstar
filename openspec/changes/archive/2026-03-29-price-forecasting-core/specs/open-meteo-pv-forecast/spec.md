## MODIFIED Requirements

### Requirement: Open-Meteo Forecast Data for All Slots

The backend SHALL provide Open-Meteo forecast data for all 72 hours (yesterday, today, and tomorrow) using the forecast API with `past_days=1` and `forecast_days=2`. The fetching mechanism MUST be completely asynchronous to prevent blocking the main event loop during API timeouts or DNS failures. The weather fetch function SHALL accept configurable `forecast_days` and optional additional parameters (e.g., `wind_speed_10m`) without breaking existing callers that use default values.

#### Scenario: Yesterday's slots show hindcast data
- **WHEN** the Aurora dashboard generates forecast slots
- **THEN** yesterday's slots SHALL show Open-Meteo hindcast data (what the model would have predicted)

#### Scenario: Today and tomorrow's slots show forecast data
- **WHEN** the Aurora dashboard generates forecast slots
- **THEN** today and tomorrow's slots SHALL show Open-Meteo forecast data

#### Scenario: Open-Meteo Fetch Timeout
- **WHEN** the Open-Meteo API is unreachable due to network or DNS failure
- **THEN** the asynchronous fetch operation SHALL time out without blocking the main event loop
- **AND** the system SHALL gracefully return an empty dataset for that execution cycle

#### Scenario: Extended forecast days parameter
- **WHEN** a caller requests weather with `forecast_days=16`
- **THEN** the function SHALL fetch 16 days of forecast data from Open-Meteo
- **AND** default callers (no explicit forecast_days) SHALL continue receiving 2-day forecasts

#### Scenario: Additional weather parameters
- **WHEN** a caller requests weather with additional parameters (e.g., `wind_speed_10m`)
- **THEN** the response SHALL include those parameters alongside existing ones (temperature, cloud cover, radiation)
- **AND** default callers (no explicit extra parameters) SHALL receive only the original parameter set
