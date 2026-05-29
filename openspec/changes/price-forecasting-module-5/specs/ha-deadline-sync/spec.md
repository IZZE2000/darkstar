## ADDED Requirements

### Requirement: Backend subscribes to HA input_datetime entity state changes
When a charger has `ha_deadline_entity` configured, the backend SHALL subscribe to `state_changed` events for that entity via the existing HA WebSocket connection. When the entity state changes in HA, the backend SHALL update the corresponding charger's deadline in `data/ev_multi_day_state.json`.

#### Scenario: User sets deadline via HA UI
- **WHEN** the user sets `input_datetime.ev_departure_tesla` to `"2026-04-11 07:00:00"` via the HA dashboard
- **AND** charger `ev_charger_1` has `ha_deadline_entity: "input_datetime.ev_departure_tesla"`
- **THEN** the backend SHALL receive the `state_changed` event
- **AND** SHALL parse the datetime and update the state file with the new deadline for `ev_charger_1`
- **AND** SHALL compute `target_kwh` from the existing `target_pct` in the state file (or use default 80% if no target_pct is set)

#### Scenario: HA automation resets deadline weekly
- **WHEN** an HA automation triggers `input_datetime.set_datetime` on the entity (e.g., every Sunday setting next Friday 07:00)
- **THEN** the backend SHALL receive the state change and update the charger's deadline in the state file

#### Scenario: HA entity cleared or set to empty
- **WHEN** the HA entity state becomes empty, "unknown", or "unavailable"
- **THEN** the backend SHALL clear the charger's deadline in the state file (set to null)

### Requirement: Backend reads HA input_datetime entity on startup
On backend startup, for each charger with `ha_deadline_entity` configured, the backend SHALL read the current state of the HA entity via REST API. If the entity has a valid datetime value and the state file has no deadline for that charger, the HA value SHALL be used as the initial deadline.

#### Scenario: HA entity has a deadline, state file is empty
- **WHEN** backend starts and `input_datetime.ev_departure_tesla` has value `"2026-04-11 07:00:00"`
- **AND** the state file has no deadline for that charger
- **THEN** the backend SHALL set the charger's deadline in the state file to `"2026-04-11T07:00:00"`

#### Scenario: State file already has a deadline on startup
- **WHEN** backend starts and both the HA entity and the state file have deadline values
- **THEN** the state file value SHALL take precedence (it was the last user action)
- **AND** the backend SHALL write the state file deadline back to the HA entity to resync

#### Scenario: HA entity does not exist or is unreachable
- **WHEN** backend starts and the configured `ha_deadline_entity` cannot be read
- **THEN** the backend SHALL log a warning and continue without HA sync for that charger
- **AND** the state file deadline (if any) SHALL be used unchanged

### Requirement: Darkstar writes deadline back to HA entity on change
When a deadline is set or cleared via the Darkstar API (`POST /api/ev/chargers/{id}/deadline`), and the charger has `ha_deadline_entity` configured, the backend SHALL write the new deadline value to the HA entity using the `input_datetime.set_datetime` service.

#### Scenario: Deadline set in Darkstar, synced to HA
- **WHEN** user sets deadline via the Darkstar dashboard
- **AND** charger has `ha_deadline_entity: "input_datetime.ev_departure_tesla"`
- **THEN** the backend SHALL call `input_datetime.set_datetime` with the deadline datetime
- **AND** the HA entity state SHALL update to match the Darkstar deadline

#### Scenario: Deadline cleared in Darkstar, synced to HA
- **WHEN** deadline is cleared (set to null) in Darkstar
- **THEN** the backend SHALL call `input_datetime.set_datetime` with a default/empty value on the HA entity

### Requirement: Write-back loop prevention via debounce
The backend SHALL prevent feedback loops where a Darkstar→HA write triggers a HA→Darkstar state_changed event that triggers another write. The backend SHALL ignore `state_changed` events for a charger's `ha_deadline_entity` that arrive within 5 seconds of the last Darkstar-initiated write to that same entity.

#### Scenario: Darkstar writes, HA echoes back
- **WHEN** Darkstar writes deadline to HA entity at T=0
- **AND** HA emits a `state_changed` event for that entity at T=1 (1 second later)
- **THEN** the backend SHALL ignore the `state_changed` event (within debounce window)
- **AND** the state file SHALL NOT be updated again

#### Scenario: Genuine HA-side change outside debounce window
- **WHEN** the last Darkstar-initiated write was more than 5 seconds ago
- **AND** a `state_changed` event arrives for the HA entity
- **THEN** the backend SHALL process it as a genuine HA-side change and update the state file

### Requirement: HA datetime parsing handles multiple formats
The HA `input_datetime` entity may report state in different formats depending on configuration (date-only, time-only, or date+time). The backend SHALL parse the following formats:
- `"2026-04-11 07:00:00"` (HA default date+time)
- `"2026-04-11T07:00:00"` (ISO 8601)
- `"2026-04-11T07:00:00+02:00"` (ISO 8601 with timezone)

If the value cannot be parsed as a valid datetime, the backend SHALL log a warning and ignore the update.

#### Scenario: HA reports date+time in default format
- **WHEN** HA entity state is `"2026-04-11 07:00:00"` (space-separated)
- **THEN** the backend SHALL parse it as April 11, 2026 at 07:00 in the system's configured timezone

#### Scenario: HA reports unparseable value
- **WHEN** HA entity state is `"07:00:00"` (time-only, no date)
- **THEN** the backend SHALL log a warning "Cannot parse time-only value as deadline"
- **AND** the state file SHALL NOT be updated

### Requirement: input_datetime added to allowed service domains
The `HAClient.call_service()` domain allowlist SHALL include `input_datetime` as a valid domain for write operations. The allowed service SHALL be `set_datetime`.

#### Scenario: call_service with input_datetime domain
- **WHEN** `call_service(domain="input_datetime", service="set_datetime", entity_id="input_datetime.ev_departure_tesla", data={"datetime": "2026-04-11 07:00:00"})` is called
- **THEN** the domain safety guard SHALL allow the call
- **AND** the service SHALL execute against the HA API
