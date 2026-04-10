## MODIFIED Requirements

### Requirement: Per-device EV config structure
Each entry in `ev_chargers[]` SHALL support the following per-device fields: `departure_time` (string, HH:MM 24h format), `switch_entity` (string, HA entity ID), `replan_on_plugin` (boolean, default true), `replan_on_unplug` (boolean, default false). These fields replace the global `ev_departure_time` and `executor.ev_charger.*` settings.

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
