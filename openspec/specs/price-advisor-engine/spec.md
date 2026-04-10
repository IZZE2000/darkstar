## Purpose

Enable intelligent energy cost optimization by providing price-aware recommendations through the analyst endpoint, helping users make informed decisions about when to run heavy loads based on forecasted electricity prices.

## Requirements

### Requirement: Price-aware advice rules in analyst endpoint
The existing `GET /api/analyst/advice` endpoint SHALL include price-related advice items with `category: "price"` when `price_forecast.enabled` is `true` and forecast data is available.

#### Scenario: Cheapest day ahead
- **WHEN** any day in D+1 through D+7 has an average spot p50 that is 30% or more below today's average spot price
- **THEN** the advisor SHALL emit an advice item: `category: "price"`, `priority: "info"`, with a message indicating the percentage drop and which day (e.g., "Prices drop ~40% on Thursday. Consider deferring heavy loads.")

#### Scenario: Prices rising short-term
- **WHEN** every day from D+1 through D+3 has a higher average spot p50 than today
- **THEN** the advisor SHALL emit an advice item: `category: "price"`, `priority: "info"`, with a message indicating today is the cheapest day in the next 3 days

#### Scenario: Cheap overnight window
- **WHEN** tonight's 22:00-06:00 average spot p50 is 25% or more below the full-day average spot p50
- **THEN** the advisor SHALL emit an advice item: `category: "price"`, `priority: "info"`, with a message indicating the overnight window is cheapest

#### Scenario: Price forecast disabled
- **WHEN** `price_forecast.enabled` is `false`
- **THEN** no price advice items SHALL be included in the response
- **AND** existing non-price advice (risk, mode, battery) SHALL continue to work unchanged

#### Scenario: No forecast data available
- **WHEN** `price_forecast.enabled` is `true` but no price forecast records exist
- **THEN** no price advice items SHALL be included in the response

### Requirement: Price advice does not break existing advice
Price advice items SHALL be appended to the existing advice array alongside risk, mode, and battery advice. The addition of price advice SHALL NOT change the format or behavior of existing advice items.

#### Scenario: Mixed advice response
- **WHEN** both price advice and existing advice items are applicable
- **THEN** the response contains all applicable items with their respective categories
- **AND** the `count` field reflects the total number of all advice items

### Requirement: Price advice uses forecast outlook data
The price advisor rules SHALL consume forecast data via the same aggregation logic used by the outlook endpoint (daily averages from `price_forecasts` table). The advisor SHALL NOT perform independent forecast queries — it SHALL reuse the shared aggregation function.

#### Scenario: Shared data source
- **WHEN** the advisor generates price advice
- **THEN** the daily price summaries used for rule evaluation SHALL match those returned by `GET /api/price-forecast/outlook`
