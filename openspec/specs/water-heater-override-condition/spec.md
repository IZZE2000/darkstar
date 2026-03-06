## Purpose

The override evaluator must respect the system's water heater configuration when determining whether to trigger water heater-related override actions.

## Requirements

### Requirement: Override evaluator respects water heater configuration

The override evaluator SHALL check the `has_water_heater` flag before attempting to control water heater temperature.

#### Scenario: EXCESS_PV_HEATING skipped when no water heater
- **GIVEN** system configuration has `has_water_heater=false`
- **AND** excess PV power exceeds threshold
- **AND** battery SoC is at or above 95%
- **WHEN** override evaluator evaluates system state
- **THEN** no `EXCESS_PV_HEATING` override is triggered

#### Scenario: EXCESS_PV_HEATING triggers when water heater exists
- **GIVEN** system configuration has `has_water_heater=true`
- **AND** excess PV power exceeds threshold
- **AND** battery SoC is at or above 95%
- **WHEN** override evaluator evaluates system state
- **THEN** `EXCESS_PV_HEATING` override is triggered with `water_temp` action

### Requirement: Slot failure fallback excludes water temp when no water heater

The slot failure fallback override SHALL NOT include `water_temp` action when no water heater is configured.

#### Scenario: SLOT_FAILURE_FALLBACK without water heater
- **GIVEN** system configuration has `has_water_heater=false`
- **AND** no valid slot plan exists
- **WHEN** override evaluator evaluates system state
- **THEN** `SLOT_FAILURE_FALLBACK` override is triggered
- **AND** actions do NOT include `water_temp`

#### Scenario: SLOT_FAILURE_FALLBACK with water heater
- **GIVEN** system configuration has `has_water_heater=true`
- **AND** no valid slot plan exists
- **WHEN** override evaluator evaluates system state
- **THEN** `SLOT_FAILURE_FALLBACK` override is triggered
- **AND** actions include `water_temp` set to off temperature
