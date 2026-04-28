## MODIFIED Requirements

### Requirement: Probabilistic data retrieval from Aurora database
The system SHALL correctly retrieve and return probabilistic forecast bounds (P10/P90) from the Aurora ML database to support S-Index probabilistic calculations. When `price_forecast.enabled` is true, the system SHALL additionally retrieve daily average spot price forecast data (p50) for use by the safety floor calculation.

#### Scenario: Successfully retrieve daily probabilistic aggregates
- **WHEN** the planner requests forecast data via `_get_forecast_data_aurora()`
- **THEN** the function SHALL return daily aggregates for PV and Load P10/P90 bounds
- **AND** the data SHALL be accessible via the `daily_probabilistic` key in the return value

#### Scenario: Correctly access nested probabilistic fields
- **GIVEN** `get_forecast_slots()` returns records with nested structure `{"probabilistic": {"pv_p10": X, ...}}`
- **WHEN** `_get_forecast_data_aurora()` processes extended records
- **THEN** it SHALL access P10/P90 values via `rec.get("probabilistic", {}).get("pv_p10")` pattern
- **AND** apply PV and Load corrections to the probabilistic bounds

#### Scenario: Aggregate probabilistic data by date
- **GIVEN** extended forecast records with probabilistic bounds and correction values
- **WHEN** the function aggregates daily totals
- **THEN** it SHALL sum `pv_p10 + pv_correction` for each date
- **AND** it SHALL sum `load_p10 + load_correction` for each date
- **AND** it SHALL produce four dictionaries: `daily_pv_p10`, `daily_pv_p90`, `daily_load_p10`, `daily_load_p90`

#### Scenario: Return complete forecast result structure
- **WHEN** `_get_forecast_data_aurora()` completes successfully
- **THEN** the return value SHALL contain:
  - `slots`: list of slot-level forecasts
  - `daily_pv_forecast`: dict of daily PV totals
  - `daily_load_forecast`: dict of daily Load totals
  - `daily_probabilistic`: dict with keys `pv_p10`, `pv_p90`, `load_p10`, `load_p90`

#### Scenario: Retrieve price forecast data when enabled
- **WHEN** `price_forecast.enabled` is true
- **AND** price forecast records exist in the `price_forecasts` table
- **THEN** the return value SHALL additionally contain a `price_forecast` key with daily average spot p50 values keyed by ISO date string
- **AND** a `trailing_avg_spot` key with the 14-day trailing average from `slot_observations.export_price_sek_kwh`

#### Scenario: Price forecast data absent when disabled
- **WHEN** `price_forecast.enabled` is false or absent
- **THEN** the return value SHALL NOT contain `price_forecast` or `trailing_avg_spot` keys
- **AND** existing return structure SHALL be unchanged
