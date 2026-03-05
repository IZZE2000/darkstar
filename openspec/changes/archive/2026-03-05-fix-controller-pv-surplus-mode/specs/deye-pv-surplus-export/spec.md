## Overview

Deye inverters can export excess PV to grid while charging the battery by limiting the maximum charge current in "Zero Export to CT" mode. This enables Darkstar to optimize for price spikes during high PV production, matching the capability of Fronius and Sungrow inverters.

## ADDED Requirements

### Requirement: Deye profile supports PV surplus export while charging

The Deye profile SHALL include `max_charge_current` in the `self_consumption` mode actions to enable limiting PV charging current. When charge current is limited and "Solar Sell" is enabled on the inverter, excess PV beyond the charge limit SHALL be exported to grid.

#### Scenario: PV surplus export during high production

- **GIVEN** Deye inverter with "Solar Sell" toggle ON
- **WHEN** planner outputs `charge_kw=3.5, export_kw=5.5, discharge_kw=0` (10kW PV, 1kW load)
- **THEN** controller selects `self_consumption` mode
- **THEN** `max_charge_current` is set to limit charging to ~73A (3.5kW)
- **THEN** excess 5.5kW PV exports to grid

#### Scenario: Charge limit respects battery capacity

- **GIVEN** planner outputs `charge_kw=7.0` but battery max charge current is 100A
- **WHEN** controller calculates charge_value
- **THEN** charge_value is clamped to 100A (max charge current limit)
- **THEN** inverter charges at 100A, any remaining PV exports if Solar Sell is ON

#### Scenario: Solar Sell OFF prevents export

- **GIVEN** Deye inverter with "Solar Sell" toggle OFF
- **WHEN** planner outputs `charge_kw=3.5, export_kw=5.5, discharge_kw=0`
- **THEN** controller selects `self_consumption` mode with limited charge current
- **THEN** excess PV is curtailed (not exported)
- **NOTE**: This is suboptimal but safe. Users should enable Solar Sell for export capability.

### Requirement: Profile documents Solar Sell requirement

The Deye profile SHALL document in comments that "Solar Sell" toggle must be ON for PV surplus export to work. The toggle is ON by default on Deye inverters.

#### Scenario: User reads profile documentation

- **GIVEN** user opens `profiles/deye.yaml`
- **WHEN** user reads the `self_consumption` mode comments
- **THEN** user sees comment explaining Solar Sell requirement
- **THEN** user understands that excess PV will export when charge is limited
