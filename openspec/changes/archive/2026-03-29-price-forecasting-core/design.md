## Context

Darkstar's Aurora ML pipeline currently forecasts PV production and household load using LightGBM. Weather data is fetched from Open-Meteo for 3 parameters (temperature, cloud cover, shortwave radiation) over a 3-day window (1 past + 2 future) at a single coordinate (the user's home location).

Nordpool spot prices are fetched on-demand, cached in memory (1h TTL), and only persisted in `slot_observations` after execution. There is no price forecasting capability.

The system already has a learning-tier pattern for cold-start (load/PV models activate after minimum sample thresholds), a config-driven architecture, and Alembic for DB migrations.

This change adds the first price forecasting engine to Aurora, extending the weather pipeline and creating a new LightGBM model that predicts raw spot prices for D+1 through D+7.

## Goals / Non-Goals

**Goals:**
- Produce 7-day rolling spot price forecasts (p10/p50/p90) usable by downstream modules (Advisor, S-Index, EV deferral)
- Extend Open-Meteo weather fetch to support wind speed and multi-coordinate regional weather
- Store price forecasts with their weather inputs for honest training (no future data leakage)
- Follow existing Aurora patterns: LightGBM, learning tiers, config-driven, async-safe
- Gate all downstream consumption behind `price_forecast.enabled` (disabled by default)

**Non-Goals:**
- Building the Advisor UI, S-Index enhancement, or EV deferral controller (separate changes)
- ENTSO-E or other external data sources
- Backfilling historical prices (future enhancement)
- Changing the Kepler solver's price inputs (it stays on real Nordpool prices)

## Decisions

### 1. Single LightGBM model with `days_ahead` feature (not per-horizon models)

**Choice:** One model predicts all horizons (D+1 through D+7), with `days_ahead` as an input feature.

**Why over per-day models:** Simpler to train, maintain, and reason about. A single model sees more training data per feature combination. LightGBM handles the horizon-dependent accuracy degradation naturally through the `days_ahead` feature. Seven separate models would require 7x the minimum training data threshold.

### 2. Predict raw spot price, derive import/export at inference

**Choice:** The model's target is `slot_observations.export_price_sek_kwh` (raw Nordpool spot price). Import prices are computed at inference time using the existing fee/tax logic in `backend/core/prices.py`.

**Why:** Immune to tax/fee policy changes. The same model works regardless of VAT rate, grid transfer fee, or energy tax updates.

### 3. Regional wind index as a single averaged feature

**Choice:** For each price area, fetch wind speed from multiple coordinates (defined in `data/regions.json`), average them into a single "regional wind index" feature.

**Why over raw multi-point features:** Reduces feature dimensionality. A model with 3 separate wind values per region has 3x the features with high collinearity. A single averaged index captures the same signal with less noise and fewer parameters to learn.

### 4. Weather inputs stored alongside forecast records

**Choice:** Each price forecast record stores the weather feature values used at prediction time. Training uses these stored features paired with actual prices — not historical actual weather.

**Why:** Prevents future data leakage. In production, the model sees forecasted weather (with errors). Training on actual historical weather would create an unrealistically optimistic model. Storing inputs with forecasts avoids needing a separate weather snapshot system.

### 5. Extend existing `get_weather_series()` rather than creating a parallel function

**Choice:** Add parameters to the existing weather fetch function for extended horizon and wind speed, with a separate function for multi-coordinate regional weather.

**Why:** The existing function handles caching, error recovery, and interpolation. A separate regional weather function is needed because it fetches from different coordinates, but the core Open-Meteo interaction pattern should be shared.

### 6. New `price_forecasts` DB table (not extending `slot_forecasts`)

**Choice:** Create a dedicated table for price forecast records rather than adding columns to `slot_forecasts`.

**Why:** `slot_forecasts` is tightly coupled to the planner pipeline's per-slot PV/load forecast flow. Price forecasts have different lifecycle (issued daily, cover 7 days, store weather inputs). A separate table avoids schema confusion and allows independent querying for training.

### 7. Learning-tier cold-start gating

**Choice:** The price model uses the same learning-tier pattern as load/PV. Below a configurable minimum sample threshold, no price forecasts are produced and `price_forecast.enabled` has no effect.

**Why:** Consistent with existing system behavior. Prevents unreliable forecasts from influencing decisions on new installations.

## Risks / Trade-offs

- **[Sparse training data early on]** → The model needs weeks/months of paired price+weather data before it's useful. Mitigation: learning-tier gating prevents activation until threshold is met. Accuracy improves over time as data accumulates.
- **[Open-Meteo rate limits with multi-coordinate fetches]** → Fetching 3 coordinates per price area triples the API calls. Mitigation: cache aggressively (existing 5-min TTL pattern), batch requests where the API supports it. Open-Meteo free tier is generous for hourly data.
- **[Regional wind index may be noisy for some areas]** → The averaged wind speed from 3 points is a proxy for actual wind generation. Mitigation: the model also has local weather, calendar, and price lag features. Wind index improves accuracy but isn't the sole signal. Can iterate on coordinate selection.
- **[16-day weather forecast accuracy drops sharply after day 5-6]** → Mitigation: `days_ahead` feature lets the model learn to widen its p10/p90 bands for distant horizons. UI confidence encoding (Module 2) will also reflect this.
