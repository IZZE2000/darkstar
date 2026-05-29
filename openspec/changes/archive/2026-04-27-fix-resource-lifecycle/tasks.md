## 1. Executor Background Loop Cleanup

- [x] 1.1 In `executor/engine.py`, wrap the `while` loop in `_async_run_loop` with `try/finally`
- [x] 1.2 In the `finally` block, cancel all `_background_tasks` and await their completion with `return_exceptions=True`
- [x] 1.3 Close `ha_client` inside a nested `try/except` to prevent masking original exceptions

## 2. HA WebSocket Client Shutdown

- [x] 2.1 In `backend/ha_socket.py`, add a `stop()` method to `HAWebSocketClient` that sets `self.running = False`
- [x] 2.2 In `backend/ha_socket.py`, add a module-level `stop_ha_socket_client()` function that calls `_ha_client.stop()` on the global instance
- [x] 2.3 In `backend/main.py` lifespan shutdown, add a call to `stop_ha_socket_client()` after the executor/scheduler/recorder shutdown

## 3. Verification

- [x] 3.1 Start and stop Darkstar locally; verify no `Unclosed client session` or `Unclosed connector` warnings in logs
- [x] 3.2 Verify WebSocket client shuts down cleanly (no dangling thread warnings)
