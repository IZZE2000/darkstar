## Context

The current test suite is noisy with DeprecationWarnings and thread leakage warnings from `aiosqlite`. This noise increases the cognitive load for developers and can hide real regressions.

## Goals / Non-Goals

**Goals:**
- Eliminate all `DeprecationWarning` messages related to `pythonjsonlogger`, `Pydantic`, and `datetime.utcnow()`.
- Eliminate all `PytestUnhandledThreadExceptionWarning` messages related to unclosed `aiosqlite` connections.
- Ensure all database-related tests and fixtures follow the "dispose engine" pattern.

**Non-Goals:**
- Upgrading all libraries to the absolute latest version (only fixing specific deprecations).
- Refactoring `inputs.py` (out of scope for this change).
- Adding new feature tests.

## Decisions

### 1. Update Logging Import Path
Transition `backend/core/logging.py` to use `from pythonjsonlogger import json as jsonlogger`.
- **Rationale**: The library maintains backwards compatibility via this new path while deprecating the old top-level import.
- **Alternatives**: Switching to `JsonFormatter` directly, but reusing the existing `jsonlogger` name minimizes changes in the rest of the file.

### 2. Update Pydantic Configuration to V2
Update `BriefingRequest` in `backend/api/routers/forecast.py` to use `model_config = ConfigDict(extra="allow")`.
- **Rationale**: Pydantic V2 is already the project's standard, and the old `class Config` is scheduled for removal in V3.

### 3. Replace `utcnow()` with Timezone-Aware UTC
Update `tests/ml/test_ml_history.py` to use `datetime.now(UTC)`.
- **Rationale**: Python 3.12 formally deprecated `utcnow()`. Timezone-aware objects are the modern standard.

### 4. Explicit Engine Disposal in Tests
Modify `tests/conftest.py` and `tests/planner/test_schedule_history_overlay.py` to ensure `AsyncEngine` instances are disposed of.
- **Rationale**: `aiosqlite` uses background threads. If the engine isn't disposed of, these threads try to communicate with the event loop after it has been closed by `pytest`, causing a crash.
- **Implementation**:
    - Wrap engine creation and disposal in a `try...finally` or explicit `await engine.dispose()` call.
    - For `conftest.py`, ensure the temporary session-scoped engine is disposed of after `Base.metadata.create_all`.

## Risks / Trade-offs

- **[Risk]** → Misconfiguring Pydantic `model_config` could break the `/briefing` endpoint.
- **[Mitigation]** → Verify with existing integration tests.
- **[Risk]** → Improper engine disposal could lead to hanging tests.
- **[Mitigation]** → Ensure all tests are awaited properly and verified with the full suite run.
