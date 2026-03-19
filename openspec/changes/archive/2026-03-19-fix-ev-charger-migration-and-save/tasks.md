## 1. Fix Migration Order

- [x] 1.1 In `backend/config_migration.py` `migrate_config()`, move the `_migrate_ev_charger_fields()` call to run before `remove_deprecated_keys()`

## 2. Fix Save Validation Type Safety

- [x] 2.1 In `backend/api/routers/config.py` `_validate_config_for_save()`, coerce `departure_time` to string: `dev_departure = str(ev.get("departure_time", "") or "")`

## 3. Fix YAML Source

- [x] 3.1 In `config.yaml`, quote all bare time values under `ev_charger_1` and `ev_charger_2` (e.g., `departure_time: 18:00` → `departure_time: "18:00"`)
