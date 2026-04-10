## 1. Delete Legacy Migration Functions

Remove the 9 one-shot migration functions that target pre-ARC15 config shapes (config_version < 2). All of these functions are dead code for any current user config.

- [x] 1.1 Delete function `migrate_version_key()` (lines ~225-253) from `backend/config_migration.py`
- [x] 1.2 Delete function `migrate_battery_config()` (lines ~256-299) from `backend/config_migration.py`
- [x] 1.3 Delete function `cleanup_obsolete_keys()` (lines ~302-349) from `backend/config_migration.py`
- [x] 1.4 Delete function `migrate_soc_target_entity()` (lines ~352-384) from `backend/config_migration.py`
- [x] 1.5 Delete function `migrate_solar_arrays()` (lines ~387-451) from `backend/config_migration.py`
- [x] 1.6 Delete function `migrate_inverter_profile_keys()` (lines ~454-494) from `backend/config_migration.py`
- [x] 1.7 Delete function `migrate_root_inverter_profile()` (lines ~497-524) from `backend/config_migration.py`
- [x] 1.8 Delete function `migrate_arc15_entity_config()` (lines ~527-692) from `backend/config_migration.py`
- [x] 1.9 Delete function `migrate_inverter_custom_entities()` (lines ~1046-1097) from `backend/config_migration.py`

## 2. Delete Defensive Guard Functions

Remove the 5 guard functions that were workarounds for now-fixed bugs. These check for key patterns that cannot appear in any config produced by the current app.

- [x] 2.1 Delete function `heal_orphaned_array_keys()` (lines ~162-222) from `backend/config_migration.py`
- [x] 2.2 Delete function `cleanup_water_heating_duplicates()` (lines ~695-729) from `backend/config_migration.py`
- [x] 2.3 Delete function `fix_s_index_horizon_days_type()` (lines ~732-759) from `backend/config_migration.py`
- [x] 2.4 Delete function `migrate_ev_charger_legacy_fields()` (lines ~1100-1130) from `backend/config_migration.py`

## 3. Simplify migrate_config()

Replace the `legacy_steps` pipeline with a direct call to `remove_deprecated_keys()`. Remove all inline comments referencing old revision codes.

- [x] 3.1 In `migrate_config()` (lines ~1133-1295), delete the entire `legacy_steps` list and the `for step in legacy_steps:` loop
- [x] 3.2 Replace that block with a single direct call: `user_config, pre_merge_changes = remove_deprecated_keys(user_config)` (keep same `pre_merge_changes` variable logic)
- [x] 3.3 Remove the second call to `heal_orphaned_array_keys(final_config)` in the post-merge block (lines ~1273-1276) — this function is being deleted
- [x] 3.4 Remove the stale `if "version" in user_config: pass` block (lines ~1257-1260) — it was a no-op
- [x] 3.5 Remove the inline thinking-out-loud comments in the template merge section (lines ~1242-1253) that start with "We clone default_config...", "Actually, we can just...", "But 'user_config' object structure..." — replace with a single clear comment: `# Merge user values into the template structure`

## 4. Clean Up Documentation

Remove all references to the old CHANGELOG_PLAN.md revision system (REV Fxx, ARCxx, IPx) throughout the file. Replace with plain prose.

- [x] 4.1 Update `DEPRECATED_KEYS` registry comment block (lines ~73-116): remove all `# REV F57:`, `# ARC15:`, `# IP4:`, `# REV F19:` prefix annotations — keep the plain description of what the key was and what replaced it
- [x] 4.2 Update `remove_deprecated_keys()` docstring: remove "REV F57:" prefix from description
- [x] 4.3 Update `migrate_config()` docstring and all inline comments: remove all remaining REV/ARC/IP revision code references, replace with plain language descriptions
- [x] 4.4 Update `_write_config()` and `create_timestamped_backup()` docstrings: remove "REV F57:", "REV F66:" prefixes
- [x] 4.5 Update `validate_config_for_write()` and `_validate_config_structure()` docstrings: remove "REV F57:", "REV F62:" references
- [x] 4.6 Update `template_aware_merge()` docstring: remove "REV F66:" references
- [x] 4.7 Add a module-level docstring at the top of `backend/config_migration.py` explaining what the file does now (startup validation, deprecated-key sweep, template merge, atomic write with backup) — do NOT reference old revision codes

## 5. Update Tests

Remove tests for deleted functions. Add a new test asserting idempotency for clean configs.

- [x] 5.1 Delete `test_migration_logic()` from `tests/config/test_config_migration.py` — it tests `migrate_battery_config` and `migrate_version_key` which are deleted
- [x] 5.2 Delete `test_arc15_migration_water_heater()` from `tests/config/test_config_migration.py` — tests deleted `migrate_arc15_entity_config`
- [x] 5.3 Delete `test_arc15_migration_ev_charger()` from `tests/config/test_config_migration.py` — tests deleted `migrate_arc15_entity_config`
- [x] 5.4 Delete `test_arc15_migration_both_devices()` from `tests/config/test_config_migration.py` — tests deleted `migrate_arc15_entity_config`
- [x] 5.5 Delete `test_arc15_idempotency()` from `tests/config/test_config_migration.py` — tests deleted `migrate_arc15_entity_config`
- [x] 5.6 Delete `test_arc15_already_migrated()` from `tests/config/test_config_migration.py` — tests deleted `migrate_arc15_entity_config`
- [x] 5.7 Delete `TestFullMigrationFlow.test_migrate_config_heals_corruption()` from `tests/config/test_config_migration.py` — it constructs a pre-ARC15 config with `version` key and `deferrable_loads`, which the simplified pipeline no longer processes
- [x] 5.8 Add new test `test_migrate_config_idempotent_for_clean_config()` in `tests/config/test_config_migration.py`: construct a valid config_version=2 config with no deprecated keys, call `migrate_config()`, assert the file was NOT written (mock `_write_config` and assert it was never called, or check file mtime did not change)
- [x] 5.9 Verify `TestDeprecatedKeyRemoval`, `TestBackupSystem`, `TestTemplateAwareMerge`, and `TestBackendSave` still pass as-is — these test infrastructure that is NOT being changed

## 6. Verify

- [x] 6.1 Run `python -m pytest tests/config/ -v` — all tests must pass
- [x] 6.2 Run `python -m pytest -x -q` — full suite must pass with no regressions
- [x] 6.3 Run `./scripts/lint.sh` — no lint errors
- [x] 6.4 Verify line count of `backend/config_migration.py` is below 700 lines (was ~1468)
