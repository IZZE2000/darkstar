## Context

The `water_heaters[]` array was introduced to support multiple water heaters, but several per-device fields were left behind as global singletons:

- `executor.water_heater.target_entity` — the thermostat entity to control
- `input_sensors.water_power` — live power reading for metrics
- `input_sensors.water_heater_consumption` — daily energy for quota tracking

The array items already have `sensor` (power reading) and `energy_sensor` (exists in config, recently added). The global `input_sensors.water_power` reads the same physical sensor as `water_heaters[].sensor` — there's no reason to have both.

The UI renders orphaned "HA Sensors" and "Control" cards outside the array accordion, which is wrong — these are per-device settings.

## Goals / Non-Goals

**Goals:**
- Every per-device water heater setting lives inside `water_heaters[]`
- Backend aggregates power/energy across heaters for metrics (same as EV pattern)
- Seamless config migration from legacy single values
- Clean UI: remove orphaned cards, all per-device fields in accordion

**Non-Goals:**
- Moving temperature setpoints (`temp_off/normal/boost/max`) into the array — deferred to backlog
- Multi-heater executor dispatch (setting different temps per heater) — deferred, blocked on temperatures moving into array
- Changing the EV charger settings to match (same pattern but separate change)

## Decisions

### 1. One power sensor field: `sensor`

The `sensor` field already exists in each `water_heaters[]` item and is used by the load disaggregator. The recorder, executor, and ha_socket currently read the same kind of value from `input_sensors.water_power`. After this change, all subsystems read from `water_heaters[].sensor`. No new `power_sensor` field — one sensor, one field, no confusion.

`energy_sensor` also already exists in each array item (added in the recent EV work). It just needs to be wired up in `ha_client.py`.

The only truly new field is `target_entity` — the thermostat control entity:

```yaml
water_heaters:
  - id: main_tank
    sensor: sensor.vvb_power       # EXISTING: power sensor (now used by ALL subsystems)
    energy_sensor: ''              # EXISTING: daily energy counter (now actively wired)
    target_entity: ''              # NEW: thermostat entity for this heater
    # ... other existing fields ...
```

### 2. Backend aggregation pattern

The recorder, executor, and ha_socket currently read `input_sensors.water_power` for a single value. After migration, they read `sensor` from `water_heaters[]` and aggregate (sum across enabled heaters):

- `recorder.py`: read `sensor` from enabled heaters, aggregate for `water_kw` metric
- `ha_socket.py`: map enabled heaters' `sensor` entities to `water_kw` websocket feed
- `ha_client.py`: read `energy_sensor` from enabled heaters, aggregate for daily consumption
- `engine.py`: read `sensor` from enabled heaters for executor metrics

This mirrors how EV charger metrics work: individual device sensors, aggregated display.

### 3. Executor reads `target_entity` from array

`executor/config.py` `WaterHeaterConfig` keeps `target_entity` but loads it from the first enabled `water_heaters[]` item that has a non-empty `target_entity`, instead of from `executor.water_heater.target_entity`. Temperature setpoints remain global for now. Multi-heater dispatch comes when temperatures move into the array.

### 4. Config migration strategy

Add a pre-merge migration step in `config_migration.py`:

1. If `input_sensors.water_power` has a value and `water_heaters[0].sensor` is empty → copy value into `sensor`
2. If `input_sensors.water_heater_consumption` has a value and `water_heaters[0].energy_sensor` is empty → copy value into `energy_sensor`
3. If `executor.water_heater.target_entity` has a value and `water_heaters[0]` lacks `target_entity` → copy value into array item
4. Remove the old keys from `input_sensors` and `executor.water_heater.target_entity`
5. Template merge handles any remaining cleanup (old keys won't exist in new default config)

Note: `input_sensors.water_power` migrates into `sensor` only if the existing `sensor` field is empty. If the user already has `sensor` configured (likely — it was required), the `input_sensors` value is simply discarded since they're the same entity.

### 5. Frontend changes

- Remove "HA Sensors" section from `waterSections` in `types.ts`
- Remove "Control" section from `waterSections` in `types.ts`
- Add `target_entity` field to `EntityArrayEditor` for water heater type
- `sensor` and `energy_sensor` are already shown in the accordion — verify they're present

### 6. Health check updates

`backend/health.py` currently checks `input_sensors.water_power` and `input_sensors.water_heater_consumption` as required sensor keys. Update to check `water_heaters[].sensor` and `water_heaters[].energy_sensor` per enabled heater instead.

## Risks / Trade-offs

- **Risk: Users with custom `input_sensors.water_power` lose config on upgrade** → Mitigation: migration copies value into array `sensor` field (if empty) before template merge removes old key. Backup is created automatically. In practice, `sensor` is almost certainly already set to the same value.
- **Trade-off: Single target_entity in executor for now** → Acceptable because temperature setpoints are still global. Multi-dispatch is cleanly addable when temperatures move into array.
