## ADDED Requirements

### Requirement: Write endpoint accepts deadline and target percentage
The API SHALL expose `POST /api/ev/chargers/{id}/deadline` accepting a JSON body with `deadline` (ISO 8601 datetime string or null) and `target_pct` (float 0-100 or null). The endpoint SHALL validate inputs, convert `target_pct` to `target_kwh` using the charger's `battery_capacity_kwh` from config, and persist to the multi-day state file.

#### Scenario: Set deadline and target for a charger
- **WHEN** `POST /api/ev/chargers/ev_charger_1/deadline` is called with `{ "deadline": "2026-04-11T07:00", "target_pct": 80 }`
- **AND** charger `ev_charger_1` has `battery_capacity_kwh: 82.0` in config
- **THEN** the endpoint SHALL compute `target_kwh = (80 / 100) * 82.0 = 65.6`
- **AND** SHALL write `deadline`, `target_pct: 80`, and `target_kwh: 65.6` to `data/ev_multi_day_state.json` for that charger
- **AND** SHALL return the updated charger state with HTTP 200

#### Scenario: Clear deadline for a charger
- **WHEN** `POST /api/ev/chargers/ev_charger_1/deadline` is called with `{ "deadline": null, "target_pct": null }`
- **THEN** the endpoint SHALL set `deadline`, `target_pct`, and `target_kwh` to null in the state file for that charger
- **AND** SHALL return the updated charger state with HTTP 200

#### Scenario: Invalid charger ID
- **WHEN** `POST /api/ev/chargers/nonexistent/deadline` is called
- **THEN** the endpoint SHALL return HTTP 404 with error message "Charger not found"

#### Scenario: Deadline in the past
- **WHEN** `POST /api/ev/chargers/ev_charger_1/deadline` is called with a `deadline` that is in the past
- **THEN** the endpoint SHALL return HTTP 422 with error message "Deadline must be in the future"

#### Scenario: Target percentage out of range
- **WHEN** `POST /api/ev/chargers/ev_charger_1/deadline` is called with `target_pct: 150`
- **THEN** the endpoint SHALL return HTTP 422 with error message "target_pct must be between 0 and 100"

#### Scenario: Target percentage without deadline
- **WHEN** `POST /api/ev/chargers/ev_charger_1/deadline` is called with `{ "deadline": null, "target_pct": 80 }`
- **THEN** the endpoint SHALL return HTTP 422 with error message "target_pct requires a deadline"

### Requirement: Write endpoint triggers HA sync when configured
When a charger has `ha_deadline_entity` configured, the write endpoint SHALL write the deadline value to the HA `input_datetime` entity after persisting to the state file. HA sync failures SHALL NOT cause the endpoint to fail.

#### Scenario: Deadline written to HA entity
- **WHEN** deadline is set for a charger with `ha_deadline_entity: "input_datetime.ev_departure_tesla"`
- **THEN** the endpoint SHALL call `input_datetime.set_datetime` on the HA entity with the deadline value
- **AND** the HTTP response SHALL not be delayed by the HA call

#### Scenario: HA entity write fails
- **WHEN** deadline is set but the HA `input_datetime` entity is unreachable
- **THEN** the state file SHALL still be updated with the new deadline
- **AND** the endpoint SHALL return HTTP 200 (success)
- **AND** the HA write failure SHALL be logged as a warning

#### Scenario: Deadline cleared, HA entity reset
- **WHEN** deadline is cleared (set to null) for a charger with `ha_deadline_entity` configured
- **THEN** the endpoint SHALL call `input_datetime.set_datetime` on the HA entity with a default/empty value

### Requirement: State file is source of truth for user-set deadlines
The `data/ev_multi_day_state.json` file SHALL be the primary source of truth for user-set deadlines and target percentages. The pipeline SHALL read deadline and target_kwh from the state file. If the state file does not contain a deadline for a charger, the pipeline SHALL fall back to `config.yaml` values.

#### Scenario: State file overrides config
- **WHEN** `config.yaml` has `deadline: "2026-04-10T07:00"` and the state file has `deadline: "2026-04-12T09:00"` for the same charger
- **THEN** the pipeline SHALL use the state file value `"2026-04-12T09:00"`

#### Scenario: State file missing or corrupt
- **WHEN** `data/ev_multi_day_state.json` does not exist or cannot be parsed
- **THEN** the pipeline SHALL fall back to `config.yaml` values for deadline and target_kwh
- **AND** the API endpoint SHALL recreate the state file on next write

#### Scenario: State file has no deadline for a charger
- **WHEN** the state file exists but has no entry (or null deadline) for a specific charger
- **THEN** the pipeline SHALL fall back to that charger's `config.yaml` deadline value (if any)

### Requirement: Write endpoint returns updated charger state
After persisting changes, the write endpoint SHALL return the updated state for the affected charger in the same format as a single entry from `GET /api/ev/chargers`.

#### Scenario: Response includes computed fields
- **WHEN** deadline is set successfully
- **THEN** the response SHALL include `id`, `deadline`, `target_pct`, `target_kwh`, `mode: "multi_day"`, and any existing multi-day state fields (remaining_kwh, quota, status may be null if planner hasn't run yet)

### Requirement: Auto-clear deadline on trip completion
When the pipeline detects that `remaining_kwh <= 0` for a charger with an active deadline, it SHALL auto-clear the deadline by setting `deadline`, `target_pct`, and `target_kwh` to null in the state file. If `ha_deadline_entity` is configured, the HA entity SHALL also be cleared.

#### Scenario: Target reached, deadline auto-clears
- **WHEN** planner runs and computes `remaining_kwh = 0` for a charger with deadline `"2026-04-11T07:00"`
- **THEN** the state file SHALL be updated with null deadline, target_pct, and target_kwh for that charger
- **AND** the charger status SHALL be set to `"complete"` temporarily (until next state file write cycle)

#### Scenario: Target reached with HA entity configured
- **WHEN** deadline auto-clears and `ha_deadline_entity` is configured
- **THEN** the HA entity SHALL be cleared (set to default/empty value)

### Requirement: Missed deadline detection and warning
When the pipeline detects that a charger's deadline has passed but `remaining_kwh > 0`, it SHALL set the charger status to `"missed"` in the state file. The deadline SHALL NOT auto-clear — the user must manually clear or update it.

#### Scenario: Deadline passes with remaining energy
- **WHEN** planner runs after the deadline datetime and `remaining_kwh` is 12.3 kWh
- **THEN** the state file SHALL set `status: "missed"` for that charger
- **AND** the deadline SHALL remain in the state file (not auto-cleared)
