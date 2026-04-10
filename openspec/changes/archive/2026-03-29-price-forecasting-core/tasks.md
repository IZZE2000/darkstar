## 1. Config & Data Files

- [x] 1.1 Add `price_forecast` section to `config.yaml` and `config.default.yaml` with `enabled: false` (default), `min_training_samples: 500`, and `model_name: "price_model.lgb"`. Place it near the existing `forecasting` section.
- [x] 1.2 Create `data/regions.json` with coordinate entries for SE1, SE2, SE3, and SE4. Each area has a `local` coordinate plus relevant cross-border influence coordinates (e.g., SE4: Malmö, Copenhagen area, Rostock area). Follow the structure in the blueprint (`docs/designs/multi_day_forecasting.md`). Research appropriate lat/lon for each area.
- [x] 1.3 Add `data/regions.json` to the COPY directives in all Dockerfiles (`Dockerfile`, `darkstar/Dockerfile`, `darkstar-dev/Dockerfile`) so it is included in container builds.

## 2. Weather Extension

- [x] 2.1 Add `forecast_days` parameter (default=2) to `get_weather_series()` in `ml/weather.py` so callers can request up to 16 days. Existing callers pass no argument and get current behavior (2 days). Update the Open-Meteo API URL construction to use this parameter.
- [x] 2.2 Add `extra_params` parameter (default=None) to `get_weather_series()` in `ml/weather.py`. When provided (e.g., `["wind_speed_10m"]`), these are appended to the Open-Meteo `hourly` parameter list. The extra params are interpolated to 15-minute resolution alongside existing params. Default callers are unaffected.
- [x] 2.3 Update the weather cache key in `get_weather_series()` to include `forecast_days`, `extra_params`, and coordinates — so different callers (PV vs price) get independent cache entries.
- [x] 2.4 Write a `get_regional_weather()` function (in `ml/weather.py` or a new `ml/regional_weather.py`) that: loads `data/regions.json`, looks up the user's `price_area`, fetches weather (with `wind_speed_10m` and `forecast_days=16`) for each coordinate, and returns the per-coordinate DataFrames. Handle missing `regions.json` or unknown price area by falling back to home coordinates with a logged warning.
- [x] 2.5 Write a `compute_regional_wind_index()` function that takes the per-coordinate DataFrames from 2.4 and returns a single Series: the arithmetic mean of `wind_speed_10m` across all coordinates. Handle partial failures (some coordinates missing) by averaging available data.

## 3. Database Schema

- [x] 3.1 Create an Alembic migration adding a `price_forecasts` table with columns: `id` (autoincrement PK), `slot_start` (ISO string, indexed), `issue_timestamp` (ISO string — when forecast was generated), `days_ahead` (integer), `spot_p10` (float), `spot_p50` (float), `spot_p90` (float), `wind_index` (float), `temperature_c` (float), `cloud_cover` (float), `radiation_wm2` (float). Add a composite index on `(slot_start, issue_timestamp)`.
- [x] 3.2 Add the `price_forecasts` table as a SQLAlchemy model in `backend/learning/models.py` matching the migration schema.

## 4. Price Feature Engineering

- [x] 4.1 Create `ml/price_features.py` with a function `build_price_features()` that takes a target slot timestamp and returns a dict of features: `hour`, `day_of_week`, `month`, `is_weekend` (bool→int), `is_holiday` (bool→int, use Swedish holidays), `days_ahead` (int). Use the same time feature extraction patterns as existing `context_features.py`.
- [x] 4.2 Add price lag feature computation to `build_price_features()`: query `slot_observations.export_price_sek_kwh` for `price_lag_1d` (same hour yesterday), `price_lag_7d` (same hour last week), and `price_lag_24h_avg` (trailing 24h average). Return NaN for missing lags (LightGBM handles natively).
- [x] 4.3 Add weather feature slots to `build_price_features()`: accept `wind_index`, `temperature_c`, `cloud_cover`, `radiation_wm2` as parameters and include them in the returned feature dict.

## 5. Price Model Training

- [x] 5.1 Create `ml/price_train.py` with a `train_price_model()` function. It queries `price_forecasts` joined with `slot_observations` (on `slot_start`) to build training pairs: features = stored weather inputs + calendar + price lags, target = `export_price_sek_kwh`. Apply the same exponential decay sample weighting pattern used in `ml/train.py`.
- [x] 5.2 Implement learning-tier gating in `train_price_model()`: if the number of valid training pairs is below `config.price_forecast.min_training_samples`, skip training, log the reason, and return without writing a model file.
- [x] 5.3 Train a LightGBM model with 3 quantile objectives (alpha=0.1, 0.5, 0.9) producing p10/p50/p90. Save the model to `data/ml/models/price_model.lgb` (or the configured model name). Follow the same model saving pattern as existing `train.py`.
- [x] 5.4 Integrate `train_price_model()` into the existing Aurora training schedule in `ml/train.py` (or `ml/pipeline.py`) so it runs alongside load/PV training on the configured `run_days`/`run_time`.

## 6. Price Forecast Inference

- [x] 6.1 Create `ml/price_forecast.py` with a `generate_price_forecasts()` async function. It: loads the trained price model (if exists), fetches regional weather via `get_regional_weather()`, computes wind index via `compute_regional_wind_index()`, builds features for each 15-min slot from D+1 to D+7, runs inference (p10/p50/p90), and returns a list of forecast records.
- [x] 6.2 Persist each forecast record to the `price_forecasts` DB table, storing the weather feature values used at prediction time alongside the predictions. Set `issue_timestamp` to the current time.
- [x] 6.3 Add import/export price derivation: a function `derive_consumer_prices(spot_p10, spot_p50, spot_p90, config)` that applies the fee/VAT/tax logic from `backend/core/prices.py` to convert raw spot forecasts into import/export prices. Do NOT duplicate the calculation — call or reuse the existing price calculation logic.
- [x] 6.4 Add D+1 fallback logic: when downstream code requests D+1 prices and real Nordpool prices are not yet available (before ~13:00 CET), return the price forecast for D+1. When real prices arrive, they take precedence. Integrate this into the existing price fetching flow in `backend/core/prices.py` or a thin wrapper.

## 7. API Endpoint

- [x] 7.1 Create a new API router (e.g., `backend/api/routers/price_forecast.py`) with a `GET /api/price-forecast` endpoint. When `price_forecast.enabled` is true and forecasts exist, return the forecast array (slot_start, spot_p10/p50/p90, import_p50, export_p50, days_ahead). When disabled or no model, return an empty array with a `status` field explaining why.
- [x] 7.2 Register the new router in `backend/main.py`.

## 8. Forecast Scheduling

- [x] 8.1 Integrate `generate_price_forecasts()` into the planner pipeline or scheduler so it runs daily (e.g., after training, or on each planner cycle). Ensure it runs regardless of `price_forecast.enabled` (to accumulate data), but the API endpoint gates external access.

## 9. Tests

- [x] 9.1 Write unit tests for `build_price_features()`: verify calendar features, price lag computation with missing data, and weather feature passthrough.
- [x] 9.2 Write unit tests for `compute_regional_wind_index()`: verify averaging with 1, 2, and 3 coordinate DataFrames, and partial failure handling.
- [x] 9.3 Write unit tests for `train_price_model()`: verify cold-start gating (skip when below threshold), verify model file is written when sufficient data exists (use synthetic data).
- [x] 9.4 Write unit tests for `derive_consumer_prices()`: verify import price derivation matches the existing `prices.py` logic, verify export price equals raw spot.
- [x] 9.5 Write unit tests for the `/api/price-forecast` endpoint: verify response when enabled with data, when disabled, and when no model exists.
- [x] 9.6 Write an integration test for the regions.json loader: verify SE1-SE4 all load correctly, verify graceful fallback for unknown price area.
