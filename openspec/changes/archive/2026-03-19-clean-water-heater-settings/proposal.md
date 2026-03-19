## Why

Water heater settings have a hybrid config layout: the `water_heaters[]` array holds per-device fields, but `target_entity`, `water_power`, and `water_heater_consumption` sit outside the array as global singletons. This is incorrect for multi-heater setups and creates a confusing UI with orphaned "HA Sensors" and "Control" cards below the array card. These per-device fields must move into the array to match the EV charger pattern.

## What Changes

- **Move `executor.water_heater.target_entity`** into each `water_heaters[]` item as `target_entity`
- **Move `input_sensors.water_power`** into each `water_heaters[]` item as `power_sensor`
- **Move `input_sensors.water_heater_consumption`** into each `water_heaters[]` item as `energy_sensor` (field already exists but unused)
- **Remove** the "HA Sensors" and "Control" UI cards from the Water tab — fields now live inside the array accordion
- **Backend aggregation**: executor and recorder aggregate power/energy across all enabled heaters (same pattern as EV chargers)
- **Config migration**: auto-migrate legacy single values into `water_heaters[0]` on startup
- **Out of scope**: Temperature setpoints (`temp_off/normal/boost/max`) stay global for now — deferred to a separate backlog item

## Capabilities

### New Capabilities

_None_

### Modified Capabilities

- `water-heater-execution`: Executor reads `target_entity` from `water_heaters[id]` instead of `executor.water_heater.target_entity`. Supports dispatching to multiple heater entities.
- `sensor-configuration`: `input_sensors.water_power` and `input_sensors.water_heater_consumption` are removed from global input_sensors; now per-heater fields in `water_heaters[]`.

## Impact

- **Config schema**: `water_heaters[]` items gain `target_entity`, `power_sensor` fields; `energy_sensor` becomes actively used
- **Config migration**: new migration function to move legacy keys into array items
- **Frontend**: `WaterTab.tsx` waterSections in `types.ts` — remove HA Sensors + Control sections, add fields to EntityArrayEditor
- **Backend**: `executor/engine.py`, `executor/config.py`, `backend/recorder.py`, `backend/ha_socket.py`, `backend/health.py`, `backend/core/ha_client.py` — read sensors from array, aggregate for metrics
- **No breaking API changes**: powerflow and daily values stay aggregated
