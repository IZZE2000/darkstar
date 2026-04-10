## Why

`backend/config_migration.py` has grown to ~1468 lines of accumulated migration archaeology — 9 one-shot legacy migration functions (targeting config formats that predate the beta program) plus 5 "defensive guard" functions that were band-aids for specific bugs that have since been fixed. All beta users are on `config_version=2`, meaning ~900 lines of this file are unreachable dead code. It also contains inline prose from the old CHANGELOG_PLAN.md revision system (REV F17, REV F57, ARC15, etc.) which is the wrong documentation system — we use OpenSpec now.

## What Changes

- **Remove**: All 9 one-shot legacy migration functions (targeting pre-ARC15 config shapes that no longer exist): `migrate_version_key`, `migrate_battery_config`, `cleanup_obsolete_keys`, `migrate_soc_target_entity`, `migrate_solar_arrays`, `migrate_inverter_profile_keys`, `migrate_root_inverter_profile`, `migrate_inverter_custom_entities`, `migrate_arc15_entity_config`
- **Remove**: All 5 "defensive guard" functions that were workarounds for specific bugs now fixed: `heal_orphaned_array_keys`, `cleanup_water_heating_duplicates`, `fix_s_index_horizon_days_type`, `migrate_ev_charger_legacy_fields`, and the legacy-pass usage of `remove_deprecated_keys`
- **Simplify**: Replace the legacy_steps pipeline with a single inline deprecated-key sweep using the existing `DEPRECATED_KEYS` / `DEPRECATED_NESTED_KEYS` registries
- **Update docs**: Remove all REV/ARC/IP revision code references; replace with plain descriptions and OpenSpec change references where appropriate
- **Keep intact**: All infrastructure — `template_aware_merge`, `_validate_config_structure`, `validate_config_for_write`, backup system, `_write_config`, `_verify_written_config`, `_extract_critical_values`, `_validate_critical_values_preserved`

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- None (this is a pure internal refactor — no behavior changes for any current user)

## Impact

- **backend/config_migration.py**: ~900 lines removed, file shrinks from ~1468 to ~500-600 lines
- **No behavioral change**: all beta users are already at config_version=2; the removed code paths are unreachable
- **Tests**: existing config migration tests must all continue to pass; add a test asserting configs already at config_version=2 are not modified by the stripped pipeline
