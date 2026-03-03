## Context

### Current State
The Aurora ML pipeline currently uses an ML-first architecture for PV forecasting:
- **Training**: ML model learns `PV = f(weather_features)` directly from historical data
- **Inference**: ML predicts base PV from weather, corrector adds small adjustment
- **Open-Meteo**: Physics calculation exists but is display-only (`open_meteo_kwh` field)

This fails when radiation exceeds training maximum (434 W/m²) because ML cannot extrapolate to sunny day conditions (800+ W/m²).

### Constraints
- Must maintain backward compatibility for existing API consumers
- Cannot break existing ML models for load forecasting (load models work well)
- Must work with existing database schema (no migrations)
- Should leverage Open-Meteo which already provides radiation forecasts
- Users have varying panel configurations (kWp, tilt, azimuth)

## Goals / Non-Goals

**Goals:**
- Accurate PV forecasts on sunny days (800+ W/m²) within 20% error
- Immediate fix without waiting for summer training data
- ML learns local corrections (shadows, panel degradation, efficiency)
- No regression on winter/cloudy day performance
- Minimal changes to existing infrastructure

**Non-Goals:**
- Replacing load forecasting ML (load models work fine)
- Changing database schema
- Rewriting the entire forecasting pipeline
- Per-panel micro-optimization (arrays handled as aggregate)
- Real-time sky imagery or satellite data integration

## Decisions

### Decision 1: Physics Formula vs Open-Meteo Native
**Choice**: Use Open-Meteo's native PV calculation when available, fallback to simplified physics

**Rationale**:
- Open-Meteo already has `calculate_per_array_pv()` with panel tilt/azimuth
- Reduces code duplication
- Open-Meteo accounts for solar position and panel orientation
- Simplified physics `(rad/1000) × kWp × 0.85 × 0.25` as reliable fallback

**Alternatives considered**:
- Pure physics formula: Rejected, loses panel orientation benefits
- ML-only with extended training window: Rejected, requires summer data not available

### Decision 2: ML Residual vs ML Multiplier
**Choice**: ML learns additive residual `residual = actual - physics`

**Rationale**:
- Additive is easier to interpret and debug
- Works when physics over-predicts (shadows) and under-predicts (panel degradation)
- Additive doesn't amplify errors on sunny days

**Alternatives considered**:
- Multiplicative factor: Rejected, could amplify errors significantly
- Hybrid add/mult: Too complex for initial implementation

### Decision 3: Training Target Change
**Choice**: Modify training to predict residual instead of direct PV

**Rationale**:
- Single model architecture change affects both training and inference
- Keeps existing LightGBM pipeline intact
- Residuals are stationary (mean ~0) making training more stable

**Implementation**:
- `ml/train.py`: Target becomes `pv_kwh - physics_forecast`
- `ml/forward.py`: Base becomes physics, ML adds residual
- `ml/corrector.py`: Already learning residuals, minimal changes

### Decision 4: Gradual Migration Strategy
**Choice**: Implement with feature flag, default to new behavior after validation

**Rationale**:
- Allows A/B testing of old vs new approach
- Easy rollback if issues arise
- Users can opt-in to test during development

## Risks / Trade-offs

**[Risk] ML residual model needs training data with physics baseline**
→ **Mitigation**: Calculate physics retroactively for historical data using stored radiation

**[Risk] Open-Meteo API changes or outages**
→ **Mitigation**: Fallback to simplified physics formula if Open-Meteo unavailable

**[Risk] Physics over-predicts on heavily shaded systems**
→ **Mitigation**: ML residual will learn negative correction for shadows over time

**[Risk] Breaking change for API consumers expecting ML-based `base.pv_kwh`**
→ **Mitigation**:
  - Keep `base.pv_kwh` as physics (breaking but documented)
  - Add new field `physics.pv_kwh` for clarity
  - Update documentation

**[Risk] Initial residual model has no training data**
→ **Mitigation**:
  - Start with residual = 0 (pure physics)
  - ML learns corrections as data accumulates
  - Corrector can still apply statistical adjustments immediately

**[Trade-off] Winter performance**
- Physics handles radiation well but may miss micro-climate patterns
- ML corrections will take time to learn
- Initial winter forecasts may be slightly less accurate until ML adapts

## Migration Plan

### Phase 1: Implementation (This change)
1. Modify `ml/train.py` to train on residuals
2. Update `ml/forward.py` to use physics base + ML residual
3. Update `ml/corrector.py` to correct physics forecasts
4. Ensure `final.pv_kwh` = physics + ML_corrections

### Phase 2: Validation
1. Run parallel forecasts (old vs new) for 7 days
2. Compare MAE metrics
3. Verify sunny day accuracy improvement

### Phase 3: Deployment
1. Deploy new models
2. Retrain with residual target
3. Monitor dashboard for 14 days

### Phase 4: Cleanup
1. Remove old ML-first code paths (if feature flagged)
2. Update documentation
3. Archive old models

### Rollback Strategy
- Restore previous model files from backup
- Revert to ML-first pipeline
- No database changes required

## Open Questions

1. **Configuration**: Should we expose physics efficiency factor in config.yaml for user tuning?
2. **Multi-array**: How to handle systems with multiple arrays at different tilts/orientations?
3. **Shading**: Should we add a "shading factor" configuration for known obstructions?
4. **Validation**: How to validate during winter when sunny days are rare?
