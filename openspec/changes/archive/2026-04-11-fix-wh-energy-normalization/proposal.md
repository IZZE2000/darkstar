## Why

Beta testers with cumulative energy sensors reporting in Wh (e.g., `sensor.smart_meter_ts_65a_3_energy_real_consumed`) get broken energy recording and planner failures. The `_normalize_energy_to_kwh` function in `ha_client.py` only matches a narrow set of unit strings (`"WH"`, `"WATT_HOUR"`, etc.) and falls back to assuming kWh when the unit is unrecognized. When the HA sensor's `unit_of_measurement` doesn't exactly match (or is missing), raw Wh values like `5,675,983` are treated as kWh — 1000× too large. This causes bogus load profiles (5.6 GWh/day), infeasible MILP solver failures, and zero energy recordings on the dashboard.

## What Changes

- Make `_normalize_energy_to_kwh` robust against common Wh variants from real HA sensors (including missing units on high-value readings)
- Add heuristic detection: if no unit is set AND the raw value exceeds a reasonable kWh threshold, assume Wh and convert
- Add defensive sanity check in `get_load_profile_from_ha` to reject absurd daily totals before they reach the planner
- Log the detected unit and conversion clearly so beta testers can self-diagnose sensor config issues

## Capabilities

### New Capabilities

_None_

### Modified Capabilities

- `energy-recording`: Extend unit normalization to handle missing/ambiguous Wh sensors and add sanity bounds on load profile values

## Impact

- `backend/core/ha_client.py` — `_normalize_energy_to_kwh` function and `get_load_profile_from_ha`
- `backend/recorder.py` — relies on normalization for cumulative sensor deltas
- Planner — downstream beneficiary (no longer receives bogus load profiles)
- No API changes, no schema changes, backward compatible
