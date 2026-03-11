## Why

The PV surplus override (`EXCESS_PV_HEATING`) and slot failure fallback (`SLOT_FAILURE_FALLBACK`) both attempt to control water heater temperature without checking if a water heater is configured. When `has_water_heater=false`, the executor still triggers these overrides, logs misleading messages, and sends notifications about water heating actions that cannot be performed.

## What Changes

- Add `has_water_heater: bool` field to `SystemState` dataclass
- Add conditional check to `EXCESS_PV_HEATING` override evaluation
- Conditionally include `water_temp` action in `SLOT_FAILURE_FALLBACK` only when water heater exists
- Pass `has_water_heater` from executor engine to `SystemState`

## Capabilities

### New Capabilities

- `water-heater-override-condition`: Override logic must respect the `has_water_heater` system configuration flag before attempting to control water heater temperature.

### Modified Capabilities

None.

## Impact

- `executor/override.py` — SystemState dataclass, OverrideEvaluator.evaluate()
- `executor/engine.py` — _gather_system_state() method
- `tests/executor/test_executor_override.py` — New test cases for has_water_heater=false
