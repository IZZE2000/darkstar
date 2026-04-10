## Why

Two bugs introduced in the `feat(multi-device-ev-chargers)` commit broke config migration and saving for EV charger settings: user switch entity values are silently lost during migration, and any config.yaml with unquoted time values (parsed as integers by PyYAML) causes a 500 error on every save attempt.

## What Changes

- Fix migration order: move `_migrate_ev_charger_fields()` to run **before** `remove_deprecated_keys()` in `migrate_config()`, so old `executor.ev_charger.switch_entity` is copied to `ev_chargers[0].switch_entity` before it gets deleted
- Fix save validation: coerce `departure_time` to string before regex matching in `_validate_config_for_save()` to handle integer values that result from YAML 1.1 sexagesimal parsing
- Fix config.yaml: quote bare time values (`18:00` → `"18:00"`) to prevent PyYAML from parsing them as integers

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `config-migration`: migration order requirement — field migration must run before deprecated key removal to preserve data

## Impact

- `backend/config_migration.py`: reorder step 2 (`remove_deprecated_keys`) and step 7 (`_migrate_ev_charger_fields`) in `migrate_config()`
- `backend/api/routers/config.py`: type-coerce `departure_time` in `_validate_config_for_save()`
- `config.yaml`: quote unquoted time values under `ev_charger_1` and `ev_charger_2`
