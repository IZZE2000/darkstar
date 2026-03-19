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

The `get_status()` method SHALL include a `mode_intent` field in the `current_slot_plan` object. This field SHALL be computed by running the Controller's `decide()` method with the current slot plan and current system state. The `current_slot_plan` object SHALL also include `ev_charging_kw` (aggregate across all chargers), `ev_charger_plans` (per-device dict), `discharge_kw`, and `water_heater_plans` from the slot plan.

If the controller cannot produce a decision (e.g., system state unavailable, profile not loaded), `mode_intent` SHALL be `null`.

#### Scenario: Status API returns per-device EV plan
- **WHEN** the executor status is requested and the current slot has per-device EV plans
- **THEN** `current_slot_plan.ev_charger_plans` SHALL contain a dict mapping charger ID to planned kW
- **AND** `current_slot_plan.ev_charging_kw` SHALL be the sum across all chargers

#### Scenario: Status API returns mode_intent for current slot
- **WHEN** the executor status is requested and a current slot exists
- **AND** the controller can evaluate the slot with current system state
- **THEN** `current_slot_plan.mode_intent` contains the controller's mode intent string (one of: `"charge"`, `"self_consumption"`, `"idle"`, `"export"`)

#### Scenario: Status API returns null mode_intent when controller unavailable
- **WHEN** the executor status is requested but system state cannot be gathered (e.g., HA offline)
- **THEN** `current_slot_plan.mode_intent` is `null`
- **AND THEN** all other `current_slot_plan` fields are still populated from the schedule

#### Scenario: Status API includes per-device water heater plans
- **WHEN** the executor status is requested and the current slot has per-device water heater plans
- **THEN** `current_slot_plan.water_heater_plans` SHALL contain the per-device dict (e.g., `{"main_tank": 3.0, "upstairs_tank": 0.0}`)

### Requirement: Execution records include ev_charging_kw

The execution record logged by the executor SHALL include the aggregate `ev_charging_kw` value from the ORIGINAL slot plan (before any source isolation override) as well as a `ev_charger_plans` dict with per-device planned kW, so that downstream consumers can identify which chargers were scheduled.

#### Scenario: Per-device EV plans in execution record

- **WHEN** the executor processes a slot with charger A at 11 kW and charger B at 7.4 kW
- **THEN** the execution record includes `ev_charging_kw = 18.4` and `ev_charger_plans = {"ev_charger_1": 11.0, "ev_charger_2": 7.4}`

#### Scenario: Non-EV slot logs zero
- **WHEN** the executor processes a slot with no EV charging planned
- **THEN** the execution record includes `ev_charging_kw = 0.0` and `ev_charger_plans = {}`

### Requirement: Execution records log original planned values before EV override

The execution record's planned fields (`planned_charge_kw`, `planned_discharge_kw`, `planned_export_kw`, `planned_water_kw`) SHALL reflect the ORIGINAL slot plan from `schedule.json`, not the modified slot after source isolation or other runtime overrides.

#### Scenario: Source isolation does not affect logged planned discharge

- **WHEN** the schedule has `battery_discharge_kw = 1.4` for a slot
- **AND** EV source isolation overwrites `discharge_kw` to 0.0 for the controller
- **THEN** the execution record includes `planned_discharge_kw = 1.4`

#### Scenario: Non-EV slots are unaffected

- **WHEN** no source isolation is active
- **THEN** the execution record's planned fields match the slot plan exactly (no change in behavior)

### Requirement: Per-device EV charger config loading
The executor config loader SHALL read per-device EV settings from `ev_chargers[]` entries, building a list of `EVChargerDeviceConfig` objects with `id`, `name`, `switch_entity`, `max_power_kw`, `battery_capacity_kwh`, `replan_on_plugin`, and `replan_on_unplug`. Only enabled chargers SHALL be loaded.

#### Scenario: Two enabled chargers loaded
- **WHEN** `ev_chargers` contains charger A (enabled, switch: "switch.tesla") and charger B (enabled, switch: "switch.leaf")
- **THEN** `ExecutorConfig.ev_chargers` SHALL contain two `EVChargerDeviceConfig` entries with the respective switch entities

#### Scenario: Disabled charger excluded
- **WHEN** charger B has `enabled: false`
- **THEN** only charger A SHALL appear in `ExecutorConfig.ev_chargers`

#### Scenario: Charger with empty switch entity
- **WHEN** a charger has `switch_entity: ""`
- **THEN** its `EVChargerDeviceConfig.switch_entity` SHALL be `None`

### Requirement: Executor reads per-device schedule
The executor SHALL parse the `ev_chargers` dict from each schedule slot to build `ev_charger_plans` in `SlotPlan`. If the `ev_chargers` key is missing (old-format schedule), the executor SHALL fall back to using the aggregate `ev_charging_kw` mapped to the first configured charger.

#### Scenario: New format schedule parsed
- **WHEN** a schedule slot contains `ev_chargers: {"ev_charger_1": {"charging_kw": 11.0}}`
- **THEN** `SlotPlan.ev_charger_plans` SHALL be `{"ev_charger_1": 11.0}`

#### Scenario: Old format schedule fallback
- **WHEN** a schedule slot contains only `ev_charging_kw: 11.0` with no `ev_chargers` key
- **THEN** `SlotPlan.ev_charger_plans` SHALL map the full amount to the first configured charger

### Requirement: Execution records carry isolation reason when source isolation is active

When EV source isolation activates during a tick, the executor SHALL populate the `override_reason` field of the execution record with a descriptive string including scheduled and actual EV power. This applies only when no real override (e.g., quick action, force charge) is already active.

#### Scenario: Source isolation populates override_reason

- **WHEN** EV source isolation is active (`ev_should_charge_block = True`)
- **AND** no real override is active (`override.override_needed = False`)
- **THEN** the execution record's `override_reason` contains a string like `"EV source isolation: 10.0kW scheduled, 0.0kW actual"`

#### Scenario: Real override takes precedence over isolation reason

- **WHEN** both a real override and EV source isolation are active
- **THEN** the execution record's `override_reason` reflects the real override, not the isolation

### Requirement: Per-device water heater executor config
The executor SHALL load per-device water heater configs from the `water_heaters[]` array. Each enabled heater with a `target_entity` SHALL have a `WaterHeaterDeviceConfig` containing `id`, `name`, `target_entity`, and `power_kw`. Temperature setpoints SHALL remain global on `WaterHeaterGlobalConfig`.

#### Scenario: Two heaters with target entities
- **WHEN** `water_heaters[]` contains two enabled entries with `target_entity` values
- **THEN** the executor SHALL create two `WaterHeaterDeviceConfig` objects

#### Scenario: Heater without target entity excluded from control
- **WHEN** an enabled heater has empty `target_entity`
- **THEN** the executor SHALL NOT create a device config for it (no control possible)

#### Scenario: Global temp setpoints unchanged
- **WHEN** the executor loads config
- **THEN** `temp_normal`, `temp_off`, `temp_boost`, `temp_max` SHALL still be read from `executor.water_heater`

### Requirement: Per-device SlotPlan for water heaters
`SlotPlan` SHALL include `water_heater_plans: dict[str, float]` mapping heater ID to planned kW. The aggregate `water_kw` SHALL remain as the sum for backward compatibility.

#### Scenario: Slot plan with two heaters
- **WHEN** the schedule has heater A at 3 kW and heater B at 0 kW
- **THEN** `water_heater_plans` SHALL be `{"main_tank": 3.0, "upstairs_tank": 0.0}`
- **AND** `water_kw` SHALL be `3.0`

#### Scenario: Old-format schedule fallback
- **WHEN** a schedule slot has `water_heating_kw: 3.0` but no `water_heaters` dict
- **THEN** the executor SHALL fall back to the aggregate `water_kw: 3.0` and control only the first heater

### Requirement: Per-device water temperature control
The executor SHALL set temperature for each heater independently based on its per-device plan. For each heater in `water_heater_plans`: if planned kW > 0, set to `temp_normal`; if planned kW == 0, set to `temp_off`. Each heater uses its own `target_entity`.

#### Scenario: Two heaters with different plans
- **WHEN** heater A has planned kW 3.0 and heater B has planned kW 0.0
- **THEN** the executor SHALL call `set_water_temp(heater_A.target_entity, temp_normal)`
- **AND** the executor SHALL call `set_water_temp(heater_B.target_entity, temp_off)`

#### Scenario: All heaters idle
- **WHEN** all heaters have planned kW 0.0
- **THEN** the executor SHALL set all heaters to `temp_off`

### Requirement: Per-device water controller decisions
`ControllerDecision` SHALL include `water_temps: dict[str, int]` mapping heater ID to temperature target. The controller SHALL determine each heater's temperature based on its per-device plan from `SlotPlan.water_heater_plans`.

#### Scenario: Controller decides per-device temperatures
- **WHEN** the controller evaluates a slot with heater A planned at 3 kW and heater B at 0 kW
- **THEN** `water_temps` SHALL be `{"main_tank": 60, "upstairs_tank": 40}` (using global temp_normal and temp_off)

#### Scenario: Backward compatible water_temp field
- **WHEN** per-device plans exist
- **THEN** the scalar `water_temp` field SHALL reflect the maximum temperature across all heaters (for logging/status compat)
