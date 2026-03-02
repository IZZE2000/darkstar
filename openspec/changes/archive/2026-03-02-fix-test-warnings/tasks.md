## 1. Backend Deprecation Fixes

- [x] 1.1 Update `backend/core/logging.py` to use `from pythonjsonlogger import json as jsonlogger`
- [x] 1.2 Update `BriefingRequest` in `backend/api/routers/forecast.py` to use `ConfigDict(extra="allow")`
- [x] 1.3 Add `from pydantic import ConfigDict` import to `backend/api/routers/forecast.py`

## 2. Test Suite Modernization

- [x] 2.1 Update `tests/ml/test_ml_history.py` to replace `datetime.utcnow()` with `datetime.now(UTC)`
- [x] 2.2 Ensure `from datetime import UTC` is imported in `tests/ml/test_ml_history.py`

## 3. Async Thread Leakage Fixes

- [x] 3.1 Refactor `tests/conftest.py` `setup_test_env` to explicitly `await engine.dispose()` after schema initialization
- [x] 3.2 Update `tests/planner/test_schedule_history_overlay.py` to ensure all `AsyncEngine` instances are disposed of using `await engine.dispose()`

## 4. Verification

- [x] 4.1 Run full test suite: `uv run python -m pytest -q`
- [x] 4.2 Verify zero `DeprecationWarning` in the output
- [x] 4.3 Verify zero `PytestUnhandledThreadExceptionWarning` in the output
- [x] 4.4 Run linting: `./scripts/lint.sh`
