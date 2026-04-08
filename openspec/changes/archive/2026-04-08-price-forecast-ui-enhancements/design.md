## Context

The price forecasting backend (Modules 1 & 2) generates 7-day spot price forecasts (P10/P50/P90 quantiles at 15-min resolution) and exposes them via `/api/price-forecast` (raw slots) and `/api/price-forecast/outlook` (daily aggregates). The frontend currently surfaces this through a compact row of colored pills and text advice in the StrategyDomain card's View B. The Aurora page — which displays PV/Load probabilistic charts and KPI metrics — has no price forecast presence. During cold-start, the price card shows a static "Collecting training data..." message with no progress indication.

**Current state:**
- `ProbabilisticChart` component already renders P10/P50/P90 bands with actual overlays (used for PV/Load)
- `KPIStrip` shows 4 metrics: Cost Drift, Max Price Spread, PV MAE, Load MAE
- Aurora Forecast Horizon has a `chartMode` toggle for `load` | `pv`
- `/api/price-forecast/status` returns `enabled`, `model_available`, `config.min_training_samples` but NOT the current sample count
- Price forecast data already includes `spot_p10`, `spot_p50`, `spot_p90` per 15-min slot — exactly the shape `ProbabilisticChart` expects

## Goals / Non-Goals

**Goals:**
- Show price forecast P10/P50/P90 bands in Aurora's Forecast Horizon chart, with actual spot prices overlaid
- Add a Price MAE KPI to the Aurora KPI strip for D+1 forecast accuracy tracking
- Enhance the Dashboard price card with mini bar heights, numeric prices, and model status
- Replace the static cold-start message with a progress bar showing sample accumulation

**Non-Goals:**
- No changes to the price forecasting model or backend logic
- No new database tables or schema migrations
- No EV-related UI changes
- No historical accuracy tracking beyond the 7-day rolling MAE (that's a future concern)
- No changes to the Decomposition chart mode — price only appears in Probabilistic mode

## Decisions

### Decision 1: Extend `chartMode` to `'load' | 'pv' | 'price'`

The Aurora Forecast Horizon already has a toggle between Load and PV. Adding a third "Price" option is the natural extension. When `chartMode === 'price'`, the chart renders price forecast data through the existing `ProbabilisticChart` component.

**Alternative considered:** A separate Price chart card below the Forecast Horizon. Rejected because it duplicates the chart infrastructure and wastes vertical space.

**Key details:**
- The price toggle button only appears when `price_forecast.enabled` is true (from the dashboard API response or a separate fetch)
- Price mode uses a 7-day horizon (vs 3-day for PV/Load), requiring the x-axis range to extend. The chart's time axis is already dynamic.
- Color: use the `--color-accent` (gold) token for the price forecast line, distinguishing it from PV (green) and Load (orange)
- When price mode is active, the Decomposition/Probabilistic toggle is hidden (price has no decomposition view) — chart always shows probabilistic bands
- `showOpenMeteo` is false for price mode

### Decision 2: New backend endpoint `GET /api/price-forecast/accuracy`

The KPI strip needs a D+1 MAE value. This requires comparing past D+1 forecasts against actual spot prices from `slot_observations`. Rather than computing this in the frontend, add a lightweight backend endpoint.

**Alternative considered:** Extend `/api/price-forecast/status` with accuracy data. Rejected because status is about system health/config, not performance metrics. Accuracy is a separate concern and may grow (e.g., per-horizon MAE, bias).

**Response shape:**
```json
{
  "enabled": true,
  "d1_mae": 0.042,
  "d1_bias": 0.008,
  "sample_days": 7,
  "status": "ok"
}
```

**Computation:** Query `price_forecasts` rows where `days_ahead = 1` and `spot_p50 IS NOT NULL`, join with `slot_observations.export_price_sek_kwh` on matching `slot_start`, compute MAE = mean(|p50 - actual|) and bias = mean(p50 - actual) over the last 7 days. Return `null` values when fewer than 2 days of paired data exist.

### Decision 3: Extend `/api/price-forecast/status` with training sample count

The progress bar needs to know how many training samples have been accumulated. Add `training_samples_count` to the existing status endpoint response.

**Computation:** `SELECT COUNT(*) FROM price_forecasts WHERE spot_p50 IS NULL` gives weather-only accumulation rows, but the actual metric is total paired rows (forecast + observation). Simpler: count rows in `price_forecasts` table (all rows represent training-relevant weather snapshots). The `min_training_samples` config value is already returned.

**Response addition:**
```json
{
  "training_samples_count": 127,
  "min_training_samples": 500
}
```

### Decision 4: Price chart data source — use existing `/api/price-forecast` endpoint

The raw forecast endpoint already returns `slot_start`, `spot_p10`, `spot_p50`, `spot_p90` per 15-minute slot for D+1-D+7. This maps directly to `ProbabilisticChart`'s `SlotData` shape (`time`, `p10`, `p50`, `p90`, `actual`).

For the "actual" overlay, we need historical spot prices. The existing `slot_observations` data is accessible via `/api/energy/range` but doesn't return spot prices directly. Two options:

**Chosen approach:** Add an optional `include_actuals=true` query param to `/api/price-forecast` that joins `slot_observations.export_price_sek_kwh` for slots that have already passed. This keeps it in one fetch.

**Alternative:** Fetch actuals from a separate endpoint. Rejected — unnecessary extra request.

### Decision 5: Enhanced price pills — additive changes only

The current pills show day label + color + opacity. Enhancements:
- Add a small numeric price below each pill (avg p50, formatted as "0.45")
- Add proportional mini-bars below the pill row showing relative price heights
- The bars use the same color scheme as pills (green/amber/red) at full opacity
- Bar height is proportional: tallest bar = most expensive day, shortest = cheapest

The model status indicator shows as a small dot in the card header: green = model active, violet/pulsing = accumulating data.

### Decision 6: Training progress bar replaces static text

When `view === 'price'` and `isPriceForecastEnabled && !hasPriceData`:
- Fetch `/api/price-forecast/status` to get `training_samples_count` and `min_training_samples`
- Render a horizontal progress bar (same style as ModelTrainingCard)
- Label: "127 / 500 samples" with percentage
- Keep the "Price Forecasting Active" heading and icon

### Decision 7: Remove mini bar chart from Dashboard price card

The mini bar chart below the price pills (24px proportional bars) is redundant — the colored pills already convey relative price level. Users who want detail go to the Aurora Forecast Horizon chart. Remove entirely.

### Decision 8: Remove status dot from Dashboard price card

The green/pulsing status dot next to the Battery/Price toggle is redundant — the "Price" toggle button itself only appears when price forecasting is enabled, which already communicates availability. Remove the dot entirely (KISS).

### Decision 9: Fix price pills to show rolling D+1..D+7 from today

The backend `get_daily_outlook()` returns stale data because it doesn't filter by actual date — only by `days_ahead`. Fix: filter outlook results to dates >= today, sort by date (not `days_ahead`), deduplicate per date (keep latest forecast run).

### Decision 10: Fix Aurora price chart to show -7d..+7d rolling window with date-based X-axis

The price chart currently shows only the newest 1000 future slots. For the price mode, the chart should show a 14-day window: 7 days of history (with actuals overlaid) + 7 days of forecast. The X-axis should show dates in ISO/EU format (e.g., "Apr 02"), not timestamps. Today's date should have a "Today" label.

### Decision 11: Fix actuals not showing in price chart

Root cause: `get_price_forecasts_from_db()` returns only the newest 1000 slots (all future), so there are no past slots to join actuals onto. Fix: when `include_actuals=true`, query price forecasts from `-7 days` through the future, so the join with `slot_observations` produces actual values for past slots.

### Decision 12: Allow negative Y-axis in price chart

`ProbabilisticChart` has `min: 0` hardcoded. Spot prices can be negative. Add an optional prop to disable the Y-axis floor, and use it when rendering in price mode.

### Decision 13: Recalculate days_ahead from actual date difference

The `days_ahead` field in `get_daily_outlook()` comes from raw DB rows, but when multiple forecast runs overlap on the same date, the wrong `days_ahead` value gets kept (always 7, causing all pills to show "low" confidence). Fix: compute `days_ahead` as `(date - today).days` after grouping, instead of trusting the DB value.

### Decision 14: Use Chart.js tick callback for date axis labels

The dateAxisMode label approach of returning empty strings for non-first slots causes Chart.js autoSkip to land on empty labels. Fix: use a `tick.callback` that shows one date label per day at the noon slot position, with `autoSkip: false`. This gives predictable, evenly-spaced date labels.

### Decision 15: Add date/time to chart tooltip

The chart tooltip in dateAxisMode shows no useful time information. Add a `callbacks.title` function that formats the hovered slot's full date and time in en-GB locale.

## Risks / Trade-offs

**[Performance] Additional API calls on Aurora page** -> The price forecast endpoint returns up to ~672 slots (7 days x 96 slots). This is comparable to the PV/Load horizon data. Mitigated by only fetching when the price tab is selected (lazy load on tab click, not on page mount).

**[UX] KPI strip grows to 5 items** -> Currently 4 items in a `grid-cols-4` layout. Adding a 5th either requires `grid-cols-5` (narrower cards) or wrapping. Mitigated by keeping `grid-cols-4` on large screens and replacing "Max Price Spread" with "Price MAE" when price forecasting is enabled (both are price-related, MAE is more useful). When price forecasting is disabled, keep current 4 KPIs unchanged.

**[Data availability] Accuracy KPI needs historical forecast-vs-actual pairs** -> During cold-start or first week, there won't be enough D+1 data to compute MAE. Mitigated by showing "N/A" (same pattern as PV/Load MAE when no data exists).

**[Chart readability] 7-day price horizon is wider than 3-day PV/Load** -> The x-axis labels need to remain readable at 7 days. Mitigated by using daily tick marks instead of hourly, since price patterns are more meaningful at daily granularity. The chart already handles variable time ranges.
