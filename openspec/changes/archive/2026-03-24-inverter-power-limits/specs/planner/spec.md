## ADDED Requirements

### Requirement: Solver Enforces Inverter AC Output Limit

When `max_inverter_ac_kw` is provided in `KeplerConfig`, the solver SHALL add a per-slot constraint ensuring battery discharge energy plus PV energy does not exceed the inverter's AC output capacity for that slot.

The constraint SHALL be: `discharge[t] + pv_kwh[t] <= max_inverter_ac_kw * slot_hours[t]`

Where `pv_kwh[t]` is the (already DC-clipped) PV input for the slot — a constant, not a decision variable.

#### Scenario: Inverter AC limit constrains discharge during high PV
- **GIVEN** `max_inverter_ac_kw = 10.0` and slot duration is 0.25h
- **AND** slot PV is 2.0 kWh (8kW average, already DC-clipped)
- **WHEN** the solver optimizes
- **THEN** `discharge[t] <= 2.5 - 2.0 = 0.5 kWh` (2kW average max discharge)

#### Scenario: No AC limit when key is not configured
- **WHEN** `max_inverter_ac_kw` is `None` in `KeplerConfig`
- **THEN** no inverter AC constraint SHALL be added (backwards compatible)

### Requirement: Planner Adapter Clips PV by DC Input Limit

When `system.inverter.max_dc_input_kw` is configured, the planner adapter SHALL clip each slot's `pv_kwh` to `min(pv_kwh, max_dc_input_kw * slot_hours)` before constructing the `KeplerInputSlot`.

#### Scenario: High PV clipped to DC limit
- **GIVEN** `max_dc_input_kw = 12.0` and slot duration is 0.25h
- **AND** forecast PV is 4.0 kWh (16kW average)
- **WHEN** the adapter builds `KeplerInputSlot`
- **THEN** `pv_kwh` SHALL be `3.0` (12 * 0.25)

#### Scenario: DC limit not set
- **WHEN** `system.inverter.max_dc_input_kw` is not configured
- **THEN** `pv_kwh` SHALL pass through unchanged

### Requirement: Planner Adapter Maps Inverter Config to KeplerConfig

The planner adapter SHALL read `system.inverter.max_ac_power_kw` and map it to `KeplerConfig.max_inverter_ac_kw`. If the key is not configured, `max_inverter_ac_kw` SHALL be `None`.

#### Scenario: Inverter AC limit passed to solver
- **GIVEN** `system.inverter.max_ac_power_kw` is `10.0`
- **WHEN** the adapter builds `KeplerConfig`
- **THEN** `KeplerConfig.max_inverter_ac_kw` SHALL be `10.0`
