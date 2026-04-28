## Purpose

The Kepler planner SHALL schedule water heater boost and custom entity sink actions only when there is genuine excess PV — i.e., forecast PV exceeds all forecast consumption AND the battery SoC is near full. This ensures the priority order: battery charges first, EV charges if applicable, then excess goes to the chosen sink.

## Requirements

### Requirement: Sink activation requires configurable SoC threshold (default 95%)

Excess PV MUST always charge the battery first. The sink (water heater boost or custom entity) SHALL only activate in slots where the solver's projected battery SoC >= a configurable threshold `soc_threshold_percent` (default 95%). This is enforced via a big-M binary constraint in the MILP:

```
soc_binary[t] ∈ {0, 1}
soc[t] >= threshold_kWh - M * (1 - soc_binary[t])   // if binary=1, SoC >= threshold%
sink_var[t] <= soc_binary[t]                         // sink requires SoC above threshold
```

Where `M = capacity_kWh` and `threshold_kWh = capacity_kWh * soc_threshold_percent / 100`.

#### Scenario: Sink does not activate when battery is below threshold
- **WHEN** slot 14 has forecast excess PV (PV > load + water + EV)
- **AND** projected battery SoC in slot 14 is 80%
- **AND** `soc_threshold_percent` is 95
- **THEN** the sink SHALL NOT activate in slot 14
- **AND** the excess PV SHALL go to battery charging

#### Scenario: Sink activates when battery is at or above threshold
- **WHEN** slot 14 has forecast excess PV
- **AND** projected battery SoC in slot 14 is 95%
- **AND** `soc_threshold_percent` is 95
- **THEN** the sink MAY activate in slot 14 (subject to reward vs export economics)

#### Scenario: Lower threshold allows earlier sink activation
- **WHEN** `soc_threshold_percent` is set to 85
- **AND** projected battery SoC in slot 14 is 87%
- **THEN** the sink MAY activate in slot 14

#### Scenario: Battery charges first across the full horizon
- **WHEN** the solver plans a full day with morning low SoC and afternoon high PV
- **THEN** the solver SHALL schedule battery charging during morning/early afternoon
- **AND** sink activation SHALL only appear in slots where battery SoC first reaches the configured threshold
- **AND** no sink activation SHALL occur before the battery is near full

### Requirement: Pre-calculated excess PV flags serve as coarse filter

Before the MILP runs, the solver SHALL pre-calculate per-slot excess PV flags from raw forecasts: `excess[t] = max(0, pv_forecast[t] - load_forecast[t] - min_water_heat_forecast[t] - min_ev_forecast[t]) > 0`. These flags are a **coarse upper bound** that excludes slots where PV cannot possibly exceed demand. Sink variables are constrained to slots where this flag is true AND SoC >= `soc_threshold_percent`.

#### Scenario: Nighttime slot excluded by coarse filter
- **WHEN** slot 3 has zero PV forecast
- **THEN** the excess PV flag SHALL be false
- **AND** no sink variable SHALL be created for that slot

### Requirement: Kepler plans water heater boost with SoC gate

The Kepler solver SHALL schedule water heater boost (binary on/off per slot) only in slots where: (1) the pre-calculated excess PV flag is true, AND (2) projected SoC >= `soc_threshold_percent`. No daily energy budget — the solver's energy balance naturally handles economics, and the executor's thermostat handles physics.

#### Scenario: Excess PV slot with full battery gets water heater boost
- **WHEN** slot 14 has forecast excess PV AND projected SoC >= 95%
- **AND** the excess PV sink is `water_heater_boost`
- **THEN** the MILP SHALL create a boost binary variable for each water heater in that slot
- **AND** boost SHALL NOT appear in slots without forecast excess PV or with SoC < 95%

#### Scenario: No excess PV means no boost
- **WHEN** there are zero excess PV slots across the horizon
- **AND** the excess PV sink is `water_heater_boost`
- **THEN** no boost slots appear in the schedule output

#### Scenario: Boost disabled when sink is not water_heater_boost
- **WHEN** the excess PV sink is `custom_entity` or `disabled`
- **THEN** no boost variables are created
- **AND** water heaters only get their normal minimum kWh

#### Scenario: Boost shares slot with normal heating
- **WHEN** a water heater already has normal heating scheduled in slot 14
- **AND** slot 14 has excess PV AND SoC >= 95%
- **THEN** the heater SHALL run continuously (already on) and the boost flag SHALL be set

### Requirement: Excess PV reward incentivizes solver over export (same for both sinks)

A configurable `boost_reward_sek_per_kwh` (default 0.5) SHALL be applied identically to both water heater boost and custom entity sinks. For water heater boost, the reward is `reward * boost_var * heater_kw * h`. For custom entity, the reward is `reward * custom_entity_active_var * power_kw * h` where `power_kw` is configurable (default 1.0 kW). The custom entity's power consumption (`custom_entity_active[t] * power_kw * h`) SHALL be added to the energy balance demand side, ensuring the solver makes genuine economic tradeoffs. The reward is subtracted from the objective function, making the solver prefer the chosen sink over export when the reward exceeds the export price.

#### Scenario: Boost activates when reward exceeds export price
- **WHEN** slot 14 has excess PV AND SoC >= 95%
- **AND** export price is 0.5 SEK/kWh
- **AND** boost reward is 1.0 SEK/kWh
- **THEN** the solver SHALL schedule boost for that slot (boost earns more than exporting)

#### Scenario: Export wins when export price exceeds reward
- **WHEN** slot 14 has excess PV AND SoC >= 95%
- **AND** export price is 2.0 SEK/kWh
- **AND** boost reward is 1.0 SEK/kWh
- **THEN** the solver SHALL prefer exporting over boost

### Requirement: Custom entity is a solver variable with reward and SoC gate

When the excess PV sink is `custom_entity`, the solver SHALL create a binary variable `custom_entity_active[t]` per slot, constrained identically to water heater boost: (1) pre-calculated excess PV flag must be true, AND (2) projected SoC >= `soc_threshold_percent`. The reward is sized by a configurable `power_kw` (default 1.0 kW). The custom entity's power consumption SHALL be added to the energy balance demand side: `custom_entity_active[t] * power_kw * h`. This ensures the solver makes genuine economic tradeoffs between exporting and directing energy to the entity. The executor toggles the entity based on the solver's decision, not pre-calculated flags.

#### Scenario: Custom entity activated by solver decision
- **WHEN** slot 14 has excess PV AND SoC >= 95%
- **AND** the excess PV sink is `custom_entity`
- **AND** the reward exceeds the export price
- **THEN** the solver SHALL set `custom_entity_active[14] = 1`
- **AND** the schedule output SHALL include `custom_entity_active: true` for slot 14

#### Scenario: Custom entity NOT activated when battery is low
- **WHEN** slot 14 has excess PV but SoC is 70%
- **AND** the excess PV sink is `custom_entity`
- **THEN** the solver SHALL set `custom_entity_active[14] = 0`
- **AND** the schedule output SHALL include `custom_entity_active: false` for slot 14

#### Scenario: Custom entity skipped when sink is disabled
- **WHEN** the excess PV sink is configured as `disabled`
- **THEN** no custom entity variables are created
- **AND** no custom entity actions are performed by the executor

### Requirement: Schedule output includes water heater boost flag

The schedule output SHALL include a `water_heating_boost` field in each slot indicating which heaters are in boost mode.

#### Scenario: Boost slot in schedule output
- **WHEN** heater A has boost scheduled in slot 14
- **THEN** the slot output SHALL contain `water_heating_boost: {"main_tank": true}`
- **AND** the normal `water_heating_kw` field SHALL include both normal and boost energy

#### Scenario: No boost in slot output
- **WHEN** no heater has boost in slot 8
- **THEN** the slot output SHALL contain `water_heating_boost: {}` or no boost entries

### Requirement: Executor toggles custom entity based on schedule

The executor SHALL toggle a user-configured HA entity on during slots where the schedule indicates `custom_entity_active: true` and off otherwise.

#### Scenario: Custom entity turned on during active slot
- **WHEN** the schedule has `custom_entity_active: true` in slot 14
- **AND** the excess PV sink is configured as `custom_entity`
- **WHEN** executor processes slot 14
- **THEN** the configured entity SHALL be set to `on_value`

#### Scenario: Custom entity turned off during inactive slot
- **WHEN** the schedule has `custom_entity_active: false` in slot 8
- **AND** the excess PV sink is configured as `custom_entity`
- **WHEN** executor processes slot 8
- **THEN** the configured entity SHALL be set to `off_value`

#### Scenario: Custom entity set to off_value on slot failure
- **WHEN** the executor enters `SLOT_FAILURE_FALLBACK`
- **AND** the excess PV sink is configured as `custom_entity`
- **THEN** the configured entity SHALL be set to `off_value`
- **AND** the entity SHALL NOT be left in an active state
