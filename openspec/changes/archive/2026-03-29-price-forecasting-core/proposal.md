## Why

Darkstar currently has no visibility beyond the next 24-48 hours of Nordpool prices. This prevents multi-day strategic planning (e.g., deferring EV charging to a cheaper day) and leaves the S-Index and advisor blind to price trends. This change builds the foundational forecasting engine that downstream modules (Advisor/Outlook, S-Index enhancement, EV deferral controller) will consume.

## What Changes

- Extend `ml/weather.py` to fetch 16-day Open-Meteo forecasts (currently 2 days) with new parameters including `wind_speed_10m` — the primary marginal price driver in the Nordics.
- Create a `data/regions.json` file mapping Nordpool price areas (SE1-SE4 initially) to regional weather coordinate sets for computing a regional wind index.
- Build a LightGBM price forecast model (p10/p50/p90 quantile regression) predicting raw Nordpool spot prices for D+1 through D+7.
- Add DB schema for persisting price forecast records (including weather inputs at issue time for honest training).
- Add a `price_forecast.enabled` config toggle (disabled by default) as a global gate for downstream consumers.
- D+1 forecast serves as fallback before the ~13:00 CET Nordpool day-ahead auction; replaced by real prices once available.
- Follow existing learning-tier pattern: model only activates after sufficient paired (price + weather) data accumulates.

## Capabilities

### New Capabilities

- `price-forecasting`: The LightGBM price model, training pipeline, inference, and forecast persistence. Covers the regional wind index computation, feature engineering (calendar, weather, price lags), and learning-tier cold-start gating.
- `regional-weather-coordinates`: The `regions.json` data file and the loader that maps a user's configured `price_area` to weather coordinate sets. Handles multi-point weather fetching and averaging into a single regional wind index feature.
- `weather-extension`: Extension of the existing Open-Meteo weather fetch to support 16-day forecasts, wind speed parameters, and multi-coordinate fetching.

### Modified Capabilities

- `open-meteo-pv-forecast`: The weather fetch function gains new parameters (wind speed) and a longer forecast horizon (16 days). Existing PV forecast behavior must be preserved.

## Impact

- **ML pipeline** (`ml/`): New price model alongside existing load/PV models. New training and inference code.
- **Weather** (`ml/weather.py`): Extended fetch with more parameters, longer horizon, multi-coordinate support.
- **Database** (`alembic/`): New migration for price forecast table(s).
- **Config** (`config.yaml`): New `price_forecast` section with `enabled` toggle.
- **Data files** (`data/regions.json`): New static data file.
- **Dependencies**: No new external dependencies (LightGBM and Open-Meteo already in use).
