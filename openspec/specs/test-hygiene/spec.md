# Test Hygiene

## Purpose
This specification defines the standards for maintainable, warning-free, and thread-safe testing in the Darkstar environment. It aims to eliminate technical debt and ensure that the test suite provides high-signal feedback.

## Requirements

### Requirement: Warning-Free Logging
The system SHALL use the non-deprecated `pythonjsonlogger.json` structure for JSON logging.

#### Scenario: Logger initialization
- **WHEN** `backend/core/logging.py` is initialized
- **THEN** it imports from `pythonjsonlogger.json` and no `DeprecationWarning` is issued.

### Requirement: Modern Pydantic Configurations
The system SHALL use the Pydantic V2 `model_config` syntax for model configuration.

#### Scenario: Pydantic model validation
- **WHEN** `backend/api/routers/forecast.py` is imported or `BriefingRequest` is instantiated
- **THEN** no `PydanticDeprecatedSince20` warning is issued.

### Requirement: Timezone-Aware UTC Usage
The system SHALL use `datetime.now(UTC)` instead of `datetime.utcnow()` for UTC timestamps.

#### Scenario: UTC timestamp generation
- **WHEN** tests generate UTC timestamps (e.g., in `tests/ml/test_ml_history.py`)
- **THEN** they use `datetime.now(UTC)` and no `DeprecationWarning` is issued.

### Requirement: Guaranteed Thread Safety in Tests
The system SHALL ensure that no `AsyncEngine` instance is created in session-scoped fixtures. Per-test fixtures that create engines SHALL explicitly await `engine.dispose()` before the test event loop is closed.

#### Scenario: Database test cleanup
- **WHEN** a per-test fixture creates a database engine
- **THEN** it explicitly awaits `engine.dispose()` to ensure background threads are terminated before the test event loop closes.

### Requirement: Test Isolation from Production Config
The system SHALL NOT read from or write to `config.yaml` during any test session. Test config SHALL be injected via a monkey-patch of `inputs.load_yaml` in the session fixture.

#### Scenario: Test session does not corrupt config.yaml
- **WHEN** `uv run python -m pytest` is executed (or aborted mid-run)
- **THEN** `config.yaml` on disk is identical before and after the run.

#### Scenario: All callers of `inputs.load_yaml("config.yaml")` receive test config
- **WHEN** any module calls `inputs.load_yaml("config.yaml")` during a test session
- **THEN** it receives the in-memory test config dict without reading the filesystem.

### Requirement: Clean Test Suite Baseline
The full test suite SHALL execute with zero `DeprecationWarning` and zero `PytestUnhandledThreadExceptionWarning` messages. The lint script SHALL exit non-zero if any check (including frontend linting) fails.

#### Scenario: Full suite execution
- **WHEN** `uv run python -m pytest` is executed
- **THEN** the output contains the current passing count and zero warnings.

#### Scenario: lint.sh propagates frontend lint failures
- **WHEN** `./scripts/lint.sh` is executed and `pnpm lint` exits non-zero
- **THEN** `lint.sh` exits non-zero and does NOT print "✅ All checks passed!".
