## 1. Add Recency Weighting to Base Model Training

- [x] 1.1 Add `_compute_sample_weights(df, half_life_days, config)` function to `ml/train.py` that computes exponential decay weights based on each sample's age (days from now), with configurable half-life defaulting to 30 days
- [x] 1.2 Remove `days_back` parameter and 90-day cap from `TrainingConfig` and `_load_slot_observations()` — load all available data from DB
- [x] 1.3 Pass sample weights to `LGBMRegressor.fit()` via the `sample_weight` parameter in `_train_regressor()`
- [x] 1.4 Update `_parse_args()` to remove `--days-back` CLI flag (no longer needed)

## 2. Remove Corrector from Pipeline

- [x] 2.1 Simplify `ml/pipeline.py:run_inference()` to only call `generate_forward_slots()` — remove `predict_corrections()` and `_apply_corrections_to_db()` calls
- [x] 2.2 Simplify `ml/api.py:get_forecast_slots()` — set `final.load_kwh = base_load` directly (remove `+ load_corr`), same for PV. Remove correction fields from response.
- [x] 2.3 Remove corrector import and training step from `ml/training_orchestrator.py`
- [x] 2.4 Remove corrector-related imports from `ml/forward.py` (the `_determine_graduation_level` import)
- [x] 2.5 Clean up `backend/learning/store.py:store_forecasts()` — remove the "preserve corrections on conflict" logic from the UPSERT (stop writing correction columns, but leave DB columns in schema)

## 3. Remove Auto-Tuner/Analyst Forecast Bias

- [x] 3.1 Delete `backend/learning/analyst.py`
- [x] 3.2 Remove per-hour learning adjustment application from `planner/inputs/data_prep.py` (the `pv_adjustment_by_hour_kwh`/`load_adjustment_by_hour_kwh` block)
- [x] 3.3 Remove hourly adjustment overlay loading from `planner/inputs/learning.py`
- [x] 3.4 Remove Analyst invocation from `backend/recorder.py` (the `update_learning_overlays()` call)
- [x] 3.5 Remove `auto_tune_enabled` from Aurora state response in `backend/api/routers/forecast.py`

## 4. Clean Up Removed Files

- [x] 4.1 Delete `ml/corrector.py`
- [x] 4.2 Delete `scripts/train_corrector.py`

## 5. Frontend — Remove Dead Toggles

- [x] 5.1 Remove "Error Correction" toggle and its handler (`handleErrorCorrectionToggle`) from `frontend/src/pages/Aurora.tsx`
- [x] 5.2 Remove "Auto-Tuner" toggle and its handler (`handleAutoTuneToggle`) from `frontend/src/pages/Aurora.tsx`
- [x] 5.3 Remove the `toggle_error_correction` API endpoint from `backend/api/routers/config.py`
- [x] 5.4 Remove related state variables and API client methods from frontend (`toggleErrorCorrection`, `error_correction_enabled` etc.)

## 6. Update Supporting Code

- [x] 6.1 Update `inputs.py` to remove any corrector-specific references or imports
- [x] 6.2 Update training schedule configuration for daily retraining (cron/orchestrator config)

## 7. Tests

- [x] 7.1 Delete corrector test files: `tests/ml/test_corrector.py`, `tests/ml/test_corrector_clamp.py`
- [x] 7.2 Update `tests/ml/test_ml_orchestrator.py` — remove corrector training mocks/assertions
- [x] 7.3 Update `tests/ml/test_ml_integration_complete.py` — remove `error_correction_enabled` config and corrector assertions
- [x] 7.4 Update `tests/backend/test_pipeline_spike_filtering.py` — remove any corrector/correction references
- [x] 7.5 Add test for `_compute_sample_weights()` verifying exponential decay behavior (1-day ≈ 1.0, 30-day ≈ 0.5, 180-day ≈ 0.05)
- [x] 7.6 Add test for `_train_regressor()` verifying sample weights are passed through to LightGBM
- [x] 7.7 Add test that `_load_slot_observations()` loads all available data (no days_back cap)
- [x] 7.8 Update `tests/ml/test_residual_training.py` if it references corrector or days_back (no changes needed)
- [x] 7.9 Run full test suite to catch any remaining corrector/analyst references

## 8. Documentation

- [x] 8.1 Update `docs/ARCHITECTURE.md` — remove Corrector from Aurora pipeline description, remove Analyst from async services list, document recency-weighted training approach
- [x] 8.2 Update `docs/RELEASE_NOTES.md` — document the removal of corrector/auto-tuner and addition of recency weighting
