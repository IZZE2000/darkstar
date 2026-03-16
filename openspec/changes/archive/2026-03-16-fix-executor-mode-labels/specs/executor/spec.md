## MODIFIED Requirements

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

The execution record logged by the executor SHALL include the `ev_charging_kw` value from the slot plan, so that downstream consumers (API, frontend) can detect EV charging context without inferring it from other fields.

#### Scenario: EV charging slot logs ev_charging_kw
- **WHEN** the executor processes a slot with `ev_charging_kw = 2.0` in the plan
- **THEN** the execution record includes `ev_charging_kw = 2.0`

#### Scenario: Non-EV slot logs zero ev_charging_kw
- **WHEN** the executor processes a slot with no EV charging planned
- **THEN** the execution record includes `ev_charging_kw = 0.0`
