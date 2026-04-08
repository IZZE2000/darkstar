## ADDED Requirements

### Requirement: Price forecast accuracy API endpoint
The backend SHALL provide a `GET /api/price-forecast/accuracy` endpoint that returns D+1 forecast accuracy metrics computed from historical forecast-vs-actual comparisons.

#### Scenario: Accuracy data available
- **WHEN** the endpoint is called and at least 2 days of D+1 forecast-vs-actual paired data exist
- **THEN** the response SHALL include `enabled: true`, `d1_mae` (mean absolute error of D+1 p50 vs actual spot price in SEK/kWh), `d1_bias` (mean signed error), `sample_days` (number of days in computation), and `status: "ok"`

#### Scenario: Insufficient data for accuracy
- **WHEN** the endpoint is called and fewer than 2 days of paired data exist
- **THEN** the response SHALL include `enabled: true`, `d1_mae: null`, `d1_bias: null`, `sample_days: 0`, and `status: "insufficient_data"`

#### Scenario: Price forecasting disabled
- **WHEN** `price_forecast.enabled` is `false`
- **THEN** the response SHALL include `enabled: false`, `d1_mae: null`, `d1_bias: null`, and `status: "disabled"`

#### Scenario: Accuracy computation uses 7-day rolling window
- **WHEN** computing D+1 accuracy
- **THEN** the system SHALL use the most recent 7 days of D+1 forecast-vs-actual pairs
- **AND** MAE SHALL be computed as `mean(|spot_p50 - export_price_sek_kwh|)` across all matched slots

### Requirement: Price MAE displayed in Aurora KPI strip
The KPI strip on the Aurora page SHALL display a Price Forecast MAE metric when price forecasting is enabled, replacing the "Max Price Spread" KPI.

#### Scenario: Price MAE shown when forecast enabled
- **WHEN** the Aurora page renders and `price_forecast.enabled` is `true`
- **THEN** the KPI strip SHALL display a "Price Forecast Error" card showing the D+1 MAE value in SEK/kWh with a "MAE (7d)" sublabel
- **AND** this card SHALL replace the "Max Price Spread" card in the same grid position

#### Scenario: Max Price Spread shown when forecast disabled
- **WHEN** the Aurora page renders and `price_forecast.enabled` is `false`
- **THEN** the KPI strip SHALL display the original "Max Price Spread" card (no changes)

#### Scenario: Price MAE not yet available
- **WHEN** price forecasting is enabled but accuracy data returns `d1_mae: null`
- **THEN** the KPI card SHALL display "N/A" as the value (same pattern as PV/Load MAE)

### Requirement: KPI strip accepts price accuracy data
The `KPIStrip` component SHALL accept an optional `priceAccuracy` prop containing the accuracy endpoint response.

#### Scenario: Prop passed when price forecast enabled
- **WHEN** the Aurora page fetches dashboard data and `price_forecast.enabled` is `true`
- **THEN** it SHALL also fetch `GET /api/price-forecast/accuracy` and pass the result as `priceAccuracy` prop to `KPIStrip`

#### Scenario: Prop omitted when price forecast disabled
- **WHEN** `price_forecast.enabled` is `false`
- **THEN** the `priceAccuracy` prop SHALL be `undefined` and the KPI strip renders its default 4 metrics
