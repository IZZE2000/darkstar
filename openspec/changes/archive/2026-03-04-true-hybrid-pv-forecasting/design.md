## Context

### Current State
The Aurora ML pipeline currently uses an ML-first architecture for PV forecasting:
- **Training**: ML model learns `PV = f(weather_features)` directly from historical data
- **Inference**: ML predicts base PV from weather, corrector adds small adjustment
- **Open-Meteo**: Physics calculation exists but is display-only (`open_meteo_kwh` field)

This fails when radiation exceeds training maximum (434 W/m²) because ML cannot extrapolate to sunny day conditions (800+ W/m²).

### Existing Infrastructure
- **OpenMeteoSolarForecast** (`inputs.py:720-724`): Already uses panel tilt/azimuth for accurate POA irradiance
- **Corrector** (`ml/corrector.py`): Already learns residuals: `residual = actual - forecast`
- **Aurora Reflex** (`backend/learning/reflex.py`): Long-term auto-tuner for confidence and safety parameters

### Constraints
- Must maintain backward compatibility for existing API consumers
- Cannot break existing ML models for load forecasting (load models work well)
- Must work with existing database schema (no migrations)
- Should leverage existing `OpenMeteoSolarForecast` which already handles tilt/azimuth
- Users have varying panel configurations (kWp, tilt, azimuth) - already in config

## Goals / Non-Goals

**Goals:**
- Accurate PV forecasts on sunny days (800+ W/m²) within 20% error
- Immediate fix without waiting for summer training data
- ML learns hour-by-hour local corrections (shadows, panel degradation, efficiency)
- Corrector catches short-term weather forecast errors
- No regression on winter/cloudy day performance
- Minimal changes to existing infrastructure

**Non-Goals:**
- Replacing load forecasting ML (load models work fine)
- Changing database schema
- Rewriting the entire forecasting pipeline
- Per-panel micro-optimization (arrays handled as aggregate via OpenMeteoSolarForecast)
- Real-time sky imagery or satellite data integration
- User-configurable efficiency factor (ML learns it automatically)

## Decisions

### Decision 1: Physics Engine - OpenMeteoSolarForecast vs Simplified Formula
**Choice**: Use `OpenMeteoSolarForecast` from `inputs.py` as the physics engine

**Rationale**:
- Already exists and supports panel tilt/azimuth (POA irradiance)
- Handles multi-array systems with different orientations
- Uses Open-Meteo's solar position calculations
- More accurate than simplified `(rad/1000) × kWp × efficiency` formula
- Code reuse - same library used for fallback PV forecast in `inputs.py`

**Implementation**:
- Create reusable function in `ml/weather.py` that wraps `OpenMeteoSolarForecast`
- Use for both training (retroactive physics) and inference (forward forecasting)

### Decision 2: ML Residual vs ML Multiplier
**Choice**: ML learns additive residual `residual = actual - physics`

**Rationale**:
- Additive is easier to interpret and debug
- Works when physics over-predicts (shadows → negative residual) and under-predicts (panel degradation → positive residual)
- Additive doesn't amplify errors on sunny days (multiplicative would)
- Efficiency differences auto-learned: if real efficiency is 75% vs assumed 85%, ML learns consistent negative residual

**Training Target**:
```python
target = actual_pv_kwh - physics_forecast_kwh
```

### Decision 3: Training Data Filter
**Choice**: Only train on slots with actual PV data and sun-up conditions

**Filter Logic**:
```sql
WHERE pv_kwh IS NOT NULL                    -- Have actual measurement
  AND (radiation > 10 OR pv_kwh > 0.01)    -- Sun is up OR system producing
```

**Rationale**:
- Nighttime slots (radiation=0, pv=0) provide no learning value
- Residual = 0 - 0 = 0 is noise, not signal
- Filter captures: sunny slots, cloudy slots with production, edge cases
- Excludes: pure nighttime, sensor gaps, zero-production anomalies

### Decision 4: Corrector Integration
**Choice**: Corrector learns residuals against the hybrid forecast (Option A)

**Corrector Target**:
```python
residual = actual_pv_kwh - (physics_kwh + ml_residual_kwh)
```

**Rationale**:
- Corrector sits on top of everything
- Catches short-term patterns ML residual misses (today's weather forecast error)
- Clean separation of concerns:
  - **Physics**: Theoretical max based on radiation + panel geometry
  - **ML Residual**: Long-term patterns (fixed shadows, degradation, efficiency)
  - **Corrector**: Short-term patterns (weather forecast errors, daily conditions)

### Decision 5: No User-Configurable Efficiency
**Choice**: Efficiency is auto-learned by ML residual, not exposed in config

**Rationale**:
- KISS principle: One less config knob to tune
- ML residual naturally learns the difference between theoretical and actual efficiency
- If real efficiency is 75% instead of 85%, ML learns consistent ~-12% residual
- No user intervention required

**Default Physics Efficiency**: Use OpenMeteoSolarForecast's default (built into its model)

### Decision 6: Retroactive Physics Calculation
**Choice**: Calculate physics for all historical slots at migration time

**Implementation**:
1. Query historical `slot_observations` with `shortwave_radiation_w_m2` from weather
2. For each slot, calculate physics using `OpenMeteoSolarForecast`
3. Store physics values (can be cached or recalculated on demand)
4. Use for retraining ML models with residual targets

**Alternative**: Calculate on-the-fly during training - simpler but slower

## Architecture Diagram

```
                         ┌──────────────────────────────────────┐
                         │         INPUTS                       │
                         │  - Weather (radiation, temp, clouds) │
                         │  - Panel config (kWp, tilt, azimuth) │
                         └──────────────────────────────────────┘
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          FORWARD FORECAST (ml/forward.py)                │
├──────────────────────────────────────────────────────────────────────────┤
│  1. PHYSICS BASE                                                         │
│     OpenMeteoSolarForecast(radiation, tilt, azimuth, kWp)                │
│     → physics_kwh per slot                                               │
│                                                                          │
│  2. ML RESIDUAL                                                          │
│     pv_model.lgb predicts: residual = f(hour, day, weather, physics)     │
│     → ml_residual_kwh per slot                                           │
│                                                                          │
│  3. COMPOSE                                                              │
│     intermediate = physics_kwh + ml_residual_kwh                         │
│     → stored as pv_forecast_kwh                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          CORRECTOR (ml/corrector.py)                     │
├──────────────────────────────────────────────────────────────────────────┤
│  Level 0: No corrections (infant, <4 days data)                         │
│  Level 1: Statistical bias per (hour, day_of_week)                      │
│  Level 2: ML error model learns: residual = actual - (physics + ml)     │
│     → corrector_residual_kwh per slot                                    │
│                                                                          │
│  FINAL = intermediate + corrector_residual                               │
└──────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
                         ┌──────────────────────────────────────┐
                         │         OUTPUT                        │
                         │  final.pv_kwh = physics + ml + corr   │
                         │  API: base.pv_kwh = physics           │
                         │       correction.pv_kwh = ml + corr   │
                         └──────────────────────────────────────┘
```

## Risks / Trade-offs

**[Risk] ML residual model needs training data with physics baseline**
→ **Mitigation**: Calculate physics retroactively for historical data using stored radiation

**[Risk] Open-Meteo API changes or outages**
→ **Mitigation**: Fallback to simplified physics formula `(rad/1000) × kWp × 0.85 × 0.25h`

**[Risk] Physics over-predicts on heavily shaded systems**
→ **Mitigation**: ML residual learns negative correction for shadows within 14 days

**[Risk] Breaking change for API consumers expecting ML-based `base.pv_kwh`**
→ **Mitigation**:
  - Document that `base.pv_kwh` is now physics-based
  - `final.pv_kwh` remains the authoritative forecast
  - Add `physics.pv_kwh` and `ml_residual.pv_kwh` to API for transparency

**[Risk] Initial residual model has no training data**
→ **Mitigation**:
  - Start with residual = 0 (pure physics)
  - ML learns corrections as data accumulates
  - Corrector can still apply statistical adjustments immediately

**[Trade-off] Winter performance**
- Physics handles radiation well but may miss micro-climate patterns
- ML corrections will take time to learn (14+ days)
- Initial winter forecasts may be slightly less accurate until ML adapts

## Migration Plan

### Phase 1: Implementation (This change)
1. Create physics calculation helper in `ml/weather.py`
2. Modify `ml/train.py` to train on residuals with sun-up filter
3. Update `ml/forward.py` to use physics base + ML residual
4. Update `ml/corrector.py` to correct hybrid forecasts
5. Calculate retroactive physics for historical training data

### Phase 2: Validation
1. Run parallel forecasts (old vs new) for 7 days
2. Compare MAE metrics on sunny vs cloudy days
3. Verify shadow learning (hour-by-hour residual patterns)

### Phase 3: Deployment
1. Deploy new models with residual targets
2. Monitor dashboard for 14 days
3. Compare with Aurora Reflex confidence adjustments

### Phase 4: Documentation
1. Update `docs/ARCHITECTURE.md` with new forecasting flow
2. Document API changes for frontend consumers
3. Archive old ML-first models

### Rollback Strategy
- Restore previous model files from backup
- Revert to ML-first pipeline
- No database changes required
