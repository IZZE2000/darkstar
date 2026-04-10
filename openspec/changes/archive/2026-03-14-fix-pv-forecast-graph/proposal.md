## Why

The Aurora Forecast Horizon PV chart shows per-array Open-Meteo lines with identical curve shapes (differing only by amplitude), because the backend uses a simplified formula that ignores panel tilt and azimuth. Users with arrays at different orientations see misleading identical curves instead of orientation-dependent production profiles. The physics-based calculation (`calculate_physics_pv`) already exists and is used for ML forecasting — it just isn't used for the graph data path.

Additionally, a critical azimuth convention bug in `calculate_physics_pv()` caused ~10x underestimation of PV values, and the chart UI had usability issues (timeline labels didn't show day, SoC view was unwanted, load was default instead of PV).

## What Changes

- Replace `calculate_per_array_pv()` with `calculate_physics_pv()` in the Open-Meteo graph data path (`ml/api.py`)
- Remove the legacy `calculate_per_array_pv()` and `calculate_pv_from_radiation()` functions from `ml/weather.py` (single caller, no tests, superseded by physics-based calculation)
- Fix azimuth convention mismatch in `calculate_physics_pv()` — solar azimuth from North convention must be converted to South convention
- Update the `open-meteo-pv-forecast` spec to require physics-based POA irradiance calculation instead of the simplified linear formula
- Improve chart UX: timeline labels include day, remove SoC Tunnel view, default to PV mode

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `open-meteo-pv-forecast`: The "Open-Meteo PV Calculation" requirement changes from a simplified linear formula to physics-based POA irradiance calculation using tilt/azimuth per array

## Impact

- **Backend**: `ml/api.py` (Open-Meteo data generation), `ml/weather.py` (remove two legacy functions, fix azimuth bug)
- **Frontend**: `Aurora.tsx`, `ProbabilisticChart.tsx`, `DecompositionChart.tsx` (timeline labels, remove SoC view, default to PV)
- **Data accuracy**: Per-array Open-Meteo lines now show correct orientation-dependent production profiles with accurate magnitude
