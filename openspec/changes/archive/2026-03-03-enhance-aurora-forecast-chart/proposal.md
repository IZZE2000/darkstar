## Why

The Aurora Forecast Horizon (48h) chart currently shows Aurora ML forecasts (P10, P50, P90) but lacks comparison with the raw Open-Meteo weather model forecast that Aurora uses as input. Users cannot see how Aurora's ML corrections differ from the baseline weather model, making it harder to understand forecast confidence and model behavior. Additionally, the "Actual" line exists but is invisible because the chart uses a rolling window that hides past data, and the window is not anchored to calendar days.

## What Changes

- **Fixed 48h window**: Chart now shows 00:00 today to 00:00 tomorrow (always 48h, anchored to calendar days instead of rolling from current time)
- **Open-Meteo forecast line**: New solid line showing PV estimate derived directly from Open-Meteo radiation data (sum of all arrays)
- **Per-array dashed lines**: Individual dashed lines for each configured solar array's Open-Meteo forecast
- **Visible Actual line**: Historical actual PV production now visible in the fixed window
- **Toggle-able lines**: Users can click legend labels to show/hide individual lines (existing Chart.js behavior preserved)

## Capabilities

### New Capabilities

- `open-meteo-pv-forecast`: Capability to derive and display PV production estimates from Open-Meteo weather radiation data, with support for multiple solar array configurations

### Modified Capabilities

- None (this is a new visualization feature, not changing existing spec behavior)

## Impact

**Frontend:**
- `frontend/src/components/ProbabilisticChart.tsx` - Add Open-Meteo dataset(s) with per-array dashed lines
- `frontend/src/pages/Aurora.tsx` - Fixed 48h window logic, pass Open-Meteo data
- `frontend/src/lib/types.ts` - Add `open_meteo_kwh` and `open_meteo_arrays` to horizon slot types

**Backend:**
- `backend/api/routers/forecast.py` - Populate `history_series` with actual observations, add Open-Meteo PV estimates to slots
- `ml/weather.py` - Add function to calculate PV estimate from radiation data
- `ml/api.py` - Include Open-Meteo data in forecast slot responses

**API:**
- `AuroraHorizonSlot` type extended with `open_meteo_kwh` (sum) and `open_meteo_arrays` (per-array breakdown)
- `AuroraHorizon` type extended with `history_series` containing actual observations
