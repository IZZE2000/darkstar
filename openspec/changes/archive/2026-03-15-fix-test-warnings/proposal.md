## Why

The test suite has 3 warnings (seen via `./scripts/lint.sh`) that create noise and reduce developer confidence. Two are `aiosqlite` event-loop warnings caused by test fixtures that create real database connections without proper cleanup. One is a `RuntimeWarning: coroutine was never awaited` caused by an `AsyncMock` leaking an unawaited coroutine across test boundaries.

## What Changes

- Fix `DeprecationWarning: There is no current event loop` (1x, order-dependent): Both `test_api_learning_status.py` and `test_api_learning_train.py` share an identical `client` fixture that triggers FastAPI lifespan, which synchronously instantiates a real `LearningStore`. Patch `backend.main.LearningStore` in both `client` fixtures to prevent the real aiosqlite engine from initialising in a sync context.
- Fix `PytestUnhandledThreadExceptionWarning: RuntimeError: Event loop is closed` (1x): `TestRecorderSpikeValidation::test_spike_values_zeroed_before_storage` creates a real `LearningStore(":memory:", tz)` but never closes it. Its aiosqlite background thread fires after the event loop closes, showing up as a warning on the *next* test (`test_valid_values_preserved_in_recorder`). Add `await store.close()` in a `try/finally` block.
- Fix `RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited` (1x): `test_ev_charging_replan.py::test_trigger_ev_replan_uses_run_coroutine_threadsafe` mocks `asyncio.run_coroutine_threadsafe`, so the coroutine produced by `AsyncMock(trigger_now)` is passed to the mock but never awaited. The orphaned coroutine is detected by garbage collection during the next test. Explicitly close the leaked coroutine after the assertion.

## Capabilities

### New Capabilities

None - this is a maintenance fix.

### Modified Capabilities

- `test-hygiene`: Extend the "Guaranteed Thread Safety in Tests" requirement to explicitly cover:
  - aiosqlite `AsyncEngine` disposal before event loop teardown
  - Closing unawaited coroutines created by `AsyncMock` when the real consumer (e.g. `asyncio.run_coroutine_threadsafe`) is mocked out

## Impact

- **Tests**: `tests/api/test_api_learning_status.py`, `tests/api/test_api_learning_train.py`, `tests/backend/test_recorder_deltas.py`, `tests/ev/test_ev_charging_replan.py`
- **CI**: Cleaner test output with zero warnings
