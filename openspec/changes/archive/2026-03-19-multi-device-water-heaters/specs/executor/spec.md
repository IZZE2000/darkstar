## MODIFIED Requirements

### Requirement: Status API current_slot_plan includes mode_intent

The `get_status()` method SHALL include a `mode_intent` field in the `current_slot_plan` object. This field SHALL be computed by running the Controller's `decide()` method with the current slot plan and current system state. The `current_slot_plan` object SHALL also include `ev_charging_kw`, `discharge_kw`, and `water_heater_plans` from the slot plan.

If the controller cannot produce a decision (e.g., system state unavailable, profile not loaded), `mode_intent` SHALL be `null`.

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

## ADDED Requirements

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
