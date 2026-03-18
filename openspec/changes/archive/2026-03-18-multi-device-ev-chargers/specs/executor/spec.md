## MODIFIED Requirements

### Requirement: Status API current_slot_plan includes mode_intent
The `get_status()` method SHALL include a `mode_intent` field in the `current_slot_plan` object. This field SHALL be computed by running the Controller's `decide()` method with the current slot plan and current system state. The `current_slot_plan` object SHALL also include `ev_charging_kw` (aggregate across all chargers), `ev_charger_plans` (per-device dict), and `discharge_kw` from the slot plan.

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

## ADDED Requirements

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
