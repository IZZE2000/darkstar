## MODIFIED Requirements

### Requirement: Open-Meteo Forecast Data for All Slots

The backend SHALL provide Open-Meteo forecast data for all 72 hours (yesterday, today, and tomorrow) using the forecast API with `past_days=1` and `forecast_days=2`. The fetching mechanism MUST be completely asynchronous to prevent blocking the main event loop during API timeouts or DNS failures.

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
