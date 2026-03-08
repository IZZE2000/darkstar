## Context

The system has a main `asyncio` event loop running the FastAPI server and WebSocket connections. In some instances (particularly beta users with DNS problems), this event loop is completely blocked for long periods.
1. `KeplerSolver.solve` is an intensive MILP calculation that takes ~30 seconds, and it is currently called synchronously in `planner/pipeline.py`.
2. The weather fetching in `ml/weather.py` uses the synchronous `requests` library, which blocks for 5 seconds when DNS resolution fails.
3. Health checking in `backend/health.py` iterates over ~15 Home Assistant entities sequentially. When DNS fails, each takes its full 5-second timeout, amounting to ~75 seconds of blocking the health check function itself.

The Docker container has a `HEALTHCHECK` with a 10s timeout. If the `/api/health` endpoint does not respond in time, the container is killed and restarted by the HA Supervisor watchdog, leading to a crash loop.

## Goals / Non-Goals

**Goals:**
- Unblock the main `asyncio` event loop from long-running synchronous code (both CPU-bound and I/O-bound).
- Ensure the `/api/health` endpoint always responds within a predictable timeframe, even when network requests fail.
- Adjust Docker health check parameters to be more forgiving under high system load.
- Fail fast on external API calls to avoid planner stalls.

**Non-Goals:**
- Completely rewriting the Nordpool fetch mechanism.
- Moving the planner to a separate process/worker (e.g., Celery). We will keep it in-process for simplicity (KISS), but execute it in a thread.

## Decisions

### 1. Run Kepler in a Thread
- **Decision**: Wrap the `solver.solve` call in `planner/pipeline.py` with `asyncio.to_thread()`.
- **Rationale**: `KeplerSolver.solve` is a pure, CPU-bound mathematical optimization that can safely execute in a separate thread. This prevents the ~30s execution from halting the `asyncio` event loop.

### 2. Async Weather Fetching
- **Decision**: Add an `async_get_weather_series` coroutine in `ml/weather.py` that wraps the existing synchronous `get_weather_series` via `asyncio.to_thread`. The synchronous version remains intact. Update `generate_forward_slots` in `ml/forward.py`, `predict_corrections` / `_apply_corrections_forward` in `ml/corrector.py`, and `get_all_input_data` in `inputs.py` to `await` the new wrapper.
- **Rationale**: Keeps the event loop non-blocking without cascading into sync callers (`ml/train.py`, `ml/evaluate.py`, `ml/api.py`) that run in background threads and do not need to change. No new dependency (`httpx`) is required in `weather.py`. This mirrors the established `to_thread` pattern already used for Nordpool.

### 3. Concurrent Health Checks with Timeout
- **Decision**: Refactor `HealthChecker.check_entities` to use `asyncio.gather()` for checking all entities concurrently. Wrap `HealthChecker.check_all()` with `asyncio.wait_for(timeout=15.0)`.
- **Rationale**: Reduces the worst-case execution time from ~75s to ~5s. The global timeout ensures the health check returns (even if marked unhealthy) before the Docker health check timeout kills the container.

### 4. Fail-Fast Nordpool Fetching
- **Decision**: In `inputs.py`, wrap each `asyncio.to_thread(prices_client.fetch, ...)` call with `asyncio.wait_for(..., timeout=10.0)`. Catch `asyncio.TimeoutError` and return empty data gracefully.
- **Rationale**: The `asyncio.to_thread` wrapper already exists. The missing piece is a hard timeout: without it, the background thread can be held for ~120s (urllib3 retry) and the async caller waits equally long. `wait_for` lets the caller proceed immediately while the stalled thread runs to completion silently in the thread pool, which is an acceptable trade-off for a read-only fetch.

### 5. Relax Docker Health Check Timeout
- **Decision**: Change the `HEALTHCHECK` timeout in `Dockerfile` from `10s` to `20s`.
- **Rationale**: Provides more breathing room for the system under heavy load while remaining responsive enough to detect genuine deadlocks.

## Risks / Trade-offs

- **Risk: `asyncio.to_thread` creates thread pool starvation.**
  - *Mitigation*: The default ThreadPoolExecutor size is `min(32, os.cpu_count() + 4)`. We only run one planner instance at a time (prevented by the lock in `planner_service.py`), so this is highly unlikely to cause starvation.
- **Risk: Converting `get_weather_series` callers to async may cascade unexpectedly.**
  - *Mitigation*: The `to_thread` wrapper approach is additive. Only async callers (`forward.py`, `corrector.py`, `inputs.py`) import `async_get_weather_series`. Sync callers (`train.py`, `evaluate.py`, `api.py`) continue using the unchanged synchronous version. No test breakage is expected.
