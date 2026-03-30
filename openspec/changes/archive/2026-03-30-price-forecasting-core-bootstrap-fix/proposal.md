## Why

A chicken-and-egg bug in the just-implemented price forecasting core prevents it from ever bootstrapping on a fresh install: `generate_price_forecasts()` returns early when no model exists, so no weather rows accumulate, so training data never reaches threshold, so no model ever trains. Additionally, the D+1 fallback can silently serve null-prediction weather rows as real price forecasts, which would give the planner wrong prices.

## What Changes

- Modify `generate_price_forecasts()` to always fetch weather and persist rows even when no model exists, storing `null` for the spot prediction columns — the weather features are what training needs
- Move the `generate_price_forecasts()` call in `training_orchestrator.py` outside the `if price_success:` gate so it runs on every training cycle regardless of outcome
- Add a `WHERE spot_p50 IS NOT NULL` guard to `get_d1_price_forecast_fallback()` so weather-only (null-prediction) rows are never served as price forecasts to the planner
- Add a daily scheduler tick (independent of training and planner) that calls `generate_price_forecasts()` once per day to accumulate weather snapshots ~5× faster than weekly training alone

## Capabilities

### New Capabilities

- none

### Modified Capabilities

- `price-forecasting`: Two requirements need updating. "No forecast without trained model" currently says the system SHALL produce no forecasts — this must change to allow weather-only row accumulation. "Price forecast persistence" needs a scenario for null-prediction rows. The D+1 fallback scenario needs a safety guard requirement.

## Impact

- **`ml/price_forecast.py`**: Logic change in `generate_price_forecasts()` and `get_d1_price_forecast_fallback()`
- **`ml/training_orchestrator.py`**: Move forecast call outside training success gate
- **Scheduler** (`ml/training_orchestrator.py` or equivalent daily tick): Add daily weather snapshot call
- No schema changes — spot columns are already nullable
- No new dependencies
