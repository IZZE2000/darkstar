## 1. Core Implementation

- [x] 1.1 Add water temperature execution to `_tick()` in `executor/engine.py`
  - Place **inside** the existing `if self.dispatcher:` block (line ~1262), **before** `dispatcher.execute()` is called
  - Condition on `self._has_water_heater and self.config.water_heater.target_entity`
  - Call `await self.dispatcher.set_water_temp(decision.water_temp)`
  - Append result to `action_results`

> **Out of scope**: Water boost logging to execution history. Boost fires via a separate `create_task()` in `start_water_boost()` and is not touched by this change.

## 2. Testing

- [x] 2.1 Add unit test in `tests/executor/test_executor_engine.py`
  - Mock dispatcher and assert `set_water_temp` is called during `_tick()` when `has_water_heater=True`
  - Assert it is NOT called when `has_water_heater=False`

- [x] 2.2 Manual testing with real Home Assistant
  - Verify water temp is set when `water_kw > 0` in schedule
  - Verify water temp is set to off when `water_kw = 0`
  - Verify action appears in Execution History UI
  - Verify shadow mode skips the actual HA call

- [x] 2.3 Run lint and type checks
  - Run `./scripts/lint.sh` and fix any issues
