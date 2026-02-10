# Spec: Migration Script Requirements

## Requirements

### REQ-MIGRATE-01: Old Format Detection
The migration script MUST detect old format by checking for:
- Presence of `deferrable_loads` key, OR
- Absence of both `water_heaters` and `ev_chargers` keys, OR
- `config_version < 2`

### REQ-MIGRATE-02: Water Heater Migration
When `system.has_water_heater: true` OR `deferrable_loads` contains water heater:
1. Extract sensor from `input_sensors.water_power`
2. Extract power rating from matching deferrable_load entry
3. Create single entry in `water_heaters[]` array
4. Set defaults for missing optional fields

### REQ-MIGRATE-03: EV Charger Migration
When `system.has_ev_charger: true` OR `deferrable_loads` contains EV charger:
1. Extract sensor from `input_sensors.ev_power`
2. Extract power/capacity from matching deferrable_load entry
3. Create single entry in `ev_chargers[]` array
4. Set defaults for missing optional fields

### REQ-MIGRATE-04: Deferrable Loads Mapping
Map existing `deferrable_loads[]` entries to new arrays:
- `id == "water_heater"` → `water_heaters[]`
- `id == "ev_charger"` or `type == "ev"` → `ev_chargers[]`
- Copy all relevant fields: sensor_key, power_kw, type, nominal_power_kw

### REQ-MIGRATE-05: Idempotency
Running migration multiple times MUST produce identical result (no duplicate entries).

### REQ-MIGRATE-06: Backup Creation
Migration MUST create backup of config file before modification: `config.yaml.backup.YYYYMMDD_HHMMSS`

### REQ-MIGRATE-07: Validation
After migration, validate that:
- All required fields are present
- No duplicate IDs in arrays
- Sensors are valid entity_id format
- Numeric values are positive

### REQ-MIGRATE-08: Error Handling
On migration failure:
- Log detailed error with context
- Restore from backup if available
- Raise MigrationError with clear message
- Do not save partial/corrupted config

### REQ-MIGRATE-09: Logging
Migration MUST log:
- Detection of old format
- Steps being performed
- Fields being migrated
- Any defaults being applied
- Success/failure status

### REQ-MIGRATE-10: Config Version Update
After successful migration, set `config_version: 2` to prevent re-migration.
