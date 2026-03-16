## Context

`backend/config_migration.py` was built incrementally over many revisions of the app. Each time the config schema changed, a new migration function was added to the pipeline. Each time a bug was discovered (merge re-introduced deprecated keys, YAML parser produced malformed output, wrong types were written to disk), a "defensive guard" function was added to heal configs on startup.

All beta users are confirmed at `config_version=2`. The app no longer writes the legacy key shapes that the guards were protecting against. The result is ~900 lines of dead code that runs (and does nothing) on every startup, and a file that references the old CHANGELOG_PLAN.md revision system (REV F17, F57, ARC15, IP4, etc.) which was replaced by OpenSpec.

The infrastructure in the file — backup system, template merge, validation, write — is sound and must be preserved exactly.

## Goals / Non-Goals

**Goals:**
- Remove all unreachable one-shot migration functions (9 functions, ~511 lines)
- Remove all "defensive guard" functions that were workarounds for now-fixed bugs (5 functions, ~190 lines)
- Simplify `migrate_config()` to: validate → drop deprecated keys → merge template → write if changed
- Replace all REV/ARC/IP revision code references in comments/docstrings with plain descriptions
- Keep the full test suite green; update tests that tested removed logic

**Non-Goals:**
- No changes to the backup system, `template_aware_merge`, validation, or write logic
- No changes to `migrate_config()`'s public signature or caller behavior
- No changes to `DEPRECATED_KEYS` / `DEPRECATED_NESTED_KEYS` registries (these are still useful)
- No config schema changes

## Decisions

**1. Replace `legacy_steps` pipeline with a single inline deprecated-key sweep**

The entire `legacy_steps` list gets removed. The deprecated-key sweep (`remove_deprecated_keys`) stays but is called inline in `migrate_config()` rather than through a pipeline. This is all that's needed for a config already at version 2.

Rationale: The pipeline abstraction only has value when there are multiple steps. With one remaining step, it's just indirection.

**2. Delete `heal_orphaned_array_keys` and `cleanup_water_heating_duplicates` without replacement**

These were workarounds for a specific bug in the ARC15 migration period where the YAML merge produced malformed output. The merge bug is fixed. The patterns they detect (`name: Main Array` at root level, per-device keys under `water_heating`) cannot appear in any config that hasn't been corrupted by a now-fixed version of the app.

Rationale: Adding a permanent runtime check for a transient bug adds noise and masks future issues.

**3. Delete `fix_s_index_horizon_days_type` without replacement**

This coerced a string `"4"` to int `4`. The bug was that the app wrote it as a string. The write path is fixed. YAML itself will parse unquoted `4` as an int. No user can produce a string-typed value here through normal app use.

Rationale: Type coercion in migration is a symptom of a write bug, not a permanent requirement.

**4. Delete `migrate_ev_charger_legacy_fields` without replacement**

Removed `min_soc_percent` / `target_soc_percent` from `ev_chargers[]`. These fields were removed in REV K25. Any config that ran the app after that change has already had them removed. The app no longer writes them.

Rationale: One-time migration; already run for all users.

**5. Replace all REV/ARC/IP references with plain prose or OpenSpec change names**

The revision system (REV F17, ARC15, etc.) referenced `docs/archive/CHANGELOG_PLAN.md`, which is no longer the documentation system. These references are meaningless to future readers.

Rationale: Documentation should be self-contained and not rely on external revision codes.

**6. Remove `test_migrate_config_heals_corruption` and `test_arc15_migration_*` tests**

These tests exercise code paths that will no longer exist (ARC15 migration, pre-config_version-2 healing). Keeping them as dead tests would be misleading. Replace with a test asserting that a fully-migrated config (config_version=2, no deprecated keys) is **not modified** on startup — the idempotency guarantee.

Rationale: Tests should test existing behavior, not removed behavior.

## Risks / Trade-offs

**[Risk] A user somehow has a config_version=1 config**
- Probability: Near zero — migration ran on every startup since ARC15 shipped
- Impact: Their config would not be migrated to the new array structure; app would likely fail validation
- Mitigation: The `_validate_config_structure` check (kept) will catch badly-structured configs and abort migration rather than corrupting them. A clear error log will appear. User would need to manually update or use `config.default.yaml` as a starting point.

**[Risk] A test that was testing removed logic breaks CI**
- Tests `test_migration_logic`, `test_arc15_migration_*`, `test_arc15_idempotency`, `test_arc15_already_migrated`, `test_migrate_config_heals_corruption` all test removed functions
- Mitigation: Tasks explicitly list each test to delete/replace (see tasks.md)

**[Trade-off] Losing the migration upgrade path for pre-ARC15 configs**
- Acceptance: This is intentional. The beta period is over for those config shapes. The tradeoff (simpler, maintainable code) outweighs the risk.
