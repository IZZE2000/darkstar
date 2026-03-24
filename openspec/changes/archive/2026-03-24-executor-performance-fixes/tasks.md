## 1. Config/Profile Caching

- [x] 1.1 Add mtime-based cache to `reload_config()` in `executor/engine.py`: store `_config_mtime` as an instance variable (initialized to `None` in `__init__`). At the top of `reload_config()`, call `os.path.getmtime(self.config_path)` and compare to `_config_mtime`. If unchanged, return early — the entire method can be short-circuited because all subsequent operations (status flag updates, profile reload) derive from the config and can be skipped together.
- [x] 1.2 Add mtime-based cache for profile YAML in `executor/engine.py`: store `_profile_mtime` as an instance variable (initialized to `None`). Inside `reload_config()`, after loading the config, resolve the profile file path as `profiles/{profile_name}.yaml` where `profile_name = self._full_config.get("system", {}).get("inverter_profile", "generic")`. Check `os.path.getmtime()` on that path and skip `get_profile_from_config()` when the mtime is unchanged.
- [x] 1.3 Ensure first tick after startup always reads from disk — `_config_mtime` and `_profile_mtime` are initialized to `None`, so the first mtime comparison always triggers a full load.
- [x] 1.4 In `reload_config()`, after reloading config, refresh `self._has_water_heater` and `self._has_ev_charger` from the reloaded config's system section — same pattern as `__init__` (lines 186-190): `system_cfg = self._full_config.get("system", {})` then `.get("has_water_heater", True)` / `.get("has_ev_charger", False)`.
- [x] 1.5 Add test: config reload is skipped when file mtime is unchanged
- [x] 1.6 Add test: config is re-parsed when file mtime changes

## 2. Fix Nordpool Price Fetch

- [x] 2.1 In `executor/engine.py` method `_update_battery_cost()` (~line 1820-1850), replace the `asyncio.run()` / event-loop-detection block with a direct `await get_nordpool_data("config.yaml")` call. Remove the entire `asyncio.get_running_loop()` try/except detection block.
- [x] 2.2 Keep the existing fallback to 0.5 SEK/kWh when the fetch fails or returns empty
- [x] 2.3 Add test: Nordpool price is fetched successfully via await in executor tick
- [x] 2.4 Add test: executor falls back to 0.5 SEK/kWh when Nordpool fetch raises an exception

## 3. Water Heater / EV Sensor Guards

- [x] 3.1 In `backend/recorder.py` (~line 303-312), wrap the `water_heaters[]` sensor loop with `if config.get("system", {}).get("has_water_heater", True):` — note: the local variable is `config` (not `system_config`, which does not exist in this file)
- [x] 3.2 In `backend/recorder.py` (~line 319-329), wrap the `ev_chargers[]` sensor loop with `if config.get("system", {}).get("has_ev_charger", False):` — same pattern as 3.1
- [x] 3.3 In `executor/engine.py` method `_gather_system_state()` (~line 394-405), wrap the `water_heaters[]` sensor loop with `if self._has_water_heater:` — the executor already has this flag as an instance attribute (set in `__init__` line 189)
- [x] 3.4 Add test: recorder skips water heater sensor fetch when `has_water_heater` is false
- [x] 3.5 Add test: recorder skips EV charger sensor fetch when `has_ev_charger` is false

## 4. Clean Default Config

- [x] 4.1 In `config.default.yaml` (~line 97), change `sensor: sensor.vvb_power` to `sensor: ''`
