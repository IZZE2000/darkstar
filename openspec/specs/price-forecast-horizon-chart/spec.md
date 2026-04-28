## Purpose

Add a price forecast chart mode to the Aurora Forecast Horizon card, rendering P10/P50/P90 probabilistic bands for spot prices over a 7-day horizon, with lazy data fetching and actual price overlay support.

## Requirements

### Requirement: Price toggle in Aurora Forecast Horizon
The Aurora Forecast Horizon card SHALL support a third chart mode `'price'` alongside existing `'load'` and `'pv'` modes. The price toggle button SHALL only be visible when price forecasting is enabled.

#### Scenario: Price toggle visible when price forecast enabled
- **WHEN** the Aurora page loads and `price_forecast.enabled` is `true`
- **THEN** a third toggle button (price icon) appears in the Forecast Horizon toggle group alongside the Load and PV buttons

#### Scenario: Price toggle hidden when price forecast disabled
- **WHEN** the Aurora page loads and `price_forecast.enabled` is `false`
- **THEN** only the Load and PV toggle buttons appear (no price button)

#### Scenario: Selecting price mode
- **WHEN** the user clicks the price toggle button
- **THEN** `chartMode` is set to `'price'` and the Forecast Horizon renders the price probabilistic chart

### Requirement: Price chart renders P10/P50/P90 bands via ProbabilisticChart
When `chartMode` is `'price'`, the Forecast Horizon SHALL render the existing `ProbabilisticChart` component using price forecast slot data mapped to the `SlotData` shape.

#### Scenario: Price chart renders forecast bands
- **WHEN** `chartMode` is `'price'` and price forecast data is available
- **THEN** the chart renders P10, P50, and P90 lines/bands using `spot_p10`, `spot_p50`, `spot_p90` from the price forecast endpoint
- **AND** the chart line color SHALL be gold (`--color-accent`)

#### Scenario: Actual spot prices overlaid
- **WHEN** `chartMode` is `'price'` and actual spot prices exist for past slots
- **THEN** actual prices SHALL be overlaid on the chart as data points (using the `actual` field in `SlotData`)

#### Scenario: No price data available
- **WHEN** `chartMode` is `'price'` and no price forecast data is available
- **THEN** the chart area SHALL display an empty state message (e.g., "No price forecast data available")

### Requirement: Price chart shows 7-day horizon
The price chart SHALL display a 7-day forecast horizon (D+1 through D+7), unlike PV/Load which show 3 days.

#### Scenario: 7-day x-axis range
- **WHEN** `chartMode` is `'price'`
- **THEN** the chart x-axis SHALL span from now to D+7, showing daily tick marks

#### Scenario: Horizon label reflects 7 days
- **WHEN** `chartMode` is `'price'`
- **THEN** the card header SHALL display "Forecast Horizon (7 Days)" instead of "(3 Days)"

### Requirement: Decomposition view hidden in price mode
The Decomposition/Probabilistic toggle SHALL NOT apply to price mode. Price always shows the probabilistic chart.

#### Scenario: Toggle hidden in price mode
- **WHEN** `chartMode` is `'price'`
- **THEN** the Decomposition/Probabilistic toggle is hidden or disabled
- **AND** the subtitle shows "Price Forecast" (not "Decomposition View" or "Probabilistic View")

### Requirement: Price chart data fetched lazily
Price forecast data SHALL be fetched only when the user selects price mode, not on Aurora page mount.

#### Scenario: Data fetched on price tab selection
- **WHEN** the user clicks the price toggle for the first time
- **THEN** the frontend SHALL fetch `GET /api/price-forecast?include_actuals=true`
- **AND** a loading state SHALL be shown while fetching

#### Scenario: Subsequent tab switches use cached data
- **WHEN** the user switches away from price mode and back
- **THEN** the previously fetched data SHALL be reused without a new API call (until page refresh or schedule update)

### Requirement: Price forecast API supports actual price overlay
The `GET /api/price-forecast` endpoint SHALL accept an optional `include_actuals` query parameter that enriches the response with actual spot prices for past slots.

#### Scenario: include_actuals returns actual prices
- **WHEN** the endpoint is called with `?include_actuals=true`
- **THEN** each forecast record for a slot that has passed SHALL include an `actual_spot` field containing the `export_price_sek_kwh` value from `slot_observations` for that slot
- **AND** future slots SHALL have `actual_spot` set to `null`

#### Scenario: Default behavior without include_actuals
- **WHEN** the endpoint is called without `include_actuals` or with `include_actuals=false`
- **THEN** the response SHALL NOT include `actual_spot` fields (backward compatible)
