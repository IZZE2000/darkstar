## ADDED Requirements

### Requirement: Config help tooltips document soft vs hard bounds clearly
The configuration help text (`frontend/src/config-help.json`) SHALL document `battery.max_soc_percent` and `system.battery.max_soc_percent` as **soft** ceilings — a preference the solver penalizes overshooting but tolerates when the battery is already above the limit at planning time.

The tooltip SHALL explicitly state that (a) the BMS enforces the absolute physical limit, (b) the solver treats this value as a target ceiling, and (c) starting the plan above the ceiling results in a discharge action, not a failure.

The comments in `config.default.yaml` next to `max_soc_percent` SHALL be updated with the same guidance.

#### Scenario: Tooltip describes soft semantics
- **WHEN** a user hovers the help indicator for `battery.max_soc_percent` in Settings
- **THEN** the tooltip text explicitly contains the words "soft" or "preference" (or equivalent phrasing)
- **AND** the tooltip states that exceeding the value does not cause planner failure

#### Scenario: Default config comment matches tooltip
- **WHEN** a user opens `config.default.yaml`
- **THEN** the comment adjacent to `max_soc_percent` reflects the soft semantics described in the tooltip

### Requirement: EV charger max_power_kw tooltip is explicit about requirement
The configuration help text for the per-charger `max_power_kw` field SHALL explicitly state that the field is **required**, SHALL give one or more example values (e.g., 7.4, 11, 22 kW), and SHALL warn that leaving it blank or setting it to zero causes the charger to be registered as disabled.

#### Scenario: EV power tooltip states requirement and example
- **WHEN** a user opens the EV charger editor and hovers the help indicator for `max_power_kw`
- **THEN** the tooltip text contains the word "required" (or equivalent phrasing)
- **AND** the tooltip includes at least one example value
- **AND** the tooltip warns that a missing or zero value disables the charger

### Requirement: Cumulative energy sensor tooltips explain expected sensor shape
The configuration help tooltips for each of the six cumulative energy input sensors SHALL explicitly describe the expected sensor shape: a cumulative (monotonically increasing) energy counter with `device_class: energy` and a unit of `kWh`, `Wh`, or `MWh`. The tooltips SHALL warn that power sensors (units `W`, `kW`) are not valid choices.

The six keys covered SHALL be:
- `input_sensors.total_load_consumption`
- `input_sensors.total_grid_import`
- `input_sensors.total_grid_export`
- `input_sensors.total_pv_production`
- `input_sensors.total_battery_charge`
- `input_sensors.total_battery_discharge`

The tooltips MAY include example entity naming patterns (e.g., `sensor.*_energy_total`, `sensor.*_consumed_energy`).

No runtime validation of sensor attributes is introduced by this requirement — tooltips are the sole mitigation.

#### Scenario: Load consumption tooltip describes cumulative sensor requirement
- **WHEN** a user hovers the help indicator for `input_sensors.total_load_consumption` in Settings
- **THEN** the tooltip text explicitly describes a cumulative energy counter
- **AND** the tooltip explicitly warns against selecting a power sensor (W/kW)
- **AND** the tooltip mentions `device_class: energy` or equivalent phrasing

#### Scenario: All six cumulative sensor tooltips updated
- **WHEN** `frontend/src/config-help.json` is loaded
- **THEN** each of the six `input_sensors.total_*` keys has a tooltip that describes the expected cumulative energy counter shape and warns against power sensors
