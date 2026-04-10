## MODIFIED Requirements

### Requirement: End-of-Horizon SoC Target acts as a Minimum Floor (Safety Floor)
The solver SHALL enforce the end-of-horizon `target_soc` constraint solely as a minimum floor. It SHALL penalize the solver heavily if the final State of Charge (SoC) is *below* the target (`target_under_violation`). The solver SHALL NOT apply any penalty (`target_over_violation`) if the final SoC exceeds the target, allowing the system to naturally preserve excess free or cheap energy beyond the minimum safety requirement.

The safety floor calculation SHALL use **temporal (per-slot) deficit** instead of aggregate deficit ratio. For each forecast slot, the system SHALL compute `max(0, load_forecast - pv_forecast)` and sum these values to determine the total energy the battery must provide when PV is unavailable. This temporal deficit SHALL replace the previous `(total_load - total_pv) / total_load` aggregate ratio.

The safety floor calculation SHALL look **beyond the price horizon** by using extended load/PV forecast data for a 24h window starting from where the price data ends. When extended forecast data is unavailable, the system SHALL fall back to using only the available horizon and log a warning.

The safety floor SHALL incorporate two risk-based mechanisms:
1. A **risk margin** applied to the temporal deficit (higher risk appetite = lower margin, trusting the forecast more)
2. A **minimum floor** per risk level as a percentage of battery capacity above min_soc, ensuring the floor never collapses to min_soc regardless of forecast conditions

The existing `max_safety_buffer_pct` cap SHALL still apply to prevent the floor from exceeding reasonable levels.

#### Scenario: Excess Solar Energy at End of Horizon
- **WHEN** the battery receives abundant solar energy and covering all loads leaves the end-of-horizon SoC higher than the calculated Safety Floor target
- **THEN** the solver finishes the horizon with the high SoC without attempting to force-dump the energy into the grid to hit the target

#### Scenario: Spring day with aggregate PV surplus but overnight deficit
- **WHEN** total PV forecast over the horizon exceeds total load forecast (aggregate surplus)
- **AND** evening/night slots have load but zero PV (temporal deficit exists)
- **THEN** the safety floor SHALL reflect the temporal deficit (not zero)
- **AND** the risk appetite setting SHALL meaningfully scale the floor

#### Scenario: Midday planning with short price horizon
- **WHEN** planning occurs at midday and price data only extends to midnight (~11.5h horizon)
- **AND** load/PV forecasts extend beyond midnight
- **THEN** the safety floor SHALL use the extended forecast data for the 24h window beyond midnight to account for tomorrow's overnight energy needs

#### Scenario: Price horizon expands after 13:00
- **WHEN** tomorrow's prices arrive at 13:00 and the price horizon extends to tomorrow midnight
- **THEN** the safety floor look-ahead window SHALL shift to cover the 24h beyond tomorrow midnight
- **AND** the MILP can now directly optimize the previously-blind overnight period

#### Scenario: Risk level 3 neutral user in spring
- **GIVEN** risk_appetite = 3, min_soc = 12%, battery capacity = 34.2 kWh
- **WHEN** the temporal deficit beyond the price horizon is approximately 15 kWh (overnight load)
- **THEN** the safety floor SHALL be significantly above min_soc (approximately 20-35% depending on margin and minimum floor)

#### Scenario: Risk level 5 gambler with PV surplus
- **GIVEN** risk_appetite = 5
- **WHEN** temporal deficit beyond the price horizon is calculated
- **THEN** the safety floor SHALL equal min_soc (0% margin, 0% minimum floor)

#### Scenario: Extended forecast data unavailable
- **WHEN** load/PV forecast data does not extend beyond the price horizon
- **THEN** the system SHALL log a warning
- **AND** the safety floor SHALL use only the available horizon data with the minimum floor per risk level as baseline

#### Scenario: Max safety buffer cap applies
- **WHEN** the calculated safety floor (temporal deficit reserve + weather buffer + minimum floor) exceeds `max_safety_buffer_pct` of battery capacity above min_soc
- **THEN** the safety floor SHALL be capped at min_soc + (max_safety_buffer_pct * capacity)

## ADDED Requirements

### Requirement: Adapter builds per-device water heater configs
The planner adapter SHALL replace `_aggregate_water_heaters()` with a per-device config builder that creates a `WaterHeaterInput` for each enabled water heater from the `water_heaters[]` config array. The adapter SHALL NOT aggregate power, daily minimums, or timing settings across heaters.

#### Scenario: Two enabled heaters produce two WaterHeaterInput objects
- **WHEN** `water_heaters[]` contains two entries with `enabled: true`
- **THEN** the adapter SHALL create two `WaterHeaterInput` objects
- **AND** each SHALL have its own `power_kw`, `min_kwh_per_day`, `max_hours_between_heating`, and `min_spacing_hours`

#### Scenario: Global settings passed alongside per-device list
- **WHEN** the adapter builds KeplerConfig
- **THEN** global water settings (comfort penalties, block penalties, reliability penalty, deferral hours, max block hours) SHALL remain as scalar fields on KeplerConfig
- **AND** per-device settings SHALL be in the `water_heaters` list

#### Scenario: No enabled heaters produces empty list
- **WHEN** no water heaters have `enabled: true`
- **THEN** `KeplerConfig.water_heaters` SHALL be an empty list
- **AND** water heating SHALL be disabled in the solver

### Requirement: Pipeline builds per-device mid-block locking
The pipeline SHALL detect mid-block heating state per water heater independently. For each heater currently in an active heating block (detected via power sensor), the pipeline SHALL set `force_on_slots` on that heater's `WaterHeaterInput`.

#### Scenario: One heater mid-block, another idle
- **WHEN** heater A's power sensor shows active heating and heater B's power sensor shows idle
- **THEN** heater A's `WaterHeaterInput.force_on_slots` SHALL contain the remaining block slot indices
- **AND** heater B's `WaterHeaterInput.force_on_slots` SHALL be None or empty

#### Scenario: No heaters mid-block
- **WHEN** no heater power sensors show active heating
- **THEN** all heaters' `force_on_slots` SHALL be None or empty

### Requirement: Pipeline tracks per-device today's heated energy
The pipeline SHALL calculate `heated_today_kwh` per water heater from recorder data or sensor state. Each heater's `WaterHeaterInput.heated_today_kwh` SHALL reflect only that heater's contribution.

#### Scenario: Two heaters with different today progress
- **WHEN** heater A has heated 4.0 kWh today and heater B has heated 2.0 kWh today
- **THEN** heater A's `heated_today_kwh` SHALL be 4.0
- **AND** heater B's `heated_today_kwh` SHALL be 2.0
