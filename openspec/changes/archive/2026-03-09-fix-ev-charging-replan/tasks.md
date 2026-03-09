## 1. Fix asyncio cross-thread dispatch in `_trigger_ev_replan`

- [x] 1.1 Capture the main event loop reference when the WebSocket client is started (e.g. store as `self._main_loop` via a parameter passed from the async startup context)
- [x] 1.2 Replace `asyncio.create_task(scheduler_service.trigger_now())` with `asyncio.run_coroutine_threadsafe(scheduler_service.trigger_now(), self._main_loop)` and add a done-callback that logs any exception

## 2. Fix stale config path in `_trigger_ev_replan`

- [x] 2.1 Replace `cfg.get("executor", {}).get("ev_charger", {})` with a loop over `cfg.get("ev_chargers", [])` to find the first enabled EV charger
- [x] 2.2 Read `replan_on_plugin` from that charger dict (default `True`); return early if `False`

## 3. Pass live WebSocket plug state to planner on plug-in replan

- [x] 3.1 Add an optional `ev_plugged_in_override: bool | None = None` parameter to `get_initial_state()` in `inputs.py`; if provided, skip the HA REST fetch for `ev_plugged_in` and use the override value instead
- [x] 3.2 Propagate the parameter through `get_all_input_data()` so callers can pass it down
- [x] 3.3 In `_trigger_ev_replan()`, pass `ev_plugged_in=True` into the replan trigger so it reaches `get_initial_state()`

## 4. Harden executor EV switch gating

- [x] 4.1 In `executor/engine.py` `_tick()`, separate the switch-control gate from source isolation: define `ev_should_charge_switch: bool = scheduled_ev_charging` (schedule-only) while keeping `ev_should_charge_block: bool = scheduled_ev_charging or actual_ev_charging` for discharge blocking
- [x] 4.2 Pass `ev_should_charge_switch` to `_control_ev_charger()` instead of the combined `ev_should_charge`
- [x] 4.3 Keep using combined flag for the source isolation block (battery discharge = 0 when EV drawing power)
- [x] 4.4 Update log messages to reflect the new distinction between switch control and source isolation

## 5. Tests

- [x] 5.1 Add unit test: `test_trigger_ev_replan_uses_run_coroutine_threadsafe` — mock `asyncio.run_coroutine_threadsafe` and assert it is called (not `create_task`) when plug-in event fires
- [x] 5.2 Add unit test: `test_trigger_ev_replan_reads_ev_chargers_array` — mock config with `ev_chargers[0].replan_on_plugin = false`; assert trigger does not fire
- [x] 5.3 Add unit test: `test_get_initial_state_override_ev_plugged_in` — pass `ev_plugged_in_override=True`; assert result contains `ev_plugged_in: True` without making a HA REST call for that field
- [x] 5.4 Add unit test: `test_executor_ev_switch_not_opened_without_schedule` — set `scheduled_ev_charging=False`, `actual_ev_charging=True`; assert `_control_ev_charger` is called with `ev_should_charge=False`

## 6. Validation & Lint

- [x] 6.1 Run `./scripts/lint.sh` and fix any failures
