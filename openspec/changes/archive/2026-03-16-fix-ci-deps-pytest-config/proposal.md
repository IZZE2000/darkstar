## Why

The recent inputs.py and services.py refactorings left a stale file reference in the CI pipeline, and two infrastructure gaps remain: unpinned critical database dependencies and a pytest configuration issue that prevents running tests with bare `pytest` (only `python -m pytest` works).

## What Changes

- **Fix**: `.github/workflows/ci.yml` references `inputs.py` which no longer exists (split into `backend/core/` modules) — remove the stale path from the ruff check command
- **Fix**: `requirements.txt` has `sqlalchemy` and `alembic` completely unpinned — add version bounds matching current installed versions (SQLAlchemy 2.0.48, Alembic 1.18.4)
- **Fix**: `pyproject.toml` pytest config missing `pythonpath = ["."]` — bare `uv run pytest` fails with `ModuleNotFoundError: No module named 'backend.core'` while `uv run python -m pytest` works (python -m adds CWD to sys.path automatically)

## Capabilities

### New Capabilities

None - infrastructure/config fixes only.

### Modified Capabilities

- `test-hygiene`: Extend to cover pytest path configuration for consistent test invocation

## Impact

- **CI**: `.github/workflows/ci.yml` — ruff lint step will correctly check all backend code
- **Dependencies**: `requirements.txt` — prevents surprise breakage from major version bumps
- **Tests**: `pyproject.toml` — both `pytest` and `python -m pytest` invocations work identically
