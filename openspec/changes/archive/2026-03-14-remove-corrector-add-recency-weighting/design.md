## Context

The AURORA forecasting pipeline currently has three overlapping correction/tuning systems:

1. **Base model** (`ml/forward.py`): LightGBM quantile regression (p10/p50/p90) for load and PV, trained on 90 days of historical data
2. **Corrector** (`ml/corrector.py`): Stats bias (14-day rolling average residuals per day_of_week/hour) + ML error model, writes `load_correction_kwh`/`pv_correction_kwh` to DB, applied in `ml/api.py` as `final = base + correction`
3. **Auto-Tuner/Analyst** (`backend/learning/analyst.py`): Computes hourly bias adjustments (7-day `actual - forecast` per hour), writes to `learning_daily_metrics`, applied in `planner/inputs/data_prep.py` as `adjusted = forecast + hourly_bias`
4. **Aurora Reflex** (`backend/learning/reflex.py`): Tunes policy parameters (s_index safety margin, PV confidence, battery cycle cost) — NOT a forecast correction system

Systems 2 and 3 are architecturally coupled to the base model version: they train on `actual - historical_forecast`, where historical forecasts were produced by a previous model version. After any base model retrain, both apply stale corrections calibrated to the old model. Since they stack (corrector adjusts DB values, then Auto-Tuner adjusts again in the planner), the effect is doubled.

The Auto-Tuner also computes `s_index_base_factor`, which duplicates Reflex's Safety Analyzer — both adjust the same parameter independently.

## Goals / Non-Goals

**Goals:**
- Remove both the Corrector and Auto-Tuner forecast bias systems to eliminate version-coupling bugs and double-correction
- Make the base model self-sufficient by training on all available data with recency weighting
- Simplify the inference pipeline to a single step (base model → DB → planner)
- Remove the "Error Correction" and "Auto-Tuner" UI toggles
- Consolidate `s_index_base_factor` ownership in Reflex (already does this)
- Maintain cold-start behavior for new users (graduation path)
- Ensure backward-compatible API responses and DB schema

**Non-Goals:**
- Changing the LightGBM model architecture or features (the 11 features stay)
- Modifying the PV hybrid physics model
- Changing the DB schema (correction columns and learning_daily_metrics stay, just unused)
- Modifying Aurora Reflex (it tunes policy, not forecasts)
- Optimizing training performance or model hyperparameters

## Decisions

### 1. Remove both correction systems, not just the Corrector

**Decision**: Remove the Corrector (`ml/corrector.py`) AND the Auto-Tuner's hourly bias adjustments (`analyst.py` + `data_prep.py`).

**Alternatives considered**:
- *Remove only the Corrector, keep Auto-Tuner*: Leaves one layer of the same bug in place, and the Auto-Tuner has the same version-coupling problem
- *Fix both to be version-aware*: Adds complexity (version tagging, filtered training) for marginal benefit over recency-weighted retraining

**Rationale**: Both systems do the same thing (compute `actual - forecast` bias and apply additive corrections) at different points in the pipeline. Both have the same architectural flaw. Removing both eliminates the double-correction and the version-coupling bug entirely.

### 2. Keep the Analyst class but remove its forecast bias logic

**Decision**: The Analyst's `s_index_base_factor` computation duplicates Reflex's Safety Analyzer. Remove the Analyst's hourly bias arrays (`pv_adjustment_by_hour_kwh`, `load_adjustment_by_hour_kwh`) and its `s_index_base_factor` calculation. The Analyst class can be deleted entirely since Reflex already handles `s_index_base_factor` and the hourly adjustments are being removed.

**Rationale**: Reflex already owns `s_index_base_factor` tuning with better bounds, rate limiting, and a multi-analyzer architecture. Having two systems adjust the same parameter independently is a conflict.

### 3. Exponential decay weighting for training samples

**Decision**: Use exponential decay sample weights: `weight = exp(-lambda * days_ago)` where lambda is tuned so data from 30 days ago has ~50% weight and data from 180 days ago has ~5% weight.

**Alternatives considered**:
- *Linear decay*: Simpler but gives too much weight to very old data or too little to moderately recent data
- *Hard window (current 90-day cap)*: Loses seasonal patterns entirely
- *Step function (recent data 10x)*: Too abrupt, creates training artifacts at the boundary

**Rationale**: Exponential decay is the standard approach in time-series ML. It provides smooth transition from high-weight recent data to low-weight historical data. LightGBM supports per-sample weights natively via the `sample_weight` parameter in `.fit()`.

### 4. Use all available data, no hard cap

**Decision**: Remove the `days_back=90` default in `TrainingConfig`. Train on all data in `slot_observations`.

**Rationale**: More data provides better seasonal pattern coverage. The recency weighting ensures old data doesn't dominate. Existing validation filters (load > 0.001, max_kwh cap) protect against bad data.

### 5. Keep correction columns and learning_daily_metrics in DB schema

**Decision**: Stop writing to correction columns and hourly adjustment columns but leave them in the schema.

**Rationale**: Avoids a migration. Columns will contain NULL/0 for new rows. No downstream code will read them after the changes.

### 6. Simplify API return structure

**Decision**: In `get_forecast_slots()`, `final.load_kwh` will equal `base.load_kwh` directly (no correction added). Keep the nested structure for backward compatibility.

**Rationale**: Frontend and planner consume `final.load_kwh`. Making it equal to base means no behavior change for consumers — they just get better values.

### 7. Remove UI toggles for Error Correction and Auto-Tuner

**Decision**: Remove both toggles from `Aurora.tsx`. Keep only the "Aurora Reflex" toggle (policy tuning) and "Probabilistic" toggle (s-index mode).

**Rationale**: The features behind these toggles are being removed. Leaving dead toggles in the UI would be confusing.

## Risks / Trade-offs

- **[Temporary accuracy dip after deploy]** → First few days after removing correction layers, any beneficial corrections are lost. Mitigated by: the corrections were actively harmful in the common case (post-retrain), and daily retraining means the base model adapts within 1-2 days.

- **[Loss of very-short-term adaptation]** → Corrector/Auto-Tuner could react within hours. Base model retrains daily. Mitigated by: exponential recency weighting means yesterday's data has high influence, and most behavioral patterns don't change hour-to-hour.

- **[Training time increase with more data]** → Using all historical data instead of 90 days means more training samples. Mitigated by: LightGBM is extremely fast, even 100k samples trains in seconds on commodity hardware.

- **[Decay parameter tuning]** → The lambda parameter in exponential decay affects adaptation speed. Mitigated by: start with a well-understood default (half-life = 30 days), can be adjusted via config without code changes.

- **[s_index_base_factor ownership]** → Removing the Analyst's s_index calculation means only Reflex adjusts it. Mitigated by: Reflex already does this with better bounds and rate limiting. No behavior gap.
