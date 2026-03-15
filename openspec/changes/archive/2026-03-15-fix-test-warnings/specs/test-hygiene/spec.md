## ADDED Requirements

### Requirement: aiosqlite Engine Cleanup

The system SHALL ensure that any test creating an aiosqlite-backed component (such as `LearningStore`) calls the appropriate cleanup method before the test event loop closes.

#### Scenario: LearningStore cleanup in async test
- **WHEN** a test creates a `LearningStore` instance with `:memory:` or file-based SQLite
- **THEN** the test calls `await store.close()` in a `finally` block to ensure the background connection thread terminates before the event loop closes.

#### Scenario: pytest-asyncio fixture uses yield for teardown
- **WHEN** a `@pytest_asyncio.fixture` creates a `LearningStore` or `LearningEngine`
- **THEN** the fixture uses `yield` (not `return`) so that `await store.close()` runs in the teardown phase before the event loop closes.

#### Scenario: Event loop teardown without warnings
- **WHEN** pytest-asyncio closes the event loop after a test that used aiosqlite
- **THEN** no `RuntimeError: Event loop is closed` or `PytestUnhandledThreadExceptionWarning` is raised.

### Requirement: Live Service Isolation in API Tests

API tests SHALL NOT start real background services (executor engine, HA WebSocket client) that connect to live external systems.

#### Scenario: No real executor during API tests
- **WHEN** an API test creates a `TestClient` that triggers the FastAPI lifespan
- **THEN** `get_executor_instance()` returns `None` so no `ExecutorEngine`, `HAClient`, or `aiohttp.ClientSession` is created, and no aiohttp shutdown noise appears after the test run.

#### Scenario: No real HA WebSocket during API tests
- **WHEN** an API test creates a `TestClient` that triggers the FastAPI lifespan
- **THEN** `start_ha_socket_client()` is a no-op so no daemon thread connects to the live HA instance, preventing `RuntimeWarning: coroutine was never awaited` from cross-thread event-loop interactions.

### Requirement: Meaningful Async Declarations

The system SHALL NOT declare functions as `async` unless they perform async operations (use `await`).

#### Scenario: Synchronous function declaration
- **WHEN** a function performs only synchronous operations (file I/O, dict manipulation, etc.)
- **THEN** it is declared as a regular `def` function, not `async def`.

#### Scenario: Test markers match function type
- **WHEN** a test only calls synchronous functions
- **THEN** it does not use `@pytest.mark.asyncio`.

#### Scenario: No unawaited coroutine warnings
- **WHEN** pytest runs the full test suite
- **THEN** no `RuntimeWarning: coroutine was never awaited` is raised.
