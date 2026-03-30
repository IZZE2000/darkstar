## 1. Inference — Weather Accumulation Without Model

- [x] 1.1 In `ml/price_forecast.py`, modify `generate_price_forecasts()`: replace the early `return []` when model files are missing (lines 102-111) with a flag (e.g., `has_model = False`). The function should continue to fetch weather, compute wind index, and build feature rows regardless.
- [x] 1.2 In `generate_price_forecasts()`, gate the inference block (predict with models) behind `if has_model:`. When `has_model` is False, set `spot_p10 = spot_p50 = spot_p90 = None` for each forecast record instead of running model inference.
- [x] 1.3 Ensure `_persist_forecasts()` already handles `None` values for spot columns (the `PriceForecast` model columns are nullable — verify no coercion to float occurs before persisting).

## 2. Orchestrator — Decouple Forecast Call from Training Success

- [x] 2.1 In `ml/training_orchestrator.py`, move the `generate_price_forecasts()` call (currently inside the `if price_success:` block at line 244) to run unconditionally after the training attempt, regardless of whether `price_success` is True or False. Keep the model path conditional: pass `model_path` only if `price_success` is True and the model file exists, otherwise pass `None`.

## 3. Fallback Safety — Null Guard

- [x] 3.1 In `ml/price_forecast.py`, modify `get_d1_price_forecast_fallback()` to filter out rows where `spot_p50` is `None` after fetching from the DB. If no non-null rows remain after filtering, return `None`.

## 4. Daily Scheduler Tick

- [x] 4.1 Add a daily scheduled call to `generate_price_forecasts()` in the training orchestrator or scheduler, firing once per day at approximately 06:00 (independent of the training schedule). This should call with `model_path=None` allowed — the function itself handles the no-model case.

## 5. Tests

- [x] 5.1 Add a unit test for `generate_price_forecasts()` with no model files present: verify it returns a list of records (not empty), all with `spot_p10 = spot_p50 = spot_p90 = None`, and that weather feature columns are populated.
- [x] 5.2 Add a unit test for `get_d1_price_forecast_fallback()`: given a DB containing only null-prediction rows for D+1, verify the function returns `None` rather than rows with null spot values.
- [x] 5.3 Verify the existing test for the training orchestrator confirms `generate_price_forecasts()` is called even when `train_price_model()` returns False (insufficient data path).
