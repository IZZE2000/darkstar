## Why

The AURORA forecast pipeline has three overlapping correction/tuning systems that independently adjust forecast values: the Corrector (`ml/corrector.py`), the Auto-Tuner/Analyst (`backend/learning/analyst.py`), and Aurora Reflex (`backend/learning/reflex.py`). The Corrector and Auto-Tuner both compute `actual - forecast` bias and apply additive corrections — the Corrector in the DB via `ml/pipeline.py`, and the Auto-Tuner in the planner via `data_prep.py`. Both suffer from the same architectural flaw: they train on residuals from the previous base model version, so every retrain makes their corrections stale or actively harmful. This double correction is causing unrealistically low load forecasts for users (including beta testers). Aurora Reflex is unrelated — it tunes policy parameters (safety margins, PV confidence, battery costs), not forecast values.

The base LightGBM model is capable of handling adaptation on its own with two targeted improvements: using all available historical data (currently capped at 90 days) and applying recency weighting so it adapts quickly to behavioral changes — replacing what both the Corrector and Auto-Tuner were trying to do.

## What Changes

- **BREAKING**: Remove the Corrector layer entirely — delete `ml/corrector.py`, remove error model files (`pv_error.lgb`, `load_error.lgb`), remove correction columns from the inference pipeline (`ml/pipeline.py`), remove corrector training from the orchestrator, remove "Error Correction" toggle from frontend
- **BREAKING**: Remove the Auto-Tuner/Analyst hourly bias adjustments — remove `backend/learning/analyst.py` hourly forecast bias logic, remove per-hour adjustment application from `planner/inputs/data_prep.py`, remove "Auto-Tuner" toggle from frontend. The Analyst's `s_index_base_factor` calculation is already duplicated in Reflex — Reflex owns it going forward.
- **BREAKING**: Remove correction application from forecast API (`ml/api.py`) — base model output becomes final output directly
- Remove the 90-day training data cap in `ml/train.py` — use all available historical data from the DB
- Add recency weighting to base model training — weight recent samples higher using LightGBM's native sample weight support, so the model adapts quickly to new patterns without correction layers
- Update training schedule from twice-weekly to daily
- Clean up DB writes — `store_forecasts()` no longer needs to preserve correction columns on UPSERT
- Keep the cold-start graduation path for new users (fallback behavior when insufficient data)
- Keep Aurora Reflex unchanged — it tunes policy parameters, not forecast values

## Capabilities

### New Capabilities
- `recency-weighted-training`: Sample weighting strategy for LightGBM training that gives recent data exponentially higher influence while retaining long-term seasonal patterns from older data

### Modified Capabilities
- `aurora-corrector`: **REMOVED** — The corrector capability is being deleted entirely. The corrector spec will be archived.

## Impact

- **Files removed**: `ml/corrector.py`, `scripts/train_corrector.py`, error model files on disk
- **Files modified**: `ml/pipeline.py` (simplify to single step), `ml/api.py` (remove correction application), `ml/train.py` (remove 90-day cap, add recency weighting), `ml/forward.py` (remove corrector imports), `ml/training_orchestrator.py` (remove corrector training step), `backend/learning/store.py` (simplify UPSERT), `backend/learning/analyst.py` (remove hourly bias adjustment logic), `planner/inputs/data_prep.py` (remove per-hour learning adjustments), `planner/inputs/learning.py` (remove hourly adjustment overlay loading), `inputs.py` (remove corrector references), `frontend/src/pages/Aurora.tsx` (remove "Error Correction" and "Auto-Tuner" toggles), `backend/api/routers/config.py` (remove toggle endpoint), `backend/api/routers/forecast.py` (remove auto_tune_enabled from state)
- **DB schema**: Correction columns (`pv_correction_kwh`, `load_correction_kwh`, `correction_source`) and `learning_daily_metrics` hourly adjustment columns become unused (leave in schema for backward compatibility, just stop writing them)
- **API**: `get_forecast_slots()` return structure changes — `final.load_kwh` will equal `base.load_kwh` (no correction added). Aurora state endpoint removes `auto_tune_enabled` and `error_correction_enabled` fields.
- **Config keys**: `learning.error_correction_enabled` and `learning.auto_tune_enabled` become unused (leave in config for backward compatibility)
- **Tests**: Corrector-related and analyst-related tests removed/updated
- **Training schedule**: Config change for daily retraining
