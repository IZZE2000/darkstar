## ADDED Requirements

### Requirement: Per-device EV config supports optional HA deadline entity
Each entry in `ev_chargers[]` SHALL support an optional `ha_deadline_entity` field (string, HA entity ID of an `input_datetime` helper). When configured, the backend SHALL sync the charger's multi-day deadline bidirectionally with this HA entity.

#### Scenario: Charger with HA deadline entity configured
- **WHEN** charger has `ha_deadline_entity: "input_datetime.ev_departure_tesla"`
- **THEN** the config loader SHALL store the entity ID on the charger config
- **AND** the backend SHALL subscribe to state changes for that entity

#### Scenario: Charger without HA deadline entity
- **WHEN** charger has no `ha_deadline_entity` field (or it is empty/null)
- **THEN** no HA subscription SHALL be created for deadline sync
- **AND** the charger SHALL operate using only Darkstar-side deadline management

### Requirement: Per-device EV config supports target_pct as alternative to target_kwh
Each entry in `ev_chargers[]` SHALL support an optional `target_pct` field (float, 0-100) as an alternative to `target_kwh`. When `target_pct` is set, the system SHALL compute `target_kwh = (target_pct / 100) * battery_capacity_kwh` at runtime using the charger's configured `battery_capacity_kwh`.

#### Scenario: Config with target_pct
- **WHEN** charger has `target_pct: 80` and `battery_capacity_kwh: 82.0`
- **THEN** the pipeline SHALL compute `target_kwh = 65.6` for the MultiDayPlanner

#### Scenario: Config with both target_pct and target_kwh
- **WHEN** charger has both `target_pct: 80` and `target_kwh: 60`
- **THEN** `target_pct` SHALL take precedence and `target_kwh` SHALL be recomputed from `target_pct`

#### Scenario: Config with target_pct but no battery_capacity_kwh
- **WHEN** charger has `target_pct: 80` but `battery_capacity_kwh` is null or 0
- **THEN** the system SHALL log a warning "Cannot compute target_kwh: battery_capacity_kwh not set"
- **AND** multi-day mode SHALL NOT activate for that charger

## MODIFIED Requirements

### Requirement: Per-device EV config structure
Each entry in `ev_chargers[]` SHALL support the following per-device fields: `departure_time` (string, HH:MM 24h format), `switch_entity` (string, HA entity ID), `replan_on_plugin` (boolean, default true), `replan_on_unplug` (boolean, default false). These fields replace the global `ev_departure_time` and `executor.ev_charger.*` settings.

Additionally, each entry SHALL support the following optional fields:
- `deadline` (string, ISO 8601 datetime format, e.g., `"2026-04-04T07:00"`)
- `target_kwh` (float)
- `target_pct` (float, 0-100)
- `ha_deadline_entity` (string, HA entity ID for `input_datetime` helper)

When both `deadline` and a valid target (`target_pct` or `target_kwh`) are present, the charger operates in multi-day mode. When absent, existing single-day `departure_time` behavior applies.

The config loader SHALL use a YAML 1.2 parser (ruamel.yaml) to read `config.yaml`, ensuring that unquoted `HH:MM` values are read as strings, not as YAML 1.1 sexagesimal integers.

The config loader SHALL accept `departure_time` as either a string in `"HH:MM"` format or an integer representing minutes since midnight (0–1439). If an integer is provided, it SHALL be converted to `"HH:MM"` format (e.g., `960` → `"16:00"`). Values outside 0–1439 SHALL be treated as invalid and result in `None`.

#### Scenario: Two chargers with different departure times
- **WHEN** `ev_chargers` contains charger "tesla" with `departure_time: "07:00"` and charger "leaf" with `departure_time: "08:30"`
- **THEN** the planner SHALL use 07:00 as the deadline for tesla and 08:30 as the deadline for leaf

#### Scenario: Charger with no departure time
- **WHEN** an enabled charger has `departure_time: ""` or the field is absent
- **THEN** the planner SHALL not apply a deadline constraint for that charger (charge whenever cheapest)

#### Scenario: Charger with no switch entity
- **WHEN** an enabled charger has `switch_entity: ""` or the field is absent
- **THEN** the executor SHALL skip switch control for that charger (planning-only mode)

#### Scenario: Departure time stored as YAML 1.1 sexagesimal integer
- **WHEN** `departure_time` is read from config as the integer `960` (due to prior YAML 1.1 parsing of `16:00`)
- **THEN** the config loader SHALL convert it to the string `"16:00"`
- **AND** the planner SHALL use 16:00 as the deadline for that charger

#### Scenario: Departure time stored as out-of-range integer
- **WHEN** `departure_time` is read from config as an integer outside 0–1439 (e.g., `9999`)
- **THEN** the config loader SHALL treat it as invalid and return `None`
- **AND** the planner SHALL not apply a deadline constraint for that charger

#### Scenario: Unquoted HH:MM in config.yaml read correctly
- **WHEN** config.yaml contains `departure_time: 16:00` (unquoted)
- **THEN** the YAML 1.2 parser SHALL read it as the string `"16:00"` (not the integer `960`)
- **AND** the planner SHALL use 16:00 as the deadline

#### Scenario: Charger with multi-day deadline from state file overrides config
- **WHEN** charger has `deadline: "2026-04-04T07:00"` in config AND `deadline: "2026-04-06T09:00"` in the state file
- **THEN** the state file deadline SHALL take precedence

#### Scenario: Charger with HA deadline entity and state file deadline
- **WHEN** charger has `ha_deadline_entity: "input_datetime.ev_departure_tesla"` configured
- **AND** the state file has a deadline set
- **THEN** the state file deadline SHALL be the active deadline
- **AND** the HA entity SHALL be synced to match
