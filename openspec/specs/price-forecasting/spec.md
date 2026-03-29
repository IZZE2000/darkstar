## Purpose

Enable machine learning-based forecasting of Nordpool electricity spot prices to provide price outlooks and enable D+1 fallback before day-ahead auction publication.

## Requirements

### Requirement: Price forecast model training
The system SHALL train a LightGBM quantile regression model (p10/p50/p90) to predict raw Nordpool spot prices for horizons D+1 through D+7. The training target SHALL be `slot_observations.export_price_sek_kwh` (raw spot price, no fees/taxes). The model SHALL use a single model with `days_ahead` as a feature rather than per-horizon models.

#### Scenario: Model trains on paired price and weather data
- **WHEN** the training pipeline runs and sufficient paired (price + weather) data exists above the minimum sample threshold
- **THEN** the system SHALL train a LightGBM quantile regression model using historical forecast weather inputs paired with actual spot prices

#### Scenario: Cold-start gating prevents training with insufficient data
- **WHEN** the training pipeline runs and paired data is below the minimum sample threshold
- **THEN** the system SHALL skip price model training and log a message indicating insufficient data
- **AND** no price forecast model file SHALL be written

#### Scenario: Training follows existing schedule
- **WHEN** the Aurora training schedule triggers (configured `run_days` and `run_time`)
- **THEN** the price model SHALL train alongside the existing load and PV models

### Requirement: Price forecast feature engineering
The model SHALL use the following feature categories: calendar features (hour, day_of_week, month, is_weekend, is_holiday), regional wind index (from regional weather coordinates), local weather (temperature, cloud cover, solar radiation), price lags (same hour yesterday, same hour last week, trailing daily average), and `days_ahead` (integer 1-7).

#### Scenario: Calendar features extracted from target slot
- **WHEN** building features for a forecast slot
- **THEN** the system SHALL extract hour, day_of_week, month, is_weekend, and is_holiday from the target slot timestamp

#### Scenario: Price lag features computed from historical observations
- **WHEN** building features for a forecast slot
- **THEN** the system SHALL compute price lags from `slot_observations.export_price_sek_kwh`: same hour yesterday, same hour one week ago, and trailing 24-hour average
- **AND** missing lags SHALL be filled with NaN (LightGBM handles missing values natively)

#### Scenario: Days-ahead feature distinguishes horizons
- **WHEN** building features for a slot that is N days in the future
- **THEN** the `days_ahead` feature SHALL be set to N (integer 1-7)

### Requirement: Price forecast inference
The system SHALL generate price forecasts for D+1 through D+7 at 15-minute slot resolution. D+1 forecasts SHALL serve as fallback before the ~13:00 CET Nordpool day-ahead auction. Once real Nordpool D+1 prices are available, they SHALL take precedence over the D+1 forecast.

#### Scenario: Daily forecast generation
- **WHEN** the forecast pipeline runs and a trained price model exists
- **THEN** the system SHALL generate p10/p50/p90 spot price forecasts for all 15-minute slots from D+1 through D+7

#### Scenario: D+1 fallback before auction
- **WHEN** a downstream consumer requests prices and real Nordpool D+1 prices are not yet available (before ~13:00 CET)
- **THEN** the system SHALL provide the D+1 price forecast as a fallback

#### Scenario: Real prices replace D+1 forecast
- **WHEN** real Nordpool D+1 prices become available (after auction publication)
- **THEN** the system SHALL use real prices for D+1 instead of the forecast

#### Scenario: No forecast without trained model
- **WHEN** the forecast pipeline runs and no trained price model exists
- **THEN** the system SHALL produce no price forecasts and downstream consumers SHALL receive empty/null results

### Requirement: Price forecast persistence
Each price forecast record SHALL be persisted to a `price_forecasts` table in `planner_learning.db`. Each record SHALL store the weather feature values used at prediction time alongside the forecast output to enable honest training.

#### Scenario: Forecast record stores weather inputs
- **WHEN** a price forecast is generated for a target slot
- **THEN** the persisted record SHALL include: target slot timestamp, forecast issue timestamp, days_ahead, predicted spot price (p10/p50/p90), and the weather feature values (regional wind index, temperature, cloud cover, radiation) used at prediction time

#### Scenario: Forecast records queryable for training
- **WHEN** the training pipeline needs historical forecast-weather pairs
- **THEN** it SHALL query `price_forecasts` joined with `slot_observations` (on target slot) to get (weather_at_forecast_time, actual_spot_price) training pairs

### Requirement: Import/export price derivation
At inference time, forecasted import and export prices SHALL be derived from the raw spot price prediction by applying the same fee/VAT/tax logic used in `backend/core/prices.py`. The model SHALL NOT predict import prices directly.

#### Scenario: Import price derived from spot forecast
- **WHEN** a downstream consumer needs a forecasted import price
- **THEN** the system SHALL calculate it as: `(spot_forecast + grid_transfer_fee + energy_tax) * (1 + vat_percent/100)` using current config values

#### Scenario: Export price equals spot forecast
- **WHEN** a downstream consumer needs a forecasted export price
- **THEN** the system SHALL return the raw spot price forecast directly

### Requirement: Price forecast config toggle
A `price_forecast.enabled` config option SHALL exist (disabled by default). When disabled, no price forecasts SHALL be exposed to downstream consumers. Training and persistence MAY still occur to accumulate data.

#### Scenario: Toggle disabled by default
- **WHEN** a fresh system starts with default config
- **THEN** `price_forecast.enabled` SHALL be `false`

#### Scenario: Toggle gates downstream consumption
- **WHEN** `price_forecast.enabled` is `false`
- **THEN** API endpoints serving price forecasts to downstream consumers SHALL return empty/null results
- **AND** training and internal forecast persistence MAY continue

#### Scenario: Toggle enables downstream consumption
- **WHEN** `price_forecast.enabled` is `true` and a trained model exists with sufficient data
- **THEN** API endpoints SHALL return price forecast data to downstream consumers

### Requirement: Price forecast API endpoint
The backend SHALL expose a REST API endpoint for retrieving price forecasts. The endpoint SHALL return forecast data for D+1 through D+7 including p10/p50/p90 spot prices and derived import/export prices per 15-minute slot.

#### Scenario: Endpoint returns forecast data
- **WHEN** a client requests the price forecast endpoint and `price_forecast.enabled` is `true` and forecasts exist
- **THEN** the response SHALL include an array of slot records with: slot timestamp, spot_p10, spot_p50, spot_p90, import_p50, export_p50, and days_ahead

#### Scenario: Endpoint returns empty when disabled
- **WHEN** a client requests the price forecast endpoint and `price_forecast.enabled` is `false`
- **THEN** the response SHALL return an empty forecast array with a status indicating forecasting is disabled

#### Scenario: Endpoint returns empty when no model
- **WHEN** a client requests the price forecast endpoint and no trained model exists
- **THEN** the response SHALL return an empty forecast array with a status indicating insufficient training data
