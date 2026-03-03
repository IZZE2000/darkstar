## Why

The current PV forecasting system fails catastrophically on sunny days because the ML model was trained only on winter data (Dec-Mar) with maximum radiation of 434 W/m². When spring arrives with 800+ W/m² radiation, the model cannot extrapolate and predicts 0.085 kWh instead of the actual 0.5-0.8 kWh—an 85% error. The current "hybrid" is actually ML-first with physics as display-only, which fails when weather conditions exceed training data.

## What Changes

- **BREAKING**: Change the base PV forecast from ML prediction to Open-Meteo physics calculation
- **BREAKING**: Modify ML training to predict residuals (actual - physics) instead of direct PV values
- Modify the forward forecasting pipeline to use physics-based base + ML corrections
- Update the corrector model to learn physics residuals rather than forecast errors
- **BREAKING**: Change final PV forecast composition from `ML + correction` to `physics + ML_correction`
- Update API responses to ensure `final.pv_kwh` uses the physics-based calculation
- Ensure backward compatibility for existing forecast consumers

## Capabilities

### New Capabilities
- `physics-based-pv-forecasting`: Core capability for physics-first PV forecasting with Open-Meteo radiation data and configurable panel parameters

### Modified Capabilities
- `aurora-ml-pipeline`: Modify ML training to learn physics residuals instead of direct predictions
- `forecast-correction`: Update corrector to adjust physics forecasts rather than ML forecasts
- `forecast-generation`: Change forward forecasting to use physics base + ML residual

## Impact

- **ML Models**: PV models need retraining with new target (residuals)
- **Database Schema**: No changes required
- **API Changes**: `final.pv_kwh` will now reflect physics-based values
- **Configuration**: Users can tune physics parameters (efficiency, capacity)
- **Planner**: Will receive accurate sunny-day forecasts immediately
- **Dashboard**: Forecast vs Actual charts will show proper alignment
- **Reflex/Learning**: Confidence calculations will see reduced bias on sunny days
- **Breaking**: Any code relying on `base.pv_kwh` being ML-based will need updates

## Success Criteria

- Sunny day forecasts (800+ W/m² radiation) predict within 20% of actual
- Winter forecasts maintain current accuracy
- ML correction reduces residual error by 50% within 30 days of training
- No regression on cloudy day predictions
