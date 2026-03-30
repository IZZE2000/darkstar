## 1. Price Outlook API Endpoint

- [x] 1.1 Create a shared helper function `get_daily_outlook(db, config)` (e.g., in `backend/core/price_outlook.py`) that queries the `price_forecasts` DB table, aggregates per-slot p10/p50/p90 into daily summaries for D+1 through D+7 (avg, min, max of p50 per day), and returns a list of daily summary dicts. This function is reused by both the API endpoint and the advisor rules — do not duplicate the query.
- [x] 1.2 Add a `get_trailing_avg(db)` helper in the same file that queries `slot_observations.export_price_sek_kwh` for the most recent 14 days and returns the mean. Return `None` if fewer than 2 days of data exist. Use whatever history is available if between 2 and 13 days.
- [x] 1.3 Add level classification: for each daily summary, compute `level` by comparing `avg_spot_p50` to `reference_avg` — `"cheap"` (< 85%), `"normal"` (85-115%), `"expensive"` (> 115%), `"unknown"` if reference is `None`.
- [x] 1.4 Add confidence classification: map `days_ahead` to `confidence` — 1-2 → `"high"`, 3-4 → `"medium"`, 5-7 → `"low"`.
- [x] 1.5 Add `GET /api/price-forecast/outlook` endpoint to the price forecast router (`backend/api/routers/price_forecast.py`, created by Module 1). It calls `get_daily_outlook()` and `get_trailing_avg()`, applies classification, and returns the full JSON: `{enabled, days, reference_avg, status}`.
- [x] 1.6 Handle disabled/empty cases: return `{"enabled": false, "days": [], "status": "disabled"}` when `price_forecast.enabled` is false. Return `{"enabled": true, "days": [], "status": "no_data"}` when enabled but no forecast records exist.

## 2. Price Advisor Rules (Backend)

- [x] 2.1 In `backend/api/routers/analyst.py`, add a helper function `_get_price_advice(daily_outlook, today_avg_spot)` that returns a list of advice dicts (`category: "price"`, `message: str`, `priority: "info"`).
- [x] 2.2 Implement the "cheapest day ahead" rule in `_get_price_advice()`: if any day in D+1..D+7 has `avg_spot_p50` that is 30%+ below `today_avg_spot`, emit an advice item with the day name and percentage drop (e.g., "Prices drop ~40% on Thursday. Consider deferring heavy loads.").
- [x] 2.3 Implement the "prices rising" rule: if every day from D+1 through D+3 has `avg_spot_p50` higher than `today_avg_spot`, emit an advice item indicating today is cheapest in the next 3 days.
- [x] 2.4 Implement the "cheap overnight" rule: if tonight's 22:00-06:00 hourly average p50 (query `price_forecasts` for tonight's slots) is 25%+ below the full-day average, emit an advice item about the overnight window.
- [x] 2.5 Integrate `_get_price_advice()` into the existing strategy advice function/endpoint: when `price_forecast.enabled` is true and `daily_outlook` is non-empty, call `_get_price_advice()` with `get_daily_outlook()` data and append results to the advice list. Existing non-price advice items (risk, mode, battery) remain unchanged regardless.

## 3. Frontend API Client

- [x] 3.1 Add TypeScript types `PriceOutlookDay` and `PriceOutlookResponse` to `frontend/src/lib/api.ts` or the appropriate types file. Fields: per the design's response shape — `date`, `day_label`, `days_ahead`, `avg_spot_p50`, `avg_spot_p10`, `avg_spot_p90`, `min_hour_p50`, `max_hour_p50`, `level: "cheap" | "normal" | "expensive" | "unknown"`, `confidence: "high" | "medium" | "low"`. Response wrapper: `enabled: boolean`, `days: PriceOutlookDay[]`, `reference_avg: number | null`, `status: string`.
- [x] 3.2 Add `Api.priceForecast.outlook()` method in `frontend/src/lib/api.ts` calling `GET /api/price-forecast/outlook` and returning `PriceOutlookResponse`.

## 4. StrategyDomain Toggle and View B

- [x] 4.1 Add `outlookData?: PriceOutlookResponse` and `priceAdvice?: AdviceItem[]` as optional props to the `StrategyDomain` component in `frontend/src/components/CommandDomains.tsx`.
- [x] 4.2 Add a local `view` state (`"battery" | "price"`, default `"battery"`) to `StrategyDomain`. Add a toggle control (small tab or icon button) in the card header — visible only when `outlookData?.enabled` is true and `outlookData.days.length > 0`.
- [x] 4.3 When `view === "battery"`: render the existing card content unchanged (SoC, S-Index, Safety Floor, Cycles). No changes to this view.
- [x] 4.4 When `view === "price"`: render View B — the 7-day pill row and price advice items. Pills are colored by `level` (green/amber/red/gray) with CSS opacity by `confidence` (1.0/0.75/0.5). Each pill shows the `day_label`.
- [x] 4.5 Add a tooltip to each pill on hover/tap showing `day_label`, `avg_spot_p50`, `min_hour_p50`, `max_hour_p50`, and confidence label. Follow the same tooltip pattern used elsewhere in the dashboard.
- [x] 4.6 Below the pills in View B, render price advice items from `priceAdvice` (items where `category === "price"`). If none, show a neutral fallback line (e.g., "No price alerts this week").

## 5. Dashboard Integration

- [x] 5.1 In `Dashboard.tsx`, add a `fetchPriceOutlook()` call inside `fetchDeferredData()` (alongside the existing deferred fetches) that calls `Api.priceForecast.outlook()` and stores the result in state.
- [x] 5.2 In `Dashboard.tsx`, extract price advice items from the existing analyst advice fetch (filter by `category === "price"`) and store separately in state, or pass the full advice list to StrategyDomain and filter there.
- [x] 5.3 Pass `outlookData` and `priceAdvice` props to the `<StrategyDomain>` usage in `Dashboard.tsx`. Verify the layout is pixel-identical to current when `price_forecast.enabled` is false (no toggle, no view B, card unchanged).

## 6. Tests

- [x] 6.1 Write backend unit tests for `get_daily_outlook()`: verify daily aggregation (avg/min/max), verify empty result when no forecast records exist, verify D+1 through D+7 range.
- [x] 6.2 Write backend unit tests for `get_trailing_avg()`: verify 14-day mean, partial history fallback (3 days), and `None` return for fewer than 2 days.
- [x] 6.3 Write backend unit tests for level classification: verify each threshold boundary (< 85%, 85-115%, > 115%, and `None` reference → "unknown").
- [x] 6.4 Write backend unit tests for `_get_price_advice()`: verify each rule fires under correct conditions. Verify no advice emitted when thresholds not met. Verify empty output when `price_forecast.enabled` is false.
- [x] 6.5 Write backend unit tests for `GET /api/price-forecast/outlook`: verify response shape for enabled+data, disabled, and no-data cases.
- [x] 6.6 Write a backend unit test verifying that price advice items are appended to the existing advice response without altering existing items (risk, mode, battery categories intact).
