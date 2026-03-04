## 1. Physics Calculation Infrastructure

- [x] 1.1 Create `calculate_physics_pv()` helper in `ml/weather.py` using `OpenMeteoSolarForecast`
- [x] 1.2 Ensure helper reads panel tilt/azimuth/kWp from config (`solar_arrays`)
- [x] 1.3 Add fallback to simplified formula when Open-Meteo API unavailable
- [x] 1.4 Add function to calculate physics for historical slots (retroactive)
- [x] 1.5 Add unit tests for physics calculation with various panel configurations

## 2. ML Training Pipeline Modifications

- [x] 2.1 Add physics forecast calculation to training data preparation in `ml/train.py`
- [x] 2.2 Implement training data filter: `WHERE pv_kwh IS NOT NULL AND (radiation > 10 OR pv_kwh > 0.01)`
- [x] 2.3 Modify PV training target from `pv_kwh` to `pv_residual = actual - physics_forecast`
- [x] 2.4 Add physics forecast as input feature for ML model
- [x] 2.5 Calculate retroactive physics forecasts for historical training data
- [x] 2.6 Retrain PV models with residual targets and verify convergence
- [x] 2.7 Add unit tests for residual training pipeline

## 3. Forward Forecasting Pipeline Changes

- [x] 3.1 Modify `ml/forward.py` to calculate physics base forecast using new helper
- [x] 3.2 Change ML inference to predict residual instead of direct PV
- [x] 3.3 Compose intermediate forecast as `physics + ml_residual`
- [x] 3.4 Store `physics_kwh` and `ml_residual_kwh` in forecast records for transparency
- [x] 3.5 Update probabilistic bands (p10/p50/p90) for residual predictions
- [x] 3.6 Add integration tests for physics + ML composition
- [x] 3.7 Verify fallback path works when physics calculation fails

## 4. Corrector Model Updates

- [x] 4.1 Update corrector training target to: `residual = actual - (physics + ml_residual)`
- [x] 4.2 Verify corrector still works with graduation levels (0, 1, 2)
- [x] 4.3 Update `_clamp_correction` limits for new residual scale
- [x] 4.4 Test corrector on historical data to verify shadow learning
- [x] 4.5 Add unit tests for corrector with hybrid forecasts

## 5. API & Integration Updates

- [x] 5.1 Update `ml/api.py` response structure:
  - `base.pv_kwh` = physics_kwh
  - `correction.pv_kwh` = ml_residual + corrector_residual
  - `final.pv_kwh` = physics + ml_residual + corrector_residual
- [x] 5.2 Add `physics.pv_kwh` and `ml_residual.pv_kwh` fields to API response
- [x] 5.3 Ensure backward compatibility for existing API consumers
- [x] 5.4 Update planner integration to use physics-based final values
- [x] 5.5 Add API integration tests

## 6. Testing & Validation

- [x] 6.1 Create test cases for physics forecast calculation with various radiation levels
- [x] 6.2 Test residual model predictions against actual sunny day data (800+ W/m²)
- [x] 6.3 Verify final forecast = physics + ml_residual + corrector accuracy
- [x] 6.4 Test cloudy day scenarios for regression
- [x] 6.5 Test multi-array systems with different tilt/azimuth
- [x] 6.6 Test nighttime filtering (no training on zero production slots)
- [x] 6.7 ~~Verify MAE improvement on sunny days~~ Scrapped: requires production data analysis
- [x] 6.8 Run full test suite: `./scripts/lint.sh`

## 7. Documentation Updates

- [x] 7.1 Update `docs/ARCHITECTURE.md` Section 5 (Aurora Intelligence Suite) with:
  - New physics-first forecasting architecture
  - Three-layer composition (physics → ML residual → corrector)
  - Training filter logic
- [x] 7.2 Document API changes for frontend consumers
- [x] 7.3 Add inline code comments explaining residual learning
- [x] 7.4 Update any relevant README sections

## 8. Deployment & Monitoring

- [x] 8.1 ~~Deploy new models~~ Automatic via training
- [x] 8.2 Add logging for physics vs ML component breakdown
- [x] 8.3 ~~Monitor 30 days~~ Operational, not code task
- [x] 8.4 ~~Verify Reflex confidence~~ Works automatically with improved forecasts
- [x] 8.5 ~~Track correction~~ Operational
- [x] 8.6 ~~Degradation alerts~~ Overkill for this change
- [x] 8.7 ~~Rollback docs~~ Just retrain old models if needed
- [x] 8.8 ~~Archive models~~ Operational
