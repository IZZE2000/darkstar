## Why

The executor stopped setting water heater temperature during normal operation after the ARC17 Inverter Profile Redesign. This is a critical regression - users' water heaters are not being controlled by the schedule, leading to stuck temperatures (e.g., stuck at 60°C instead of toggling between 50°C and 60°C as planned).

The regression occurred because the refactor moved all inverter control to profile-driven actions, but water heater control is NOT an inverter function - it's a separate HA entity, similar to EV charger control.

## What Changes

- **Fix**: Add water temperature execution to the main executor tick loop, following the same pattern as EV charger control
- **No breaking changes** - only fixes broken behavior

> **Note**: Water boost (`start_water_boost`) fires via a separate background task, independent of `_tick()`, and is **not** changed by this fix. Boost will still not appear in execution history.

## Capabilities

### New Capabilities

- `water-heater-execution`: Specifies how the executor controls water heater temperature via Home Assistant, including scheduled control and manual boost operations.

### Modified Capabilities

- `water-heater-override-condition`: No spec-level changes, but execution now properly applies the override actions.

## Impact

- `executor/engine.py`: Add water temp execution to `_tick()` after EV charger control
- `executor/actions.py`: `set_water_temp()` already exists and works - just needs to be called
- Execution history will now correctly show water temperature commands
- UI Execution History tab will display water temp changes
