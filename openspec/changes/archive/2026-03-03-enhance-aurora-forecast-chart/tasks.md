## 1. Backend - Data Layer

- [x] 1.1 Add `calculate_pv_from_radiation()` function to `ml/weather.py` that computes PV estimate from shortwave radiation
- [x] 1.2 Add function to calculate per-array PV estimates (iterate `solar_arrays` config)
- [x] 1.3 Add `get_history_with_actuals()` helper to fetch past slot observations from `SlotObservation` table

## 2. Backend - API Layer

- [x] 2.1 Extend `ml/api.py` `get_forecast_slots()` to include `open_meteo_kwh` and `open_meteo_arrays` in response
- [x] 2.2 Update `backend/api/routers/forecast.py` `aurora_dashboard()` to populate `history_series` with actual PV observations
- [x] 2.3 Update `aurora_dashboard()` to use fixed 48h window (00:00 today → 00:00 day after tomorrow)
- [x] 2.4 Fetch Open-Meteo radiation data and calculate PV estimates within `aurora_dashboard()`

## 3. Frontend - Types

- [x] 3.1 Add `open_meteo_kwh` and `open_meteo_arrays` to `AuroraHorizonSlot` type in `frontend/src/lib/types.ts`
- [x] 3.2 Add `open_meteo_kwh` to `SlotData` type in `ProbabilisticChart.tsx` (or extend type)

## 4. Frontend - Chart Component

- [x] 4.1 Add Open-Meteo sum line dataset to `ProbabilisticChart.tsx` using amber color (`--color-warn`)
- [x] 4.2 Add per-array dashed line datasets to `ProbabilisticChart.tsx`
- [x] 4.3 Ensure legend click-to-toggle works for all new datasets (Chart.js default behavior)

## 5. Frontend - Aurora Page

- [x] 5.1 Update `Aurora.tsx` to pass Open-Meteo data to `ProbabilisticChart`
- [x] 5.2 Change chart window logic from rolling (`now ± 24h`) to fixed (`00:00 today → 00:00 day after tomorrow`)
- [x] 5.3 Wire up `history_series` actuals to the `Actual` line in the chart

## 6. Testing & Verification

- [x] 6.1 Manually verify chart displays Open-Meteo line with correct values
- [x] 6.2 Manually verify per-array dashed lines display correctly
- [x] 6.3 Manually verify legend toggle works for all lines
- [x] 6.4 Manually verify fixed 48h window resets at midnight
- [x] 6.5 Manually verify Actual line shows historical data
- [x] 6.6 Run lint/typecheck: `./scripts/lint.sh`
