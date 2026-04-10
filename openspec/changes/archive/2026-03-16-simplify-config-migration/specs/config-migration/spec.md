## ADDED Requirements

### Requirement: Fully-migrated configs are not modified on startup
A config already at `config_version=2` with no deprecated keys SHALL pass through `migrate_config()` without any file write occurring.

#### Scenario: Idempotent startup for clean config
- **WHEN** `migrate_config()` is called with a config at `config_version=2` and no deprecated keys present
- **THEN** the config file SHALL NOT be written to disk
- **AND** the function SHALL complete without error

#### Scenario: Deprecated keys are still removed at startup
- **WHEN** `migrate_config()` is called with a config at `config_version=2` that contains a deprecated root-level key (e.g., `deferrable_loads`, `ev_charger`, `solar_array`, `version`, `schedule_future_only`)
- **THEN** the deprecated key SHALL be removed from the written config
- **AND** all other user values SHALL be preserved

#### Scenario: Deprecated nested keys are still removed at startup
- **WHEN** `migrate_config()` is called and the config contains deprecated keys under `executor.inverter` (e.g., `work_mode_entity`, `soc_target_entity`) or deprecated flat keys under `water_heating`
- **THEN** those deprecated nested keys SHALL be removed
- **AND** all sibling keys that are not deprecated SHALL be preserved

### Requirement: Critical user values are preserved through template merge
The template merge step SHALL never overwrite user-configured values with template defaults.

#### Scenario: User values survive merge with updated template
- **WHEN** `migrate_config()` runs the template merge and the default template has a key with a different value than the user config
- **THEN** the user's value SHALL be kept in the final config
- **AND** new keys present in the template but absent in the user config SHALL be added with their default values

#### Scenario: Backup is created before any write
- **WHEN** `migrate_config()` determines a write is needed
- **THEN** a timestamped backup of the current config SHALL be created before writing
- **AND** the backup SHALL be stored in the persistent backup directory

### Requirement: Corrupt or missing config is handled safely
`migrate_config()` SHALL abort without writing if the config fails structure validation, preventing data loss.

#### Scenario: Structurally invalid config aborts migration
- **WHEN** `migrate_config()` loads a config that fails `_validate_config_structure()`
- **THEN** migration SHALL be aborted
- **AND** the config file SHALL NOT be modified
- **AND** an error SHALL be logged

#### Scenario: Missing config file is a no-op
- **WHEN** `migrate_config()` is called and the config file does not exist
- **THEN** the function SHALL return without error
- **AND** no file SHALL be created

## REMOVED Requirements

### Requirement: One-shot legacy migration from pre-ARC15 config shapes
**Reason**: All beta users are confirmed at `config_version=2`. The migration functions targeting pre-ARC15 config shapes (`migrate_battery_config`, `cleanup_obsolete_keys`, `migrate_solar_arrays`, `migrate_soc_target_entity`, `migrate_inverter_profile_keys`, `migrate_root_inverter_profile`, `migrate_inverter_custom_entities`, `migrate_arc15_entity_config`, `migrate_version_key`) are dead code — they check for key patterns that cannot exist in any current user config.
**Migration**: Not applicable. Users on pre-ARC15 configs (config_version=1) are not supported. They should use `config.default.yaml` as a starting point.

### Requirement: Runtime healing of orphaned YAML keys
**Reason**: `heal_orphaned_array_keys` and `cleanup_water_healing_duplicates` were workarounds for a specific YAML merge bug during the ARC15 migration window. The underlying merge bug is fixed; these patterns cannot appear in configs produced by the current app.
**Migration**: Not applicable. These patterns no longer occur.

### Requirement: Runtime type coercion for s_index_horizon_days
**Reason**: `fix_s_index_horizon_days_type` fixed a bug where the app wrote this value as a string. The write bug is fixed; the value is always written as an integer.
**Migration**: Not applicable.

### Requirement: Runtime removal of legacy EV charger SoC fields
**Reason**: `migrate_ev_charger_legacy_fields` removed `min_soc_percent` / `target_soc_percent` from `ev_chargers[]`. This ran once for all users; the app no longer writes these fields.
**Migration**: Not applicable.
