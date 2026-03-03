## 1. ML Training Pipeline Modifications

- [ ] 1.1 Add physics forecast calculation to training data preparation in `ml/train.py`
- [ ] 1.2 Modify PV training target from `pv_kwh` to `pv_residual = actual - physics_forecast`
- [ ] 1.3 Calculate retroactive physics forecasts for historical data using stored radiation
- [ ] 1.4 Update feature engineering to include physics forecast as input feature
- [ ] 1.5 Retrain PV models with residual targets and verify convergence

## 2. Forward Forecasting Pipeline Changes

- [ ] 2.1 Modify `ml/forward.py` to calculate physics base forecast first
- [ ] 2.2 Change ML inference to predict residual instead of direct PV
- [ ] 2.3 Compose final forecast as `physics + ml_residual` instead of `ml + correction`
- [ ] 2.4 Update stored forecast structure to include physics base in `base.pv_kwh`
- [ ] 2.5 Ensure `final.pv_kwh` equals physics + residual in API responses

## 3. Corrector Model Updates

- [ ] 3.1 Update `ml/corrector.py` training to learn physics residuals
- [ ] 3.2 Modify correction application to adjust physics base (not ML base)
- [ ] 3.3 Update `_clamp_correction` limits for physics-based residuals
- [ ] 3.4 Test corrector on historical sunny days to verify shadow learning
- [ ] 3.5 Retrain corrector models with new residual targets

## 4. Open-Meteo Integration Enhancement

- [ ] 4.1 Ensure `ml/api.py` uses Open-Meteo calculation as primary physics base
- [ ] 4.2 Implement fallback to simplified physics when Open-Meteo unavailable
- [ ] 4.3 Add configuration options for `pv_system_efficiency` in config.yaml
- [ ] 4.4 Add configuration option for `pv_capacity_override_kwp` override
- [ ] 4.5 Calculate per-array physics forecasts using tilt/azimuth from config

## 5. Testing & Validation

- [ ] 5.1 Create test cases for physics forecast calculation
- [ ] 5.2 Test residual model predictions against actual sunny day data
- [ ] 5.3 Verify final forecast = physics + residual accuracy
- [ ] 5.4 Test cloudy day scenarios for regression
- [ ] 5.5 Run parallel forecasts (old vs new) for 7-day validation
- [ ] 5.6 Verify MAE improvement on sunny days (>20% accuracy target)

## 6. API & Integration Updates

- [ ] 6.1 Update `ml/api.py` response structure for physics-based forecasts
- [ ] 6.2 Ensure backward compatibility for existing API consumers
- [ ] 6.3 Update Aurora dashboard to display physics base line
- [ ] 6.4 Document breaking changes in API responses
- [ ] 6.5 Update planner integration to use physics-based final values

## 7. Documentation & Deployment

- [ ] 7.1 Document new physics-based forecasting approach
- [ ] 7.2 Add configuration examples for efficiency and capacity tuning
- [ ] 7.3 Create migration guide for users with custom integrations
- [ ] 7.4 Deploy new models and monitor dashboard metrics
- [ ] 7.5 Archive old ML-first models after 30-day validation period

## 8. Monitoring & Rollback

- [ ] 8.1 Add logging for physics vs ML component breakdown
- [ ] 8.2 Monitor PV forecast MAE improvement over 30 days
- [ ] 8.3 Create rollback procedure documentation
- [ ] 8.4 Set up alerts for forecast accuracy degradation
- [ ] 8.5 Track ML correction learning progress on shadow patterns
