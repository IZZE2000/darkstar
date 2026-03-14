## MODIFIED Requirements

### Requirement: Open-Meteo PV Calculation

The backend SHALL calculate per-array PV production estimates from Open-Meteo radiation data using physics-based POA (Plane of Array) irradiance calculation that accounts for each array's tilt and azimuth.

The calculation SHALL use `calculate_physics_pv()` with:
- `radiation_w_m2` = shortwave radiation from Open-Meteo (W/m²)
- `solar_arrays` = array configs including `kwp`, `tilt`, and `azimuth`
- `slot_start` = timestamp for solar position calculation
- `latitude` / `longitude` = system location

The solar azimuth SHALL be converted from North convention (0°=North, clockwise) to South convention (0°=South, positive=West) before calculating POA irradiance.

#### Scenario: Per-array curves reflect panel orientation

- **WHEN** the system has multiple solar arrays with different tilt/azimuth values
- **THEN** the Open-Meteo per-array lines SHALL show different curve shapes reflecting each array's orientation relative to the sun's path

#### Scenario: PV calculated using physics model

- **WHEN** Open-Meteo radiation data is available for a time slot
- **THEN** the system SHALL calculate PV estimates using POA irradiance with tilt, azimuth, and solar position

#### Scenario: Per-array capacity used for individual lines

- **WHEN** calculating per-array PV estimates
- **THEN** the system SHALL use that array's `kwp`, `tilt`, and `azimuth` values

#### Scenario: Null returned for missing radiation data

- **WHEN** Open-Meteo radiation data is unavailable for a time slot
- **THEN** the system SHALL return null for that slot's Open-Meteo PV estimate

#### Scenario: Azimuth convention correctly converted

- **WHEN** calculating POA irradiance for a south-facing panel at solar noon
- **THEN** the angle-of-incidence SHALL be near zero (direct beam aligned with panel normal)
- **AND** the PV estimate SHALL be approximately `(radiation/1000) × kwp × efficiency × 0.25h`

## REMOVED Requirements

### Requirement: Legacy simplified PV functions

**Reason**: `calculate_per_array_pv()` and `calculate_pv_from_radiation()` used a simplified formula `(radiation/1000) × kWp × efficiency × 0.25h` that ignores panel orientation. Superseded by `calculate_physics_pv()` which uses POA irradiance.

**Migration**: All callers switched to `calculate_physics_pv()`. The only caller was the Open-Meteo graph data path in `ml/api.py`.
