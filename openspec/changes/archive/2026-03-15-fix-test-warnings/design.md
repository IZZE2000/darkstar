## Context

Three test warnings remain after previous implementation attempts (verified by `./scripts/lint.sh`):

1. **DeprecationWarning: There is no current event loop (1x, order-dependent):**
   Both `tests/api/test_api_learning_status.py` and `tests/api/test_api_learning_train.py` share an identical `client` fixture that calls `create_app()` and enters a `TestClient` context manager. This triggers the FastAPI lifespan, which synchronously instantiates a real `LearningStore` (via `create_async_engine("sqlite+aiosqlite://...")` from SQLAlchemy/aiosqlite). At that moment no asyncio event loop is running, causing aiosqlite to call `asyncio.get_event_loop()` which is deprecated in Python 3.12. Pytest deduplicates warnings so only one of the two tests appears in output — which one depends on execution order.

2. **PytestUnhandledThreadExceptionWarning: RuntimeError: Event loop is closed (1x):**
   `TestRecorderSpikeValidation::test_spike_values_zeroed_before_storage` (line 494 of `test_recorder_deltas.py`) creates a real `LearningStore(":memory:", tz)` and calls `await store.ensure_wal_mode()`, but never calls `await store.close()`. When pytest-asyncio tears down the event loop after the test, aiosqlite's `_connection_worker_thread` tries to schedule a callback on the now-closed loop, producing the exception. This manifests as a warning on the *next* test (`test_valid_values_preserved_in_recorder`) because garbage collection is lazy.

3. **RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited (1x):**
   `test_ev_charging_replan.py::test_trigger_ev_replan_uses_run_coroutine_threadsafe` sets `mock_scheduler.trigger_now = AsyncMock(...)` and also mocks `asyncio.run_coroutine_threadsafe`. When `client._trigger_ev_replan()` runs, it calls `scheduler_service.trigger_now(...)` which — because it is an `AsyncMock` — returns a coroutine object. That coroutine is passed to the mocked `run_coroutine_threadsafe`, which simply returns a fake `MagicMock` future *without consuming the coroutine*. The coroutine is never awaited. Python's garbage collector detects this during the next test (`test_ev_deadline_solver.py`) when PuLP builds its constraint dict, and issues the warning.

## Goals / Non-Goals

**Goals:**
- Eliminate all 3 remaining test warnings.
- Maintain existing test coverage and assertions unchanged.

**Non-Goals:**
- Refactoring test architecture
- Adding new test coverage
- Changing production behavior

## Decisions

### Decision 1: Patch `LearningStore` in both API test client fixtures

**Chosen**: In the `client` fixture of `test_api_learning_status.py` and `test_api_learning_train.py`, patch `backend.main.LearningStore` with `MagicMock()` before the `TestClient` context manager runs lifespan. This prevents aiosqlite from initialising in a sync context.

**Rationale**: The API tests under test do not exercise the learning store — they mock the learning endpoints directly. The fixture only needs a functional FastAPI app, not a real database.

**Alternative considered**: Make `LearningStore` initialisation lazy (defer to first request). Rejected because it requires production code changes and the existing pattern of mocking at the fixture level is simpler.

### Decision 2: Close real `LearningStore` in `test_spike_values_zeroed_before_storage`

**Chosen**: Wrap `store = LearningStore(":memory:", tz)` / `await store.ensure_wal_mode()` in a `try/finally` block with `await store.close()` in the `finally` clause, scoping the entire test body that relies on `store` inside the `try`.

**Rationale**: Explicit cleanup at the test level is the established pattern in this codebase (matching `test_pipeline_spike_filtering.py`). Ensures the aiosqlite background thread is stopped before the event loop closes.

### Decision 3: Close leaked coroutine after `_trigger_ev_replan` call

**Chosen**: In `test_trigger_ev_replan_uses_run_coroutine_threadsafe`, after calling `client._trigger_ev_replan()`, retrieve the coroutine that was passed to the mocked `run_coroutine_threadsafe` and call `.close()` on it.

```python
# Close the coroutine that run_coroutine_threadsafe received but never consumed
leaked_coro = mock_run_threadsafe.call_args[0][0]
leaked_coro.close()
```

**Rationale**: The test correctly verifies that `run_coroutine_threadsafe` is called (not `create_task`), but the mock means the coroutine is never actually scheduled. Explicitly closing it prevents Python from emitting the "never awaited" warning during GC.

**Alternative considered**: Use a regular `MagicMock` instead of `AsyncMock` for `trigger_now` (since the test only checks that `run_coroutine_threadsafe` is called, not that the coroutine itself runs). Acceptable but changes the nature of the mock; `.close()` is more precise.

### Decision 4: Patch executor and HA socket in API test autouse fixture

**Chosen**: In `tests/api/conftest.py`, add two patches to the existing `prevent_real_learning_engine` autouse fixture:
- `patch("backend.main.get_executor_instance", return_value=None)` — prevents a real `ExecutorEngine` from starting, which would read `secrets.yaml`, create an `HAClient`, open a live `aiohttp.ClientSession` to Home Assistant, and leave it unclosed at interpreter shutdown (producing `--- Logging error --- Unclosed client session` noise after the test run).
- `patch("backend.ha_socket.start_ha_socket_client")` — prevents the HA WebSocket daemon thread from connecting to the live HA instance. Without this, the thread can outlive the test's event loop and emit `RuntimeWarning: coroutine 'SchedulerService.trigger_now' was never awaited` when the loop closes while the thread is still processing incoming state updates.

**Critical detail — patch target**: `backend.main` does `from backend.api.routers.executor import get_executor_instance` at module level, binding a local name. Patching the origin module (`backend.api.routers.executor`) would miss this pre-imported reference. The patch must target `backend.main.get_executor_instance` — the name actually used in the lifespan. `start_ha_socket_client` is imported locally inside the lifespan function, so patching `backend.ha_socket.start_ha_socket_client` is sufficient.

**Side effect**: API tests now complete in ~4 s instead of ~15 s because the real executor background thread and HA WebSocket connection are never started.

**Rationale**: API unit tests exercise route logic, not infrastructure services. Starting a real executor or HA socket in this context couples tests to live external state, slows them down, and produces hard-to-diagnose shutdown noise.

### Decision 5: Fix `learning_engine` fixture teardown in `test_learning_engine.py`

**Chosen**: Change the `@pytest_asyncio.fixture async def learning_engine` from `return engine` to `yield engine` followed by `await engine.store.close()`.

**Rationale**: `return` in a pytest-asyncio fixture exits immediately with no teardown path — `engine.store.close()` is never called, leaving the aiosqlite background thread alive past the event loop lifetime. Changing to `yield` gives the fixture a proper teardown phase, matching the pattern used throughout the rest of the test suite (`test_store_plan_mapping.py`, `test_reflex.py`, `test_system_state.py`).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| `LearningStore` mock in fixture hides real initialisation bugs | Acceptable — API unit tests are not the right place to test store initialisation |
| `.close()` on coroutine is unusual pattern | Well-documented Python behaviour; add inline comment explaining why |
| Warning deduplication may hide regressions | Run `./scripts/lint.sh` (not just `pytest`) which reveals all three warnings |

## Migration Plan

1. Patch `LearningStore` in the `client` fixture of both API test files.
2. Add `try/finally` with `await store.close()` in `test_spike_values_zeroed_before_storage`.
3. Close leaked coroutine in `test_trigger_ev_replan_uses_run_coroutine_threadsafe`.
4. Run `./scripts/lint.sh` to verify zero warnings and zero failures.
