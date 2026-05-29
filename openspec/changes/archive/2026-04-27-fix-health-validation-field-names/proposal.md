## Why

Three config health warnings fire as false positives for users on the v2 config schema — the validation code still references legacy field names from before the ARC14/ARC15 migrations, and a brand-new preflight check introduced in `feat(planner-diagnostics)` used the wrong field names from day one. The warnings were never visible to users until the health warning UI shipped, so the breakage went undetected for months.

## What Changes

- Fix `backend/health.py` solar check to read `system.solar_arrays[]` (plural list) instead of `system.solar_array` (singular legacy key)
- Fix `backend/health.py` water heater check to read `water_heaters[].power_kw` instead of `water_heating.power_kw`
- Fix `planner/preflight.py` battery check to read `battery.max_charge_w` / `battery.max_discharge_w` instead of `battery.max_charge_power_kw` / `battery.max_discharge_power_kw`

## Capabilities

### New Capabilities
<!-- None introduced — this is a pure correctness fix -->

### Modified Capabilities
- `planner-diagnostics`: Battery preflight field names are wrong; fix to match actual config schema
- `sensor-validation`: Health check field access for solar and water heater must reflect current config schema (ARC14/ARC15)

## Impact

- `backend/health.py`: lines ~399-431 (water heater and solar health checks)
- `planner/preflight.py`: lines ~31-32 (battery charge/discharge power field names)
- No API changes, no schema changes, no migrations — read-only validation logic only
