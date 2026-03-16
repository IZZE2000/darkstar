# Spec: Config Migration

## Purpose

Defines the behaviour of `migrate_config()` — the startup routine responsible for bringing user config files up to the current schema. The migration MUST be safe, idempotent, and non-destructive: it may only write when a change is required, must preserve user values, and must never corrupt a config file that fails structural validation.

## Requirements

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
