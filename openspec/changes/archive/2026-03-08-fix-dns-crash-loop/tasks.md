## 1. Unblock Event Loop (CPU-bound)

- [x] 1.1 Wrap `KeplerSolver.solve` execution in `asyncio.to_thread` within `planner/pipeline.py`.

## 2. Async Weather Fetching (I/O-bound)

- [x] 2.1 Add `async_get_weather_series` coroutine to `ml/weather.py` that wraps the existing `get_weather_series` via `asyncio.to_thread`. No changes to the synchronous version.
- [x] 2.2 Update `generate_forward_slots` in `ml/forward.py` to `await async_get_weather_series` instead of calling the sync version.
- [x] 2.3 Update `predict_corrections` in `ml/corrector.py` to `await async_get_weather_series`.
  - **Note**: `_apply_corrections_forward` was identified during design but doesn't exist in codebase. The `_apply_corrections_to_db` function in `ml/pipeline.py` doesn't use weather data. Only `predict_corrections` needed updating.
- [x] 2.4 Update `get_all_input_data` in `inputs.py` to `await async_get_weather_series` (via the existing `get_weather_volatility` call path, or by direct awaiting if needed).
- [x] 2.5 Verify `ml/train.py`, `ml/evaluate.py`, and `ml/api.py` are unaffected (they use the sync version from threads).

## 3. Fast and Concurrent Health Checks

- [x] 3.1 Refactor `HealthChecker.check_entities` in `backend/health.py` to use `asyncio.gather` for concurrent execution of HA entity API calls.
- [x] 3.2 Wrap the invocation of `HealthChecker.check_all` inside `get_health_status` in `backend/health.py` with `asyncio.wait_for(..., timeout=15.0)` to ensure a timely response.

## 4. Fail-Fast External APIs & Config

- [x] 4.1 Wrap each existing `asyncio.to_thread(prices_client.fetch, ...)` call inside `get_nordpool_data` in `inputs.py` with `asyncio.wait_for(..., timeout=10.0)`. Catch `asyncio.TimeoutError` and return `[]` gracefully. (Note: `to_thread` already exists — only the timeout wrapper is missing.)
- [x] 4.2 Update the `HEALTHCHECK` command in `Dockerfile` to increase the timeout from `10s` to `20s`.
