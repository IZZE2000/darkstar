## Why

The Forecast Horizon card implemented in commit b9d297e is completely non-functional. Three critical bugs prevent any useful data from being displayed: actual/historical data is missing, Open-Meteo forecast data is missing, and per-array breakdowns don't render. These bugs render the feature useless and must be fixed immediately.

## What Changes

- **Fix**: Move `history_series` inside `horizon` object in `/aurora/dashboard` API response to match TypeScript contract
- **Fix**: Change timestamp serialization from `str(ts_idx)` to `ts_idx.isoformat()` in Open-Meteo data lookup to fix key matching
- **Fix**: Update frontend TypeScript types if needed to align with corrected API structure
- **Enhancement**: Expand forecast horizon from 48h to 72h (yesterday+today+tomorrow)
- **Enhancement**: Always use Open-Meteo forecast API with `past_days=1` and `forecast_days=2`

## Capabilities

### New Capabilities
- *(none - this is a bugfix)*

### Modified Capabilities
- `aurora-forecast-display`: Update the dashboard API response structure and forecast data enrichment to correctly display actual, forecast, and per-array data

## Impact

- **Backend**: `/backend/api/routers/forecast.py` (API response structure)
- **Backend**: `/ml/api.py` (timestamp format fix)
- **Frontend**: `frontend/src/lib/types.ts` (type alignment if needed)
- **Risk**: Zero - fixes completely broken code paths that currently return no data
