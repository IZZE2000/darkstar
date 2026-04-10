## 1. Replace Legacy Open-Meteo Calculation

- [x] 1.1 In `ml/api.py`, replace the Open-Meteo block (lines 107-121) to populate `open_meteo_data` from the already-computed `physics_data` dict instead of calling `calculate_per_array_pv()`
- [x] 1.2 Remove `calculate_per_array_pv` from the import statement in `ml/api.py`

## 2. Remove Legacy Functions

- [x] 2.1 Delete `calculate_pv_from_radiation()` from `ml/weather.py`
- [x] 2.2 Delete `calculate_per_array_pv()` from `ml/weather.py`

## 3. Fix Azimuth Convention Bug

- [x] 3.1 In `ml/weather.py:190`, convert solar azimuth from North convention to South convention: `solar_azimuth = solar_pos["azimuth"] - 180.0`
- [x] 3.2 Update test assertion in `test_aurora_forward.py` to reflect correct physics values (threshold from 2.0 to 4.0 kWh)

## 4. Chart UX Improvements

- [x] 4.1 Fix timeline labels in `ProbabilisticChart.tsx` to include day abbreviation using `toLocaleString()` with `weekday: 'short'`
- [x] 4.2 Fix timeline labels in `DecompositionChart.tsx` to include day abbreviation
- [x] 4.3 Remove SoC Tunnel view from Forecast Horizon card (remove `viewMode` state, toggle buttons, and SoC chart rendering)
- [x] 4.4 Change default chart mode to 'pv' in `Aurora.tsx`
- [x] 4.5 Remove unused `Line` import from `Aurora.tsx`

## 5. Verify

- [x] 5.1 Run existing tests to ensure no regressions (`pytest tests/ml/`)
- [x] 5.2 Verify no other imports or references to the removed functions exist
- [x] 5.3 Run full lint suite (`./scripts/lint.sh`)
