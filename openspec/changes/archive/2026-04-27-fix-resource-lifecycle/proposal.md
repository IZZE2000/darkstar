## Why

The executor's async HTTP session, background tasks, and HA WebSocket client are never cleaned up on shutdown, producing noisy `Unclosed client session` warnings in production logs. Beta testers see these errors on every restart.

## What Changes

- Fix the executor's `_async_run_loop` to cancel background tasks and close the aiohttp session in a `finally` block
- Add a `stop()` method to the HA WebSocket client so it can be shut down cleanly
- Wire the WebSocket client shutdown into the FastAPI lifespan in `main.py`

## Capabilities

### New Capabilities
- `ha-websocket`: Clean shutdown of the HA WebSocket client via a `stop()` method called during FastAPI lifespan

### Modified Capabilities
- `executor`: The executor background loop must clean up all async resources (aiohttp session, background tasks) on exit, and background tasks must be cancelled before the session is closed

## Impact

- `executor/engine.py` — `finally` block in `_async_run_loop`
- `backend/ha_socket.py` — add `stop()` method
- `backend/main.py` — call WebSocket client shutdown in lifespan
