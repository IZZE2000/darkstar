## 1. Fix battery preflight field names

- [x] 1.1 In `planner/preflight.py` `check_battery_config()`, read `battery.get("max_charge_w", 0.0) / 1000` and `battery.get("max_discharge_w", 0.0) / 1000` instead of the `_power_kw` variants; update the `details` dict field names in the two raised errors to match

## 2. Fix solar health check

- [x] 2.1 In `backend/health.py`, replace the `solar_array` singular `.get()` with logic that reads `system_cfg.get("solar_arrays", [])` and checks if any entry has `kwp > 0`
- [x] 2.2 Update the solar warning `guidance` string to reference `system.solar_arrays[].kwp` instead of `system.solar_array.kwp`

## 3. Fix water heater health check

- [x] 3.1 In `backend/health.py`, replace the `water_heating.power_kw` check (lines ~399-414) with logic that reads `self._config.get("water_heaters", [])` and checks if any enabled entry has `power_kw > 0`
- [x] 3.2 Update the water heater warning `guidance` string to reference `water_heaters[].power_kw` instead of `water_heating.power_kw`
