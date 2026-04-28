## Why

The planner crashes at night (before 13:00) because the D+1 price forecast fallback returns slots for *today* — the forecast was generated yesterday when today was "tomorrow". Those stale slots collide with real Nordpool prices for today, creating duplicate timestamps that crash the solver pipeline.

## What Changes

- `get_d1_price_forecast_fallback` filters out any forecast slots whose date is not strictly in the future (today or earlier are excluded)
- `_process_nordpool_data` deduplicates `all_entries` by `start_time` before returning, keeping the first occurrence (real Nordpool data always loads first, so it wins)

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `price-forecasting`: Requirement that the D+1 fallback only contributes slots for dates strictly after today; and that assembled price data is always free of duplicate timestamps before reaching the planner.

## Impact

- `ml/price_forecast.py` — `get_d1_price_forecast_fallback`
- `backend/core/prices.py` — `_process_nordpool_data`
- No API changes, no config changes, no schema changes
