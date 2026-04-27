## Context

Three resource lifecycle gaps exist in the backend:

1. **Executor aiohttp session** — The background loop's `HAClient` creates a lazy `aiohttp.ClientSession` that is never closed when the loop exits. Python's GC eventually cleans it up, producing `Unclosed client session` warnings on every shutdown.

2. **Executor background tasks** — Three call sites (`_tick()` resume, water boost, water cancel) create `asyncio.Task`s that use the `HAClient`. On shutdown, these tasks may still be running when the session is closed, causing `RuntimeError: Session is closed`.

3. **HA WebSocket client** — `HAWebSocketClient` runs in a daemon thread with `self.running = True` but no `stop()` method. The FastAPI lifespan shutdown in `main.py` never signals it to stop.

## Goals / Non-Goals

**Goals:**
- Executor background loop cleans up all async resources on every exit path (normal, stop, crash)
- In-flight background tasks are cancelled before the aiohttp session is closed
- HA WebSocket client can be cleanly stopped and is shut down during FastAPI lifespan

**Non-Goals:**
- Changing `HAClient` to use a different HTTP library or async context manager pattern
- Adding lifecycle management to `run_once()` API endpoint — it shares the singleton session and is covered by the background loop cleanup
- Fixing resource leaks in utility scripts (`detect_soc_drops.py`, `repair_soc.py`)

## Decisions

### Decision: `try/finally` with task cancellation in `_async_run_loop`

The `while` loop is wrapped in `try/finally`. The `finally` block:
1. Cancels all tracked `_background_tasks`
2. Awaits their completion with `return_exceptions=True`
3. Closes `ha_client` inside its own `try/except` to prevent masking the original error

This ordering is critical — tasks that reference the session must be cancelled before the session is closed.

### Decision: Add `stop()` method to HAWebSocketClient + module-level `stop_ha_socket_client()`

Add a `stop()` method on `HAWebSocketClient` that sets `self.running = False`. The `connect()` loop already checks this flag at lines 195 and 238 and will exit naturally. Add a module-level `stop_ha_socket_client()` function (matching the existing `start_ha_socket_client()` pattern) that calls `_ha_client.stop()`.

Call it from `main.py` lifespan shutdown, alongside the existing executor/scheduler/recorder shutdown calls.

## Risks / Trade-offs

- **Background task cancellation**: Cancelling tasks mid-flight could lose in-progress water heater or resume actions. Acceptable — shutdown means the system is going down anyway, and these are ephemeral HA calls re-executed on next startup.
- **WebSocket stop latency**: The `connect()` loop may be mid-reconnect with exponential backoff sleep. The `running` flag check is reached within one sleep cycle. The daemon thread fallback ensures the process can still exit promptly.
