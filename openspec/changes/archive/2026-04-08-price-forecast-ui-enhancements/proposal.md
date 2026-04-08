## Why

The price forecasting backend (Modules 1 & 2) is fully operational — generating 7-day spot price forecasts with P10/P50/P90 quantiles, daily outlook aggregation, and rule-based price advice. However the frontend only surfaces this through a compact row of colored pills and a few text lines in the StrategyDomain card. There is no way to visualize the forecast over time, verify model accuracy, see actual numeric prices at a glance, or track training progress during cold-start. These enhancements close the gap between what the backend knows and what the user can see.

## What Changes

- **Price tab in Aurora Forecast Horizon**: Add a "Price" toggle alongside Load/PV in the existing Forecast Horizon chart. Renders P10/P50/P90 bands using the existing `ProbabilisticChart` component with actual Nordpool spot prices overlaid as they become available. 7-day horizon (vs 3-day for PV/Load).
- **Price forecast accuracy KPI**: Add a Price MAE metric to the Aurora KPI strip, showing mean absolute error of D+1 price forecasts vs actual spot prices (matching the existing PV/Load MAE pattern).
- **Enhanced Dashboard price card**: Improve the StrategyDomain View B (price view) with mini bar chart showing relative daily price heights, numeric average prices visible per pill, and a model status indicator.
- **Training progress indicator**: Replace the static "Collecting training data..." text shown during cold-start with a progress bar displaying accumulated vs required training samples (e.g., "127 / 500 samples").

## Capabilities

### New Capabilities
- `price-forecast-horizon-chart`: Price P10/P50/P90 probabilistic chart in Aurora Forecast Horizon section with actual price overlay and 7-day range
- `price-forecast-accuracy-kpi`: Price forecast MAE metric displayed in the Aurora KPI strip
- `price-card-enhancements`: Enhanced Dashboard price view with mini bars, numeric prices, model status, and training progress bar

### Modified Capabilities
- `weekly-outlook-widget`: View B adds mini bar heights, numeric prices per pill, model status indicator, and training progress bar during cold-start

## Impact

- **Frontend components**: `Aurora.tsx`, `ProbabilisticChart.tsx` (or wrapper), `CommandDomains.tsx`, `KPIStrip.tsx`
- **API**: May need a new endpoint or extension to `/api/price-forecast/status` to return training sample count and D+1 accuracy metrics
- **Backend**: `price_forecast.py` router — expose training sample count; new accuracy calculation comparing D+1 forecasts to actual prices
- **No database schema changes** — all data already exists in `price_forecasts` + `slot_observations`
