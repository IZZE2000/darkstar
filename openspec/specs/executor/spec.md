## Purpose

The Executor is responsible for executing scheduled energy management decisions by controlling Home Assistant entities (inverters, water heaters, EV chargers). It bridges the planner's decisions with physical device control.

## Requirements

### Requirement: Executor handles Home Assistant service failures gracefully
The executor SHALL NOT crash when Home Assistant service calls fail or time out. Any errors encountered when communicating with Home Assistant MUST be logged and wrapped in `HACallError` so the executor tick can continue safely and the result log remains intact.

#### Scenario: Home Assistant API times out during a service call
- **WHEN** any `call_service` HTTP request takes longer than the configured timeout
- **THEN** the timeout is caught and wrapped as `HACallError`
- **AND THEN** the retry-with-backoff mechanism attempts up to 3 times before giving up
- **AND THEN** if all retries are exhausted, `HACallError` is raised to the caller

#### Scenario: Home Assistant API times out during water heater control
- **WHEN** the `set_water_temp` service call fails after all retries
- **THEN** the water heater action is recorded as a failed `ActionResult` in the tick result log
- **AND THEN** the rest of the executor tick continues normally (profile actions are still executed)
- **AND THEN** no previously collected action results are lost

### Requirement: call_service uses retry-with-backoff
`HAClient.call_service` SHALL use the same `_retry_with_backoff` mechanism as `get_state`, with 3 attempts and a 1-second base delay, treating `TimeoutError` and `aiohttp.ClientError` as retryable.

### Requirement: Timeout handling is tested
A unit test SHALL exist verifying that a `TimeoutError` raised by the HTTP session during `call_service` results in an `HACallError` being raised by the client.

### Requirement: Status API current_slot_plan includes mode_intent

The `get_status()` method SHALL include a `mode_intent` field in the `current_slot_plan` object. This field SHALL be computed by running the Controller's `decide()` method with the current slot plan and current system state. The `current_slot_plan` object SHALL also include `ev_charging_kw` and `discharge_kw` from the slot plan.

If the controller cannot produce a decision (e.g., system state unavailable, profile not loaded), `mode_intent` SHALL be `null`.

#### Scenario: Status API returns mode_intent for current slot
- **WHEN** the executor status is requested and a current slot exists
- **AND** the controller can evaluate the slot with current system state
- **THEN** `current_slot_plan.mode_intent` contains the controller's mode intent string (one of: `"charge"`, `"self_consumption"`, `"idle"`, `"export"`)

#### Scenario: Status API returns null mode_intent when controller unavailable
- **WHEN** the executor status is requested but system state cannot be gathered (e.g., HA offline)
- **THEN** `current_slot_plan.mode_intent` is `null`
- **AND THEN** all other `current_slot_plan` fields are still populated from the schedule

### Requirement: Execution records include ev_charging_kw

The execution record logged by the executor SHALL include the `ev_charging_kw` value from the ORIGINAL slot plan (before any source isolation override), so that downstream consumers (API, frontend) can detect EV charging context without inferring it from other fields.

#### Scenario: EV charging slot logs ev_charging_kw

- **WHEN** the executor processes a slot with `ev_charging_kw = 10.0` in the schedule
- **AND** source isolation overwrites `discharge_kw` to 0
- **THEN** the execution record includes `ev_charging_kw = 10.0` (from the original slot)

#### Scenario: Non-EV slot logs zero ev_charging_kw
- **WHEN** the executor processes a slot with no EV charging planned
- **THEN** the execution record includes `ev_charging_kw = 0.0`

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
