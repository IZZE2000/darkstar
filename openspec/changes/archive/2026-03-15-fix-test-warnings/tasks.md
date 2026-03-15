## 1. Fix DeprecationWarning: There is no current event loop (API test fixtures)

Both `test_api_learning_status.py` and `test_api_learning_train.py` share an identical `client` fixture that triggers real `LearningStore` initialisation. Patch `backend.main.LearningStore` in both.

- [x] 1.1 In `tests/api/test_api_learning_status.py`, update the `client` fixture to patch `backend.main.LearningStore` with `MagicMock()` so the real aiosqlite engine is never created during lifespan
- [x] 1.2 In `tests/api/test_api_learning_train.py`, apply the same patch to its `client` fixture
- [x] 1.3 Run both test files individually and confirm the DeprecationWarning is gone

## 2. Fix PytestUnhandledThreadExceptionWarning: RuntimeError: Event loop is closed

`test_spike_values_zeroed_before_storage` creates a real `LearningStore` but never closes it, causing the aiosqlite background thread to crash when the event loop closes.

- [x] 2.1 In `tests/backend/test_recorder_deltas.py::TestRecorderSpikeValidation::test_spike_values_zeroed_before_storage` (around line 494), wrap `store = LearningStore(":memory:", tz)` and `await store.ensure_wal_mode()` in a `try/finally` block with `await store.close()` in the `finally`, encompassing the full test body that uses `store`
- [x] 2.2 Run `tests/backend/test_recorder_deltas.py` in isolation and confirm the `PytestUnhandledThreadExceptionWarning` is gone

## 3. Fix RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited

`test_trigger_ev_replan_uses_run_coroutine_threadsafe` creates an `AsyncMock` for `trigger_now` whose produced coroutine is passed to the mocked `run_coroutine_threadsafe` and never consumed.

- [x] 3.1 In `tests/ev/test_ev_charging_replan.py::TestEVReplanAsyncDispatch::test_trigger_ev_replan_uses_run_coroutine_threadsafe`, after calling `client._trigger_ev_replan()` and before the end of the `with patch("asyncio.run_coroutine_threadsafe")` block, retrieve and close the leaked coroutine:
  ```python
  # Close the coroutine passed to run_coroutine_threadsafe (it was never consumed because the mock intercepted it)
  leaked_coro = mock_run_threadsafe.call_args[0][0]
  leaked_coro.close()
  ```
- [x] 3.2 Run `tests/ev/test_ev_charging_replan.py` followed by `tests/ev/test_ev_deadline_solver.py` and confirm the RuntimeWarning is gone

## 4. Fix additional LearningStore/aiohttp leaks discovered during audit

Audit of all test files revealed two more resource-management issues.

- [x] 4.1 In `tests/ml/test_learning_engine.py`, change the `learning_engine` pytest-asyncio fixture from `return engine` to `yield engine` followed by `await engine.store.close()` in a teardown block, so the aiosqlite engine is properly closed after each test that uses the fixture
- [x] 4.2 In `tests/api/conftest.py`, add two patches to the existing `prevent_real_learning_engine` autouse fixture:
  - `patch("backend.main.get_executor_instance", return_value=None)` — prevents the real `ExecutorEngine` (and its `HAClient` aiohttp session) from starting during API tests. Must patch `backend.main` (not the origin module) because `main.py` does `from backend.api.routers.executor import get_executor_instance` at module level.
  - `patch("backend.ha_socket.start_ha_socket_client")` — prevents the real HA WebSocket daemon thread from connecting to the live HA instance. Without this, the thread can outlive the test's event loop and emit `RuntimeWarning: coroutine 'SchedulerService.trigger_now' was never awaited` when the loop closes before the thread finishes processing incoming state updates.

## 5. Verification

- [x] 5.1 Run `uv run python -m pytest -q` and confirm 661 passed, 1 skipped, **0 warnings**, no `--- Logging error ---` aiohttp shutdown noise
- [x] 5.2 Confirm API tests now complete in ~4s (previously ~15s) due to the executor and HA socket no longer starting real background threads
