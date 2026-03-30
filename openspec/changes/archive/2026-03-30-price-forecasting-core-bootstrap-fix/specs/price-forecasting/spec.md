## MODIFIED Requirements

### Requirement: Price forecast inference
The system SHALL generate price forecasts for D+1 through D+7 at 15-minute slot resolution. D+1 forecasts SHALL serve as fallback before the ~13:00 CET Nordpool day-ahead auction. Once real Nordpool D+1 prices are available, they SHALL take precedence over the D+1 forecast. When no trained model exists, the system SHALL still fetch regional weather and persist rows with null spot prediction columns to accumulate training data.

#### Scenario: Daily forecast generation
- **WHEN** the forecast pipeline runs and a trained price model exists
- **THEN** the system SHALL generate p10/p50/p90 spot price forecasts for all 15-minute slots from D+1 through D+7

#### Scenario: D+1 fallback before auction
- **WHEN** a downstream consumer requests prices and real Nordpool D+1 prices are not yet available (before ~13:00 CET)
- **THEN** the system SHALL provide the D+1 price forecast as a fallback
- **AND** the system SHALL only return rows where spot_p50 is not null

#### Scenario: Real prices replace D+1 forecast
- **WHEN** real Nordpool D+1 prices become available (after auction publication)
- **THEN** the system SHALL use real prices for D+1 instead of the forecast

#### Scenario: Weather accumulation without trained model
- **WHEN** the forecast pipeline runs and no trained price model exists
- **THEN** the system SHALL still fetch regional weather data and build feature rows for D+1 through D+7
- **AND** the system SHALL persist those rows with spot_p10, spot_p50, and spot_p90 set to null
- **AND** the system SHALL NOT return these rows to downstream consumers as price forecasts

### Requirement: Price forecast scheduling
The system SHALL call `generate_price_forecasts()` on two independent schedules: once on every training cycle (regardless of whether training succeeded), and once per day on a dedicated daily tick (e.g., 06:00). This ensures weather snapshots accumulate continuously from first install, enabling the model to train within approximately one week.

#### Scenario: Weather snapshots run on every training cycle
- **WHEN** the training orchestrator runs a training cycle
- **THEN** `generate_price_forecasts()` SHALL be called regardless of whether price model training succeeded or was skipped

#### Scenario: Daily weather snapshot tick
- **WHEN** the daily scheduler tick fires (independent of training schedule)
- **THEN** `generate_price_forecasts()` SHALL be called to persist a fresh weather snapshot for D+1 through D+7

### Requirement: Price forecast persistence
Each price forecast record SHALL be persisted to a `price_forecasts` table in `planner_learning.db`. Each record SHALL store the weather feature values used at prediction time alongside the forecast output to enable honest training. Records without spot predictions (weather-only rows) are valid and SHALL be stored with null spot columns.

#### Scenario: Forecast record stores weather inputs
- **WHEN** a price forecast is generated for a target slot
- **THEN** the persisted record SHALL include: target slot timestamp, forecast issue timestamp, days_ahead, predicted spot price (p10/p50/p90), and the weather feature values (regional wind index, temperature, cloud cover, radiation) used at prediction time

#### Scenario: Weather-only record stored during cold start
- **WHEN** a forecast row is persisted and no model was available at issue time
- **THEN** the record SHALL store all weather feature columns with their actual values
- **AND** spot_p10, spot_p50, and spot_p90 SHALL be null

#### Scenario: Forecast records queryable for training
- **WHEN** the training pipeline needs historical forecast-weather pairs
- **THEN** it SHALL query `price_forecasts` joined with `slot_observations` (on target slot) to get (weather_at_forecast_time, actual_spot_price) training pairs
- **AND** rows with null spot columns SHALL be included in this join (the spot columns are not training features)

## ADDED Requirements

### Requirement: D+1 fallback null safety
The D+1 fallback query SHALL filter out weather-only (null-prediction) rows before returning results to the planner. A row with a null spot_p50 SHALL never be served as a price forecast to downstream consumers.

#### Scenario: Fallback excludes null-prediction rows
- **WHEN** `get_d1_price_forecast_fallback()` queries the database and weather-only rows exist for D+1
- **THEN** those rows SHALL be excluded from the returned results
- **AND** if no non-null D+1 forecast rows exist, the function SHALL return None
