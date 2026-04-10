## ADDED Requirements

### Requirement: Migrate global EV departure time into first charger
The migration SHALL copy `ev_departure_time` from root level into the first enabled `ev_chargers[]` entry as `departure_time`, only if that entry does not already have a `departure_time` value set.

#### Scenario: Global departure time migrated to first charger
- **WHEN** `ev_departure_time: "07:00"` exists at root level
- **AND** the first enabled charger has no `departure_time` field
- **THEN** the first enabled charger SHALL have `departure_time: "07:00"` after migration

#### Scenario: Existing per-device departure time preserved
- **WHEN** `ev_departure_time: "07:00"` exists at root level
- **AND** the first enabled charger already has `departure_time: "08:00"`
- **THEN** the charger's `departure_time` SHALL remain `"08:00"`

#### Scenario: No enabled chargers skips migration
- **WHEN** `ev_departure_time` exists but no chargers have `enabled: true`
- **THEN** the migration SHALL skip this step without error

### Requirement: Migrate executor EV charger settings into first charger
The migration SHALL copy `executor.ev_charger.switch_entity`, `executor.ev_charger.replan_on_plugin`, and `executor.ev_charger.replan_on_unplug` into the first enabled `ev_chargers[]` entry, only if those fields are not already set on that entry.

#### Scenario: Switch entity migrated
- **WHEN** `executor.ev_charger.switch_entity: "switch.wallbox"` exists
- **AND** the first enabled charger has no `switch_entity` field
- **THEN** the first enabled charger SHALL have `switch_entity: "switch.wallbox"` after migration

#### Scenario: Replan settings migrated with defaults preserved
- **WHEN** `executor.ev_charger.replan_on_plugin: true` and `executor.ev_charger.replan_on_unplug: false` exist
- **AND** the first enabled charger has no replan fields
- **THEN** the first enabled charger SHALL have `replan_on_plugin: true` and `replan_on_unplug: false`

#### Scenario: Existing per-device settings preserved
- **WHEN** the first enabled charger already has `switch_entity: "switch.other"`
- **THEN** that value SHALL NOT be overwritten by the executor.ev_charger migration

### Requirement: Deprecate migrated global EV settings
After migration, the following paths SHALL be added to the deprecated keys registry: `ev_departure_time` (root level), `executor.ev_charger.switch_entity`, `executor.ev_charger.replan_on_plugin`, `executor.ev_charger.replan_on_unplug`. These SHALL be removed from the config file during the deprecated-key cleanup phase.

#### Scenario: Deprecated keys removed after migration
- **WHEN** migration completes and deprecated key removal runs
- **THEN** `ev_departure_time` SHALL no longer exist at root level
- **AND** `executor.ev_charger.switch_entity`, `executor.ev_charger.replan_on_plugin`, `executor.ev_charger.replan_on_unplug` SHALL no longer exist

#### Scenario: executor.ev_charger section cleaned up
- **WHEN** all keys under `executor.ev_charger` have been migrated and deprecated
- **AND** no non-deprecated keys remain under `executor.ev_charger`
- **THEN** the entire `executor.ev_charger` section SHALL be removed

### Requirement: Migration is idempotent
Running the migration multiple times SHALL produce the same result. The migration SHALL only copy values when the target field is absent or empty.

#### Scenario: Second migration run is a no-op
- **WHEN** migration has already run once (per-device fields populated, deprecated keys removed)
- **AND** migration runs again on startup
- **THEN** no config file write SHALL occur

### Requirement: Config default template updated
The `config.default.yaml` template SHALL include the new per-device fields in `ev_chargers[]` entries (`departure_time`, `switch_entity`, `replan_on_plugin`, `replan_on_unplug`) with appropriate defaults. The global `ev_departure_time` and `executor.ev_charger` section SHALL be removed from the template.

#### Scenario: New installation gets per-device defaults
- **WHEN** a new user starts with `config.default.yaml`
- **THEN** each `ev_chargers[]` entry SHALL include `departure_time: ""`, `switch_entity: ""`, `replan_on_plugin: true`, `replan_on_unplug: false`
- **AND** no global `ev_departure_time` or `executor.ev_charger` section SHALL exist
