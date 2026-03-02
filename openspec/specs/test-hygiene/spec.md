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
The system SHALL ensure that all `AsyncEngine` instances created during tests are explicitly disposed of before the event loop is closed.

#### Scenario: Database test cleanup
- **WHEN** a test or session fixture that creates a database engine finishes
- **THEN** it explicitly awaits `engine.dispose()` to ensure background threads are terminated.

### Requirement: Clean Test Suite Baseline
The full test suite SHALL execute with zero `DeprecationWarning` and zero `PytestUnhandledThreadExceptionWarning` messages.

#### Scenario: Full suite execution
- **WHEN** `uv run python -m pytest` is executed
- **THEN** the output contains "492 passed" (or current count) and "0 warnings".
