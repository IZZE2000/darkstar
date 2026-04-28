## MODIFIED Requirements

### Requirement: Per-device EV config structure
Each entry in `ev_chargers[]` SHALL support the following per-device fields: `departure_time` (string, HH:MM 24h format), `switch_entity` (string, HA entity ID), `replan_on_plugin` (boolean, default true), `replan_on_unplug` (boolean, default false). These fields replace the global `ev_departure_time` and `executor.ev_charger.*` settings.

Additionally, each entry SHALL support two optional multi-day fields: `deadline` (string, ISO 8601 datetime format, e.g., `"2026-04-04T07:00"`) and `target_kwh` (float). When both are present and valid, the charger operates in multi-day mode. When absent, existing single-day `departure_time` behavior applies.

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

#### Scenario: Charger with multi-day deadline overrides departure_time
- **WHEN** a charger has both `departure_time: "07:00"` and `deadline: "2026-04-04T07:00"` with `target_kwh: 60`
- **AND** `price_forecast.enabled` is true
- **THEN** the multi-day deadline SHALL govern the charging schedule
- **AND** `departure_time` SHALL be ignored for deadline purposes

#### Scenario: Charger with multi-day deadline but price_forecast disabled
- **WHEN** a charger has `deadline` and `target_kwh` set but `price_forecast.enabled` is false
- **THEN** the `deadline` datetime SHALL be used as a simple deadline (like a far-future departure_time)
- **AND** no daily quota constraint SHALL apply (charge freely until the deadline)

### Requirement: Per-device deadline calculation
The pipeline SHALL calculate `ev_deadline` independently for each charger using that charger's `departure_time` field. Chargers without a departure time SHALL have `deadline: None`. When a charger has a multi-day `deadline` configured, the pipeline SHALL use the multi-day deadline datetime instead of calculating from `departure_time`.

#### Scenario: Two chargers with different departure times
- **WHEN** charger A has `departure_time: "07:00"` and charger B has `departure_time: "09:00"`
- **AND** current time is 22:00
- **THEN** charger A's deadline SHALL be tomorrow 07:00 and charger B's deadline SHALL be tomorrow 09:00

#### Scenario: Charger with no departure time
- **WHEN** a charger has `departure_time: ""`
- **THEN** its deadline SHALL be `None` (no deadline constraint in solver)

#### Scenario: Charger with multi-day deadline
- **WHEN** a charger has `deadline: "2026-04-04T07:00"` and today is 2026-04-01
- **THEN** the Kepler deadline for today's solve SHALL be end-of-day (today 23:59)
- **AND** on 2026-04-04, the Kepler deadline SHALL be 07:00
