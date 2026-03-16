## MODIFIED Requirements

### Requirement: Execution records include ev_charging_kw

The execution record logged by the executor SHALL include the `ev_charging_kw` value from the ORIGINAL slot plan (before any source isolation override), so that downstream consumers (API, frontend) can detect EV charging context without inferring it from other fields.

#### Scenario: EV charging slot logs ev_charging_kw

- **WHEN** the executor processes a slot with `ev_charging_kw = 10.0` in the schedule
- **AND** source isolation overwrites `discharge_kw` to 0
- **THEN** the execution record includes `ev_charging_kw = 10.0` (from the original slot)

#### Scenario: Non-EV slot logs zero ev_charging_kw

- **WHEN** the executor processes a slot with no EV charging planned
- **THEN** the execution record includes `ev_charging_kw = 0.0`

## ADDED Requirements

### Requirement: Execution records log original planned values before EV override

The execution record's planned fields (`planned_charge_kw`, `planned_discharge_kw`, `planned_export_kw`, `planned_water_kw`) SHALL reflect the ORIGINAL slot plan from `schedule.json`, not the modified slot after source isolation or other runtime overrides.

#### Scenario: Source isolation does not affect logged planned discharge

- **WHEN** the schedule has `battery_discharge_kw = 1.4` for a slot
- **AND** EV source isolation overwrites `discharge_kw` to 0.0 for the controller
- **THEN** the execution record includes `planned_discharge_kw = 1.4`

#### Scenario: Non-EV slots are unaffected

- **WHEN** no source isolation is active
- **THEN** the execution record's planned fields match the slot plan exactly (no change in behavior)

### Requirement: Execution records carry isolation reason when source isolation is active

When EV source isolation activates during a tick, the executor SHALL populate the `override_reason` field of the execution record with a descriptive string including scheduled and actual EV power. This applies only when no real override (e.g., quick action, force charge) is already active.

#### Scenario: Source isolation populates override_reason

- **WHEN** EV source isolation is active (`ev_should_charge_block = True`)
- **AND** no real override is active (`override.override_needed = False`)
- **THEN** the execution record's `override_reason` contains a string like `"EV source isolation: 10.0kW scheduled, 0.0kW actual"`

#### Scenario: Real override takes precedence over isolation reason

- **WHEN** both a real override and EV source isolation are active
- **THEN** the execution record's `override_reason` reflects the real override, not the isolation
