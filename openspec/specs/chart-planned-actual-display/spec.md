## Purpose

TBD: Define the purpose of chart planned vs actual display capability.

## Requirements

### Requirement: Main chart displays planned values for all slots

ChartCard SHALL display planned/forecasted values in the main chart elements (bars and solid lines) for ALL time slots, both historical (before NOW) and future (after NOW). This enables users to see what was planned across the entire 48-hour window.

#### Scenario: Historical slot shows planned charge value
- **WHEN** a slot is historical (before NOW marker) AND has both `battery_charge_kw` (planned) and `actual_charge_kw` values
- **THEN** the main charge bar SHALL display `battery_charge_kw` (planned value)
- **AND** the dotted "Actual Charge" overlay line SHALL display `actual_charge_kw`

#### Scenario: Future slot shows planned charge value
- **WHEN** a slot is future (after NOW marker) AND has `battery_charge_kw` value
- **THEN** the main charge bar SHALL display `battery_charge_kw`
- **AND** no actual overlay is shown (no actual data exists yet)

#### Scenario: Slot without planned value
- **WHEN** a slot has no `battery_charge_kw` or `charge_kw` value
- **THEN** the main charge bar SHALL show nothing (null)
- **AND** the slot is visually empty in the chart

### Requirement: Main chart displays forecasted PV for all slots

ChartCard SHALL display PV forecast values in the solid yellow line for ALL time slots. Actual PV generation is shown only in the dotted overlay for historical slots.

#### Scenario: Historical slot shows PV forecast with actual overlay
- **WHEN** a slot is historical AND has both `pv_forecast_kwh` and `actual_pv_kwh` values
- **THEN** the solid PV line SHALL display `pv_forecast_kwh` converted to kW
- **AND** the dotted "Actual PV" overlay line SHALL display `actual_pv_kwh` converted to kW

#### Scenario: Future slot shows PV forecast only
- **WHEN** a slot is future AND has `pv_forecast_kwh` value
- **THEN** the solid PV line SHALL display `pv_forecast_kwh` converted to kW
- **AND** no actual PV overlay is shown

### Requirement: Main chart displays forecasted load for all slots

ChartCard SHALL display load forecast values in the solid blue line for ALL time slots. Actual load is shown only in the dotted overlay for historical slots.

#### Scenario: Historical slot shows load forecast with actual overlay
- **WHEN** a slot is historical AND has both `load_forecast_kwh` and `actual_load_kwh` values
- **THEN** the solid Load line SHALL display `load_forecast_kwh` converted to kW
- **AND** the dotted "Actual Load" overlay line SHALL display `actual_load_kwh` converted to kW

### Requirement: All metrics follow consistent planned vs actual display pattern

ChartCard SHALL apply the same planned/actual display logic consistently across all energy metrics.

#### Scenario: Discharge metric follows pattern
- **WHEN** viewing discharge data
- **THEN** main bars SHALL show `battery_discharge_kw` (planned)
- **AND** dotted overlay SHALL show `actual_discharge_kw` for historical slots

#### Scenario: Water heating metric follows pattern
- **WHEN** viewing water heating data
- **THEN** main bars SHALL show `water_heating_kw` (planned)
- **AND** dotted overlay SHALL show `actual_water_kw` for historical slots

#### Scenario: EV charging metric follows pattern
- **WHEN** viewing EV charging data
- **THEN** main bars SHALL show `ev_charging_kw` (planned)
- **AND** dotted overlay SHALL show `actual_ev_charging_kw` for historical slots

#### Scenario: Export metric follows pattern
- **WHEN** viewing export data
- **THEN** main bars SHALL show `export_kwh` (planned)
- **AND** dotted overlay SHALL show `actual_export_kw` for historical slots

### Requirement: Planned values sourced from slot_plans database

The backend SHALL provide planned values from the `slot_plans` table for all historical slots via the `battery_charge_kw`, `battery_discharge_kw`, `water_heating_kw`, and `soc_target_percent` fields in the schedule API response.

#### Scenario: Backend provides planned values for historical slots
- **WHEN** the schedule API returns historical slot data
- **THEN** the response SHALL include `battery_charge_kw` from `slot_plans.planned_charge_kwh`
- **AND** the response SHALL include `battery_discharge_kw` from `slot_plans.planned_discharge_kwh`
- **AND** the response SHALL include `water_heating_kw` from `slot_plans.planned_water_heating_kwh`
