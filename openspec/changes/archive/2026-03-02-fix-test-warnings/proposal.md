## Why

The current test suite for Darkstar Energy Manager is "noisy" with several DeprecationWarnings and unhandled thread exceptions. This noise masks real issues, creates technical debt, and can lead to runtime failures in future Python or library versions. Fixing these ensures a "clean green" baseline for all future feature work.

## What Changes

- **Update Logging**: Transition from `pythonjsonlogger.jsonlogger` to the new `pythonjsonlogger.json` structure to resolve deprecation warnings.
- **Modernize Pydantic**: Update `BriefingRequest` in `backend/api/routers/forecast.py` to use Pydantic V2 `model_config` instead of the deprecated `class Config`.
- **Standardize UTC**: Replace deprecated `datetime.utcnow()` with timezone-aware `datetime.now(UTC)` in `tests/ml/test_ml_history.py`.
- **Fix Async Cleanup**: Ensure `AsyncEngine` instances in `tests/conftest.py` and `tests/planner/test_schedule_history_overlay.py` are properly disposed of to prevent `aiosqlite` thread leakage.
- **Verify Clean Suite**: Ensure the full test suite runs with zero warnings and zero errors.

## Capabilities

### New Capabilities
- `test-hygiene`: Defines the standards for warning-free and thread-safe testing in the Darkstar environment.

### Modified Capabilities
- (None)

## Impact

- **Backend**: `backend/core/logging.py`, `backend/api/routers/forecast.py`.
- **Tests**: `tests/conftest.py`, `tests/ml/test_ml_history.py`, `tests/planner/test_schedule_history_overlay.py`.
- **Infrastructure**: Improved test reliability and reduced console noise during CI/CD.
