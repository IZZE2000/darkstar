## Context

The Aurora Forecast Horizon chart displays two types of PV data:
1. **Physics-based forecast** (line 95 in `ml/api.py`) — uses `calculate_physics_pv()` with POA irradiance, tilt/azimuth, and solar position. This is correct.
2. **Open-Meteo overlay lines** (line 115 in `ml/api.py`) — uses legacy `calculate_per_array_pv()` which applies `(radiation/1000) × kWp × efficiency × 0.25h`. This ignores panel orientation entirely.

The physics-based calculation already iterates over all arrays with their tilt/azimuth and produces per-array results. The Open-Meteo path can simply reuse this same data.

**Post-implementation discovery:** The physics calculation had an azimuth convention bug. `_calculate_solar_position()` returns azimuth in North convention (0°=North, clockwise), but `_calculate_poa_irradiance()` expects South convention (0°=South, positive=West). This 180° offset caused the direct beam angle-of-incidence to be near-zero at solar noon, reducing physics PV estimates to ~10% of actual (diffuse-only).

## Goals / Non-Goals

**Goals:**
- Per-array Open-Meteo lines reflect actual panel orientation (tilt/azimuth)
- Remove dead legacy code (`calculate_per_array_pv`, `calculate_pv_from_radiation`)
- Fix azimuth convention mismatch to produce correct PV magnitude
- Improve chart UX: day labels, remove SoC view, default to PV mode

**Non-Goals:**
- Changing the ML forecast pipeline structure (already uses physics-based calculation)
- Changing the frontend chart rendering logic (already handles per-array data correctly)

## Decisions

### Reuse physics_data instead of computing Open-Meteo separately

The `get_forecast_slots()` function already computes physics-based per-array data at line 95 and stores it in `physics_data[ts_str]["physics_arrays"]`. The Open-Meteo block (lines 107-121) computes the same thing but with the wrong formula.

**Decision:** Replace the Open-Meteo block to read from the already-computed `physics_data` instead of calling a separate function. This eliminates redundant computation and ensures both paths use the same physics calculation.

**Alternative considered:** Call `calculate_physics_pv()` a second time in the Open-Meteo block. Rejected because the data is already computed 10 lines above.

### Remove legacy functions entirely

`calculate_per_array_pv()` and `calculate_pv_from_radiation()` have a single caller, no tests, and are superseded by `calculate_physics_pv()`. There is also a `calculate_physics_pv_simple()` which serves as an internal fallback within `calculate_physics_pv()` — this stays.

**Decision:** Delete both legacy functions from `ml/weather.py` and remove the import from `ml/api.py`.

### Fix azimuth convention in calculate_physics_pv

The `_calculate_solar_position()` function returns azimuth in meteorological North convention (0°=North, clockwise). However, `_calculate_poa_irradiance()` expects solar azimuth in South convention (0°=South, positive=West) to match the panel azimuth convention used by Home Assistant.

**Decision:** Convert solar azimuth at line 190 in `calculate_physics_pv()`:
```python
solar_azimuth = solar_pos["azimuth"] - 180.0
```

This single-line fix aligns conventions. The cosine in the AOI formula is periodic, so no range clamping needed.

**Impact on ML forecasting:** The ML forward pass also calls `calculate_physics_pv()`, so it had the same broken physics base. The ML residual model learned to compensate with inflated residuals. After this fix:
1. Physics values increase ~10x → correct POA-based estimates
2. Existing ML models temporarily overshoot (inflated residuals)
3. Next training cycle recalculates physics retroactively → models retrain with correct residuals
4. Steady state: physics carries most signal, ML residual is small (shadows/efficiency)

### Chart UX improvements

**Timeline labels:** Both `ProbabilisticChart.tsx` and `DecompositionChart.tsx` used `toLocaleTimeString()` showing only time (e.g., "14:00"), making all three days indistinguishable. Changed to `toLocaleString()` with `weekday: 'short'` to show day abbreviations (e.g., "Sat 14:00").

**Remove SoC Tunnel view:** The Forecast Horizon card had a Forecast/SoC toggle, but SoC Tunnel wasn't needed. Removed `viewMode` state, SoC chart rendering, and the toggle buttons.

**Default to PV mode:** Changed default `chartMode` from `'load'` to `'pv'` since solar production is the primary interest.

## Risks / Trade-offs

[Numerical change in Open-Meteo line values] → Expected and desired. The lines will now show orientation-dependent curves with correct magnitude instead of flat-scaled copies at 10% of actual.

[ML forecast temporary overshoot] → Self-healing via daily training with retroactive physics recalculation. Overshoot period lasts at most one training cycle.
