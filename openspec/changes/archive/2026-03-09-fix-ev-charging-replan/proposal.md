## Why

EV plug-in detection does not trigger a replan: the `_trigger_ev_replan()` function calls `asyncio.create_task()` from a synchronous method on a background thread, raising a `RuntimeError` that is silently swallowed. As a result, the car starts charging immediately on plug-in regardless of electricity price, and no optimal schedule is created until the user manually triggers a replan.

## What Changes

- Fix `_trigger_ev_replan()` to correctly schedule the coroutine into the main event loop via `asyncio.run_coroutine_threadsafe()` instead of `asyncio.create_task()`
- Fix the wrong config path in `_trigger_ev_replan()` that reads `executor.ev_charger` (old path) instead of the ARC15 `ev_chargers[]` array
- Harden executor EV switch logic so charging is only allowed when the schedule explicitly requests it (`scheduled_ev_charging = True`), not when actual power draw is detected without a schedule
- Pass the real-time WebSocket plug state into the planner when triggering replan-on-plugin, eliminating the WebSocket-vs-REST propagation race

## Capabilities

### New Capabilities
- `ev-charging-replan`: Reliable real-time replanning when an EV is plugged in — detects plug event via WebSocket, triggers planner with live state, and produces an optimal charging schedule before the charger switch is opened

### Modified Capabilities
<!-- No existing spec-level capability contracts are being changed -->

## Impact

- `backend/ha_socket.py` — `_trigger_ev_replan()`: asyncio fix + config path fix + passes live plug state
- `executor/engine.py` — `_tick()`: executor EV switch logic stricter (schedule-only gating)
- `planner/pipeline.py` — `generate_schedule()`: accepts optional pre-fetched initial state to avoid REST re-fetch
- `inputs.py` — `get_initial_state()`: accepts optional `override_ev_plugged_in` parameter
