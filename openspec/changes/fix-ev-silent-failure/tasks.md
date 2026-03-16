## 1. Frontend: Fix ChartCard Overlay Index Mismatch

- [x] 1.1 In `frontend/src/components/ChartCard.tsx`, find the overlay visibility control block (currently around lines 1088–1095). It contains three lines like `if (ds[15]) ds[15].hidden = ...`. Read the file to locate the exact lines.
- [x] 1.2 Replace the three existing (wrong) visibility lines and add the missing fourth line so the block reads exactly:
  ```typescript
  if (ds[15]) ds[15].hidden = !overlays.showActual || !overlays.ev
  if (ds[16]) ds[16].hidden = !overlays.showActual || !overlays.export
  if (ds[17]) ds[17].hidden = !overlays.showActual || !overlays.water
  ```
  Note: `ds[15]` = Actual EV, `ds[16]` = Actual Export, `ds[17]` = Actual Water. These indices are determined by the fixed dataset creation order in the same file (search for the block that creates all 18 datasets).
- [x] 1.3 Verify there are no other references to `ds[15]`, `ds[16]`, or `ds[17]` in the visibility logic that would conflict with this fix.

## 2. Config: Add energy_sensor to Default Template

- [x] 2.1 In `config.default.yaml`, find the `water_heaters:` section. In the default `- id: main_tank` entry, add `energy_sensor: ''` on the line immediately after `sensor: sensor.vvb_power`. Add a comment: `# Cumulative energy counter (recommended for accurate load isolation)`.
- [x] 2.2 In `config.default.yaml`, find the `ev_chargers:` section. In the default `- id: ev_charger_1` entry, add `energy_sensor: ''` on the line immediately after `sensor: sensor.tesla_power`. Add a comment: `# Cumulative energy counter (recommended for accurate load isolation)`.

## 3. Backend Recorder: Cumulative Energy Isolation for EV and Water

- [x] 3.1 In `backend/recorder.py`, read and understand the inner function `get_cumulative_kwh(key: str)` (around line 233). It fetches an entity from `input_sensors[key]`, normalizes to kWh, and returns `(kwh_value, sensor_timestamp)`. Create a new inner function immediately after it named `get_cumulative_kwh_for_entity(entity_id: str) -> tuple[float | None, datetime | None]` that does the same thing but accepts an entity ID directly (no `input_sensors` lookup). It can share the same body — just replace `entity = input_sensors.get(key)` with `entity = entity_id`.
- [x] 3.2 In `backend/recorder.py`, after the line that builds `ev_charger_sensors` and before `gather_sensor_reads` (around line 308), build a second list `ev_charger_energy_sensors: list[tuple[str, str]]` — a list of `(charger_id, energy_sensor_entity)` tuples for enabled EV chargers that have a non-empty `energy_sensor` field. Example:
  ```python
  ev_charger_energy_sensors: list[tuple[str, str]] = []
  for ev_charger in ev_chargers:
      if ev_charger.get("enabled", True):
          es = ev_charger.get("energy_sensor", "")
          if es:
              ev_charger_energy_sensors.append((str(ev_charger["id"]), str(es)))
  ```
- [x] 3.3 In `backend/recorder.py`, build a similar list `water_heater_energy_sensors: list[tuple[str, str]]` — a list of `(heater_id, energy_sensor_entity)` tuples for enabled water heaters with a non-empty `energy_sensor` field. Add this immediately after step 3.2's block, looping over `config.get("water_heaters", [])`.
- [x] 3.4 In `backend/recorder.py`, find the block starting with the comment `# Water and EV still use power snapshots` (around line 433). Replace the two snapshot lines and the isolation block (lines 433–448) with the following logic:
  - For EV: loop over `ev_charger_energy_sensors`. For each `(charger_id, entity_id)`, call `get_cumulative_kwh_for_entity(entity_id)` to get `(cumulative, sensor_ts)`. If not None, call `state_store.get_delta(f"ev_energy_{charger_id}", cumulative, now, sensor_timestamp=sensor_ts)`. If delta is valid, add it to `ev_charging_kwh`. If cumulative is None or delta is invalid, fall back to the proportional share of `ev_charging_kw * 0.25` for that charger. If `ev_charger_energy_sensors` is empty, use `ev_charging_kw * 0.25` directly.
  - For water: same pattern — loop over `water_heater_energy_sensors`, use `state_store.get_delta(f"water_energy_{heater_id}", ...)`, fall back to `water_kw * 0.25` per heater if no energy sensor or invalid delta.
  - The `used_cumulative_load` subtraction block that follows (lines 440–448) remains unchanged: it subtracts `ev_charging_kwh + water_kwh` from `load_kwh` and clamps to zero.
- [x] 3.5 In `backend/recorder.py`, find the `logger.info("Recording observation for ...")` line (around line 516). Add `EV={ev_charging_kwh:.3f}kWh` to the log string, between Water and Bat. Result should be:
  ```python
  logger.info(
      f"Recording observation for {slot_start}: SOC={soc_percent}% "
      f"PV={pv_kwh:.3f}kWh Load={load_kwh:.3f}kWh Water={water_kwh:.3f}kWh "
      f"EV={ev_charging_kwh:.3f}kWh Bat={battery_kw:.3f}kW"
  )
  ```

## 4. Backend Health Check: Warning for Missing Energy Sensors

- [x] 4.1 In `backend/health.py`, read the `_validate_config_structure` method (around line 279) to understand the pattern for adding a `HealthIssue` with `severity="warning"`. Note the `HealthIssue` dataclass fields: `category`, `severity`, `message`, `guidance`, and optionally `entity_id`.
- [x] 4.2 In `backend/health.py`, at the end of the `_validate_config_structure` method (before the final `return issues`), add a loop over enabled EV chargers. For each enabled charger where `energy_sensor` is absent or empty, append a `HealthIssue`:
  - `category="config"`, `severity="warning"`
  - `message=f"EV charger '{charger.get('name', charger.get('id'))}' has no energy sensor configured. Load isolation accuracy is reduced."`
  - `guidance="Configure 'energy_sensor' for this charger in Settings > EV to enable accurate EV energy isolation from house load."`
- [x] 4.3 In `backend/health.py`, immediately after the EV charger loop (step 4.2), add an identical loop over enabled water heaters. For each enabled heater where `energy_sensor` is absent or empty, append a `HealthIssue`:
  - `category="config"`, `severity="warning"`
  - `message=f"Water heater '{heater.get('name', heater.get('id'))}' has no energy sensor configured. Load isolation accuracy is reduced."`
  - `guidance="Configure 'energy_sensor' for this heater in Settings > Water to enable accurate water heating energy isolation from house load."`

## 5. Frontend Settings UI: Energy Sensor Fields and Tooltip Updates

- [x] 5.1 In `frontend/src/pages/settings/components/EntityArrayEditor.tsx`, find the `WaterHeaterEntity` interface (around line 16). Add `energy_sensor: string` as a field after `sensor: string`.
- [x] 5.2 In `frontend/src/pages/settings/components/EntityArrayEditor.tsx`, find the `EVChargerEntity` interface (around line 30). Add `energy_sensor: string` as a field after `sensor: string`.
- [x] 5.3 In `frontend/src/pages/settings/components/EntityArrayEditor.tsx`, find the `DEFAULT_WATER_HEATER` object (around line 55). Add `energy_sensor: ''` immediately after `sensor: ''`.
- [x] 5.4 In `frontend/src/pages/settings/components/EntityArrayEditor.tsx`, find the `DEFAULT_EV_CHARGER` object (around line 68). Add `energy_sensor: ''` immediately after `sensor: ''`.
- [x] 5.5 In `frontend/src/pages/settings/components/EntityArrayEditor.tsx`, find the JSX block that renders the `sensor` field (Power sensor) for both device types (around line 343 — `value={entity.sensor}` / `onChange={(val) => updateEntity(index, { sensor: val })}`). This is the "Power sensor" field. Update its label/placeholder text to say "Power sensor" and add (or update) a tooltip/helper text reading: `"Real-time power reading for this device. Used for live monitoring and dashboard display."`.
- [x] 5.6 In `frontend/src/pages/settings/components/EntityArrayEditor.tsx`, immediately after the existing `sensor` (Power sensor) field block, add a new entity dropdown field for `energy_sensor`. Label: `"Energy sensor"`. Placeholder: `"Select Home Assistant energy sensor..."`. Tooltip/helper: `"Cumulative energy counter for this device. Used for accurate load isolation — how much energy the device consumed each slot. Recommended for clean training data."`. The field should call `updateEntity(index, { energy_sensor: val })` on change. Use exactly the same component/pattern as the existing `sensor` field above it.
- [x] 5.7 Verify the `evFieldList` and `waterFieldList` in `frontend/src/pages/settings/types.ts` do NOT need updating — these are for top-level flat fields only, not `entity_array` sub-fields. The `entity_array` fields are managed by `EntityArrayEditor.tsx` directly.

## 6. Documentation

- [x] 6.1 In `docs/ARCHITECTURE.md`, find section **12.2 The Data Pipeline**, step 3 (Storage). Update the description to mention that `ev_charging_kwh` and `water_kwh` are now computed from cumulative energy sensor deltas when `energy_sensor` is configured on the device, rather than power snapshots. Add a note that snapshot fallback is used when no energy sensor is configured.
- [x] 6.2 In `docs/ARCHITECTURE.md`, find section **12.5 Future Extensibility**. In the step-by-step list "To add a new load type", update step 1 to note that new load type config entries in `config.default.yaml` should include an `energy_sensor: ''` field alongside the `sensor` (power) field.
- [x] 6.3 In `docs/ARCHITECTURE.md`, find section **5.5 Database-First Energy Architecture**. The diagram already shows `SUM(ev_charging_kwh)`. Update the prose below the diagram to note that `ev_charging_kwh` accuracy depends on `energy_sensor` being configured; without it, the snapshot fallback is used (less accurate during partial slots).

## 7. Tests: Energy Sensor Cumulative Delta and Health Check

All tests go in `tests/backend/test_recorder_deltas.py` (recorder tests) and `tests/backend/test_health.py` (health tests). Follow the exact patterns of the existing tests in those files.

### 7.1 Recorder: EV cumulative delta with energy_sensor configured

- [x] 7.1.1 Add a test `test_ev_energy_sensor_cumulative_delta` to the `TestLoadIsolation` class in `tests/backend/test_recorder_deltas.py`. This test verifies that when an EV charger has `energy_sensor` configured, the recorder uses cumulative delta (not power snapshot) to compute `ev_charging_kwh`.
  - Config: `config["ev_chargers"] = [{"id": "ev1", "sensor": "sensor.ev_power", "energy_sensor": "sensor.ev_energy", "enabled": True}]`
  - State store seed: include `"ev_energy_ev1": {"value": 120.5, "timestamp": prev_time.isoformat()}` alongside the usual `pv_total` and `load_total` entries.
  - Mock `get_ha_entity_state` to return `sensor.ev_energy` with `{"state": "121.5", "attributes": {"unit_of_measurement": "kWh"}, "last_updated": now.isoformat()}`. Also return the usual `total_pv_production` (e.g. 101.25) and `total_load_consumption` (e.g. 53.0) cumulative sensors.
  - Mock `get_ha_sensor_kw_normalized` to return `4.0` for `sensor.ev_power` (this should NOT be used since energy_sensor is configured, but must be present since the recorder reads it).
  - Assert: `record["ev_charging_kwh"] == pytest.approx(1.0, abs=0.01)` (delta: 121.5 − 120.5 = 1.0 kWh)
  - Assert: `record["load_kwh"] == pytest.approx(2.0, abs=0.01)` (total 3.0 − EV 1.0 = 2.0)
  - Follow the exact same test structure as `test_ev_charging_subtracted_from_total_load` (line 927) — same mocks, same patching, same assertion style. The only differences are: (a) config includes `energy_sensor`, (b) state store includes `ev_energy_ev1`, (c) mock returns the energy sensor entity state.

### 7.2 Recorder: Water heater cumulative delta with energy_sensor configured

- [x] 7.2.1 Add a test `test_water_energy_sensor_cumulative_delta` to the `TestLoadIsolation` class. Same pattern as 7.1.1 but for water heater.
  - Config: `config["water_heaters"] = [{"id": "wh1", "sensor": "sensor.water_power", "energy_sensor": "sensor.water_energy", "enabled": True}]`
  - State store seed: include `"water_energy_wh1": {"value": 50.0, "timestamp": prev_time.isoformat()}`.
  - Mock `get_ha_entity_state` to return `sensor.water_energy` with `{"state": "50.75", "attributes": {"unit_of_measurement": "kWh"}, "last_updated": now.isoformat()}`.
  - Mock `get_ha_sensor_kw_normalized` to return `3.0` for `sensor.water_power`.
  - Assert: `record["water_kwh"] == pytest.approx(0.75, abs=0.01)` (delta: 50.75 − 50.0)
  - Assert: `record["load_kwh"] == pytest.approx(1.25, abs=0.01)` (total 2.0 − water 0.75)

### 7.3 Recorder: Fallback to power snapshot when energy_sensor cumulative unavailable

- [x] 7.3.1 Add a test `test_energy_sensor_fallback_to_snapshot_when_no_prior_state` to the `TestLoadIsolation` class. This verifies that when `energy_sensor` is configured but there is no prior state (first run), the recorder falls back to `power_kw × 0.25`.
  - Config: `config["ev_chargers"] = [{"id": "ev1", "sensor": "sensor.ev_power", "energy_sensor": "sensor.ev_energy", "enabled": True}]`
  - State store seed: only the usual `pv_total` and `load_total` — do NOT include `ev_energy_ev1` (simulates first run, no prior reading).
  - Mock `get_ha_entity_state` to return `sensor.ev_energy` with `{"state": "121.5", "attributes": {"unit_of_measurement": "kWh"}, "last_updated": now.isoformat()}`.
  - Mock `get_ha_sensor_kw_normalized` to return `4.0` for `sensor.ev_power`.
  - Assert: `record["ev_charging_kwh"] == pytest.approx(1.0, abs=0.01)` — the fallback uses `4.0 kW × 0.25h = 1.0 kWh`.
  - Note: On first run, `state_store.get_delta` returns `None` because there is no prior value. The recorder code should then fall back to the power snapshot path.

### 7.4 Health check: Warning for enabled device with missing energy_sensor

- [x] 7.4.1 Add a test `test_health_warns_missing_energy_sensor_ev` in `tests/backend/test_health.py`. This test verifies the health check emits a WARNING when an enabled EV charger has no `energy_sensor`.
  - Instantiate `HealthChecker` using `HealthChecker.__new__(HealthChecker)` and set `checker._config` and `checker._secrets` (follow the pattern from `test_check_entities_uses_concurrent_gather` at line 56).
  - Set `checker._config["ev_chargers"] = [{"id": "ev1", "name": "My EV", "sensor": "sensor.ev_power", "energy_sensor": "", "enabled": True}]`
  - Call `issues = checker._validate_config_structure()` (this is a sync method, not async).
  - Assert: at least one issue has `severity == "warning"` and `"My EV"` in `issue.message` and `"energy sensor"` in `issue.message.lower()`.

- [x] 7.4.2 Add a test `test_health_no_warning_energy_sensor_configured` in `tests/backend/test_health.py`. Verifies no energy-sensor warning when `energy_sensor` is configured.
  - Same setup, but `checker._config["ev_chargers"] = [{"id": "ev1", "name": "My EV", "sensor": "sensor.ev_power", "energy_sensor": "sensor.ev_energy", "enabled": True}]`
  - Call `issues = checker._validate_config_structure()`.
  - Assert: no issue contains `"energy sensor"` in its message (filter the issues list).

- [x] 7.4.3 Add a test `test_health_no_warning_disabled_device_missing_energy_sensor` in `tests/backend/test_health.py`. Verifies disabled devices don't trigger a warning.
  - Same setup, but `checker._config["ev_chargers"] = [{"id": "ev1", "name": "My EV", "sensor": "sensor.ev_power", "energy_sensor": "", "enabled": False}]`
  - Call `issues = checker._validate_config_structure()`.
  - Assert: no issue contains `"energy sensor"` in its message.
