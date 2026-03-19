## MODIFIED Requirements

### Requirement: Migrate executor EV charger settings into first charger
The migration SHALL copy `executor.ev_charger.switch_entity`, `executor.ev_charger.replan_on_plugin`, and `executor.ev_charger.replan_on_unplug` into the first enabled `ev_chargers[]` entry, only if those fields are not already set on that entry.

This migration step SHALL run **before** `remove_deprecated_keys()` is called. The deprecated key removal step MUST NOT execute before all field migration steps complete, as the migration reads from paths that are listed as deprecated.

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

#### Scenario: Migration runs before deprecated key removal
- **WHEN** `executor.ev_charger.switch_entity` is listed in `DEPRECATED_NESTED_KEYS`
- **AND** migration has not yet run
- **THEN** `_migrate_ev_charger_fields()` SHALL execute before `remove_deprecated_keys()`
- **AND** the switch entity value SHALL be present in `ev_chargers[0]` after both steps complete
