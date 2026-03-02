## Context

The Darkstar executor is responsible for reading the current schedule from `schedule.json`, gathering system state from Home Assistant, evaluating overrides, making controller decisions, and executing actions. Currently, it uses the synchronous `requests` library for all HTTP communication with Home Assistant.

When a Fronius inverter becomes unresponsive (common with Modbus/TCP communication issues), Home Assistant's API may hang when querying entity states. Since the executor's event loop is blocked by synchronous HTTP calls, the entire executor freezes and stops processing ticks. This was observed in production where the executor stopped at 20:40 and didn't resume until a manual reboot ~10 hours later.

The executor runs in a background thread with its own asyncio event loop, but the HA client makes blocking calls directly from async methods without using `asyncio.to_thread()` or an async HTTP library.

## Goals / Non-Goals

**Goals:**
- Eliminate blocking HTTP calls in the executor's async event loop
- Ensure executor continues processing even when HA is slow or unresponsive
- Add proper timeout and retry handling for HA API calls
- Maintain backward compatibility with existing configuration
- Keep the same public API surface (internal changes only)

**Non-Goals:**
- Changing the executor's architecture or threading model
- Adding new features beyond async HTTP
- Modifying the scheduler or planner components
- External API changes (this is internal refactoring)

## Decisions

### Decision: Use `aiohttp` instead of `asyncio.to_thread()`
**Rationale**: While wrapping sync `requests` calls in `asyncio.to_thread()` would be a quick fix, using `aiohttp` is the proper production-grade solution. It provides native async support, better connection pooling, built-in timeout handling, and is the industry standard for async HTTP in Python. This eliminates thread overhead and potential thread pool exhaustion.

**Alternative considered**: `asyncio.to_thread()` wrapper around existing `requests` code. Rejected because it still uses sync library with thread overhead and doesn't provide native async benefits like connection pooling.

### Decision: Keep HAClient as internal class, make methods async
**Rationale**: The `HAClient` is already an internal implementation detail. Making its methods async (`get_state`, `get_state_value`, `call_service`, etc.) is the cleanest approach. The `ActionDispatcher` already has async `execute()` method, so awaiting HA client calls fits naturally.

**Alternative considered**: Creating separate async client class. Rejected because it duplicates code and complicates the architecture.

### Decision: Timeout of 5 seconds with single retry
**Rationale**: A 5-second timeout is reasonable for local HA API calls. If HA doesn't respond in 5 seconds, something is wrong. Single retry handles transient network blips without indefinite hanging.

**Alternative considered**: 10-second timeout (current). Rejected because it's too long - the executor ticks every minute, so hanging for 10+ seconds per entity (with 10+ entities) causes cascade delays.

### Decision: Graceful degradation on HA failures
**Rationale**: If HA is unreachable, the executor should log the error and continue operating with last-known state rather than crashing. This matches the current behavior but with better responsiveness.

## Risks / Trade-offs

**[Risk] All executor tests use sync mocking** → Mitigation: Update test mocks to use `AsyncMock` and `pytest-asyncio`. The test infrastructure already supports async tests.

**[Risk] Dependencies need updating** → Mitigation: `aiohttp` is already widely used and well-maintained. Add to requirements.txt with pinned version.

**[Risk] Exception handling changes** → Mitigation: `aiohttp` raises different exception types than `requests`. Need to update exception handling to catch both `aiohttp.ClientError` and maintain backward compatibility where needed.

**[Trade-off] Code churn** → The `executor/actions.py` file (~1000 lines) needs significant changes. However, this is isolated to one module and well-covered by tests.

## Migration Plan

1. **Phase 1**: Update `HAClient` class to use `aiohttp` and make methods async
2. **Phase 2**: Update `ActionDispatcher` to await HA client calls
3. **Phase 3**: Update `ExecutorEngine` state gathering to use async methods
4. **Phase 4**: Update all executor tests to use async mocks
5. **Phase 5**: Run full test suite, verify no regressions
6. **Phase 6**: Deploy to staging, monitor for 24 hours
7. **Phase 7**: Deploy to production

**Rollback**: If issues occur, revert the commit. The changes are isolated to the executor module.

## Open Questions

- Should we add circuit breaker pattern for repeated HA failures? (Future enhancement)
- Should we track HA API latency metrics? (Future enhancement)
