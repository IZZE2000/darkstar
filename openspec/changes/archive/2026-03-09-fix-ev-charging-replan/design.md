## Context

The EV plug-in event arrives over WebSocket in `HAWebSocketClient._handle_state_change()`, a synchronous method running in a dedicated background thread (`HA-WebSocket`) with its own event loop. When an EV is detected as plugged in, `_trigger_ev_replan()` is called synchronously, but it attempts to dispatch a coroutine using `asyncio.create_task()` — which requires an active coroutine context. This raises `RuntimeError: no running event loop`, caught silently by a bare `except Exception`, so the replan never fires.

Additionally, the config lookup in that same function reads from `executor.ev_charger` — a path that no longer exists after the ARC15 migration moved EV configuration to `ev_chargers[]`. And in `executor/engine.py`, the EV charger switch is turned on whenever `actual_ev_charging OR scheduled_ev_charging`, meaning a car that starts drawing power for any reason (e.g. its own timer) will be allowed to continue charging uncontrolled.

## Goals / Non-Goals

**Goals:**
- Make the replan actually execute when an EV is plugged in
- Fix the stale config path in `_trigger_ev_replan()`
- Harden the executor so the EV switch is only enabled by a valid schedule slot
- Reduce the WebSocket-vs-REST propagation race by passing WebSocket state into the planner

**Non-Goals:**
- Multi-EV per-charger replan logic (always uses the first enabled EV)
- Changes to the MILP solver or how EV charging slots are structured
- UI changes

## Decisions

### D1 — Use `asyncio.run_coroutine_threadsafe()` for cross-thread dispatch

The WebSocket thread has its own event loop; the scheduler service runs in the main app event loop. `asyncio.run_coroutine_threadsafe(coro, loop)` is the correct cross-thread primitive. The main loop reference must be captured at startup and stored on the singleton client.

**Alternatives considered:**
- `asyncio.create_task()` — requires an active coroutine context; not applicable from a sync method.
- Spawning a new `asyncio.run()` thread — creates an isolated event loop with no access to shared async resources (DB connections, HTTP sessions); rejected.
- Threading queue + consumer — overly complex for a single-fire trigger; rejected.

### D2 — Pass live plug state as an override to `get_initial_state()`

When the replan is triggered by a plug event, we already know the car is plugged in. Rather than having the planner re-fetch from HA REST (which may not have propagated yet), the WebSocket state passes `ev_plugged_in=True` directly via a new optional parameter on `get_initial_state()` and `get_all_input_data()`.

**Alternatives considered:**
- Add a debounce (e.g. sleep 2 s before replan) — fragile, adds latency, doesn't eliminate the race on slow HA instances; rejected.
- Inject state via a module-level cache — creates hidden coupling; rejected.

### D3 — Stricter executor gating: schedule-only

Change `ev_should_charge = scheduled_ev_charging or actual_ev_charging` to `ev_should_charge = scheduled_ev_charging`. The `actual_ev_charging` signal is useful for _source isolation_ (blocking battery discharge when EV is drawing power), but should not be used to _allow_ charging when no schedule says to.

`actual_ev_charging` is kept for the source isolation side-effect (blocking discharge) but removed from the switch-control gate.

**Alternatives considered:**
- Keep OR logic, add a separate "is car plugged in" guard — doesn't prevent the window between plug-in and replan completion; rejected.

## Risks / Trade-offs

- **Risk: Main event loop reference unavailable at init time** → Capture loop via `asyncio.get_event_loop()` at the point `trigger_ev_replan` is called (not at `__init__`), or store it when the WebSocket thread is started from an async context. The scheduler service startup is async, so the loop is available there.
- **Risk: `run_coroutine_threadsafe` future is fire-and-forget** → Log the future result in a callback so errors surface in logs.
- **Risk: Stricter executor gating breaks the "car started charging on its own" fallback** → Intentional; unscheduled charging should not be silently permitted. This is the correct production behaviour.
