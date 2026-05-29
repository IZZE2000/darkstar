## ADDED Requirements

### Requirement: HA WebSocket client has a stop method

`HAWebSocketClient` SHALL have a `stop()` method that sets `self.running = False`, causing the `connect()` loop to exit. A module-level `stop_ha_socket_client()` function SHALL call this on the global `_ha_client` instance.

#### Scenario: stop() causes connect loop to exit
- **WHEN** `stop()` is called on a running `HAWebSocketClient`
- **THEN** `self.running` is set to `False`
- **AND THEN** the `connect()` while loop exits on its next iteration
- **AND THEN** the daemon thread completes

#### Scenario: stop() on already-stopped client is a no-op
- **WHEN** `stop()` is called on a client that is already stopped
- **THEN** no error is raised

### Requirement: FastAPI lifespan shuts down the WebSocket client

The FastAPI lifespan shutdown in `backend/main.py` SHALL call `stop_ha_socket_client()` alongside the existing executor, scheduler, and recorder shutdown calls.

#### Scenario: Shutdown stops WebSocket client
- **WHEN** the FastAPI lifespan shutdown runs
- **THEN** `stop_ha_socket_client()` is called
- **AND THEN** the WebSocket client's `running` flag is `False`
