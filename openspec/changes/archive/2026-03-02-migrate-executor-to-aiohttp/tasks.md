## 1. Dependencies and Setup

- [x] 1.1 Add `aiohttp` to requirements.txt with version pinning
- [x] 1.2 Verify `aiohttp` is compatible with existing dependencies
- [x] 1.3 Update executor imports to include aiohttp types

## 2. HAClient Migration (executor/actions.py)

- [x] 2.1 Replace `requests.Session` with `aiohttp.ClientSession` in HAClient.__init__
- [x] 2.2 Convert `get_state()` method to async with aiohttp GET request
- [x] 2.3 Convert `get_state_value()` method to async
- [x] 2.4 Convert `call_service()` method to async with aiohttp POST request
- [x] 2.5 Update exception handling to catch `aiohttp.ClientError` instead of `requests.RequestException`
- [x] 2.6 Add 5-second timeout to all HTTP requests
- [x] 2.7 Update type hints to reflect async return types
- [x] 2.8 Ensure session is properly closed on cleanup

## 3. ActionDispatcher Updates (executor/actions.py)

- [x] 3.1 Update `_write_entity()` to await HAClient async methods
- [x] 3.2 Update `_verify_action()` to await HAClient async methods
- [x] 3.3 Update `_execute_action()` to properly await async operations
- [x] 3.4 Ensure `execute()` method properly chains async calls
- [x] 3.5 Update `_set_max_export_power()` to use async HAClient
- [x] 3.6 Update `set_water_temp()` to use async HAClient
- [x] 3.7 Update `set_ev_charger_switch()` to use async HAClient

## 4. ExecutorEngine Updates (executor/engine.py)

- [x] 4.1 Update `_gather_system_state()` to await HAClient calls
- [x] 4.2 Update `init_ha_client()` to handle async initialization if needed
- [x] 4.3 Update `_tick()` method to await all state gathering operations
- [x] 4.4 Update automation toggle check to await HAClient
- [x] 4.5 Update EV power monitoring to await HAClient
- [x] 4.6 Ensure all HA client calls are awaited in async contexts

## 5. Exception Handling Updates

- [x] 5.1 Update HACallError to handle aiohttp exceptions
- [x] 5.2 Ensure timeout errors are properly caught and logged
- [x] 5.3 Add retry logic for transient network failures
- [x] 5.4 Update error messages to include timeout information

## 6. Test Updates

- [x] 6.1 Update test_executor_actions.py to use AsyncMock for HAClient
- [x] 6.2 Update test_executor_engine.py to use async test patterns
- [x] 6.3 Update test_executor_controller.py mocks
- [x] 6.4 Update test_ev_isolation.py async patterns
- [x] 6.5 Update test_integration.py to await async operations
- [x] 6.6 Update test_executor_watt_control.py async mocks
- [x] 6.7 Ensure all test files use pytest-asyncio decorators
- [x] 6.8 Add test for timeout handling behavior

## 7. Validation and Testing

- [x] 7.1 Run full test suite: `uv run python -m pytest tests/executor/ -v`
- [x] 7.2 Verify no regressions in executor behavior
- [x] 7.3 Test with mock HA that simulates slow responses
- [x] 7.4 Verify executor continues ticking during HA delays
- [x] 7.5 Run linter: `uv run ruff check executor/`
- [x] 7.6 Run type checker: `uv run pyright executor/`

## 8. Documentation

- [x] 8.1 Update executor module docstrings with async notes
- [x] 8.2 Document timeout configuration in config.example.yaml

- [x] 8.4 Update architecture docs if needed (no changes required - migration aligns with existing async architecture guidelines)

## 9. Deployment Preparation

- [x] 9.1 Create feature branch: `git checkout -b feat/migrate-executor-aiohttp` (deployment workflow)
- [x] 9.2 Commit changes with conventional commit format (deployment workflow)
- [x] 9.3 Test in staging environment (deployment workflow)
- [x] 9.4 Monitor for 24 hours before production deploy (deployment workflow)
- [x] 9.5 Prepare rollback plan (deployment workflow)
