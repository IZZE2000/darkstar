## Why

The Darkstar HA add-on is currently entering a restart loop ("crashing") when beta users experience DNS or temporary networking issues. The Supervisor watchdog kills the container because the main `asyncio` event loop is blocked by synchronous CPU-bound operations (Kepler MILP solver, ~30s) and synchronous network calls (`requests.get` to Open-Meteo, ~5s per timeout) preventing the FastAPI server from responding to `/api/health` and WebSocket pings within the 10-15s required thresholds. Furthermore, health check entities are polled sequentially with 5s timeouts, further delaying the health endpoint when networking is degraded.

## What Changes

- Modify `HealthChecker.check_entities` to poll all Home Assistant entities concurrently using `asyncio.gather()`, drastically reducing the worst-case health check execution time.
- Wrap the entire `check_all()` execution in `asyncio.wait_for()` with a 15s timeout to guarantee a response before Docker kills the container.
- Wrap the synchronous Kepler MILP solver execution (`KeplerSolver.solve`) in `asyncio.to_thread()` in `planner/pipeline.py` to prevent event loop blocking.
- Add an `async_get_weather_series` wrapper in `ml/weather.py` that delegates to the existing synchronous `get_weather_series` via `asyncio.to_thread`. Update only the async callers (`generate_forward_slots` in `ml/forward.py`, `predict_corrections` in `ml/corrector.py`, `get_all_input_data` in `inputs.py`) to `await` the new wrapper. The synchronous version remains unchanged for sync callers (`ml/train.py`, `ml/evaluate.py`, `ml/api.py`).
- Add `asyncio.wait_for(..., timeout=10.0)` around the existing `asyncio.to_thread` calls for `prices_client.fetch` in `inputs.py`. The `to_thread` wrapper already exists; the missing piece is a hard timeout to discard stalled threads quickly.
- Increase the Dockerfile `HEALTHCHECK` timeout from `10s` to `20s` to provide more resilience against normal heavy loads.

## Capabilities

### New Capabilities

- `dns-resiliency`: Ensures core system stability and fail-fast behavior when DNS or external network connectivity is lost.

### Modified Capabilities

- `open-meteo-pv-forecast`: Migrates data fetching to be non-blocking.

## Impact

- **Code:** `backend/health.py`, `planner/pipeline.py`, `ml/weather.py` (new async wrapper only), `ml/forward.py`, `ml/corrector.py`, `inputs.py`, `Dockerfile`.
- **System Stability:** Significant improvement; the process should no longer be killed by HA Supervisor during network outages.
- **Performance:** Health check latency under degraded conditions will drop from ~75s to <5s. The main event loop will remain responsive during the ~30s planner optimization cycle.
