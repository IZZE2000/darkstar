## MODIFIED Requirements

### Requirement: Aurora dashboard API returns forecast data with history series
The `/aurora/dashboard` API SHALL return forecast horizon data including historical actuals and per-array breakdowns in the correct structure.

#### Scenario: Dashboard returns history series in horizon object
- **WHEN** the Aurora dashboard API is called
- **THEN** the response SHALL contain `horizon.history_series` with `pv` and `load` arrays
- **AND** each entry SHALL have `timestamp`, `value`, and optional `confidence`

#### Scenario: Open-Meteo forecast data is attached to all slots
- **WHEN** the Aurora dashboard generates forecast slots
- **THEN** each slot SHALL include Open-Meteo forecast data using forecast API with `past_days=1` and `forecast_days=2`
- **AND** yesterday's slots SHALL show hindcast data (what the model predicted)
- **AND** today and tomorrow's slots SHALL show forecast data
- **AND** the slot SHALL include per-array PV forecasts when multiple arrays are configured

#### Scenario: Per-array forecasts display correctly
- **WHEN** the system is configured with multiple solar arrays
- **THEN** the dashboard SHALL display separate forecast lines for each array
- **AND** each array line SHALL be labeled with the array name from configuration

#### Scenario: 72-hour forecast window
- **WHEN** the Aurora dashboard is displayed
- **THEN** the forecast horizon SHALL cover 72 hours (yesterday + today + tomorrow)
- **AND** the horizon start SHALL be 00:00 of the previous day
- **AND** the horizon end SHALL be 00:00 of the day after tomorrow
