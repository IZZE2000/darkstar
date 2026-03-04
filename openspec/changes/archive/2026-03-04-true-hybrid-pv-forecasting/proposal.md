## Why

The current PV forecasting system fails catastrophically on sunny days because the ML model was trained only on winter data (Dec-Mar) with maximum radiation of 434 W/m². When spring arrives with 800+ W/m² radiation, the model cannot extrapolate and predicts 0.085 kWh instead of the actual 0.5-0.8 kWh—an 85% error. The current "hybrid" is actually ML-first with physics as display-only, which fails when weather conditions exceed training data.

## What Changes

- **BREAKING**: Change the base PV forecast from ML prediction to physics-based calculation using `OpenMeteoSolarForecast` with panel tilt/azimuth
- **BREAKING**: Modify ML training to predict residuals (actual - physics) instead of direct PV values
- Modify the forward forecasting pipeline to compose: `final = physics_base + ml_residual + corrector_residual`
- Update the corrector to learn residuals against the hybrid forecast (physics + ml_residual)
- Add training data filter to only train on slots with both actual PV and sun-up conditions
- Ensure `OpenMeteoSolarForecast` uses panel tilt/azimuth from config for accurate POA (Plane of Array) irradiance

## Capabilities

### New Capabilities
- `physics-based-pv-forecasting`: Core capability for physics-first PV forecasting with Open-Meteo radiation data and panel tilt/azimuth

### Modified Capabilities
- `aurora-ml-pipeline`: ML training now learns physics residuals instead of direct predictions
- `forecast-correction`: Corrector refines the hybrid forecast (physics + ML residual)
- `forecast-generation`: Forward forecasting composes physics + ML residual + corrector

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  PHYSICS BASE                                                   │
│  OpenMeteoSolarForecast(radiation, tilt, azimuth, kWp)          │
│  → physics_kwh = 0.65 kWh (sunny day estimate)                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  ML RESIDUAL (pv_model.lgb)                                     │
│  Learns long-term patterns: shadows, degradation, efficiency    │
│  → ml_residual_kwh = -0.08 kWh (e.g., chimney shade at 11-13h)  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    intermediate = 0.65 - 0.08 = 0.57 kWh
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  CORRECTOR (corrector.py)                                       │
│  Learns short-term patterns: weather forecast errors            │
│  → corrector_residual_kwh = -0.03 kWh                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    FINAL = 0.57 - 0.03 = 0.54 kWh
```

## Impact

- **ML Models**: PV models need retraining with residual targets
- **Database Schema**: No changes required
- **API Changes**: `base.pv_kwh` will reflect physics-based values, `final.pv_kwh` = physics + ML + corrector
- **Configuration**: Panel tilt/azimuth already configured; efficiency auto-learned by ML residual
- **Planner**: Will receive accurate sunny-day forecasts immediately (physics handles any radiation)
- **Dashboard**: Forecast vs Actual charts will show proper alignment
- **Reflex/Learning**: Confidence calculations will see reduced bias on sunny days
- **Breaking**: Any code expecting `base.pv_kwh` to be ML-based will need updates

## Success Criteria

- Sunny day forecasts (800+ W/m² radiation) predict within 20% of actual
- Winter forecasts maintain current accuracy
- ML residual learns hour-by-hour patterns (shadows) within 14 days
- No regression on cloudy day predictions
- Training only uses slots with actual PV data and sun-up conditions
