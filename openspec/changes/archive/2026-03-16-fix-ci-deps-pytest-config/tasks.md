## 1. Fix stale CI pipeline path

- [x] 1.1 In `.github/workflows/ci.yml` line 25, change `ruff check backend/ inputs.py --output-format=github` to `ruff check backend/ --output-format=github` (remove the non-existent `inputs.py` reference)

## 2. Pin database dependencies

- [x] 2.1 In `requirements.txt`, change `alembic` (line 4) to `alembic>=1.18.4,<2.0.0`
- [x] 2.2 In `requirements.txt`, change `sqlalchemy` (line 24) to `sqlalchemy>=2.0.48,<3.0.0`

## 3. Fix pytest pythonpath configuration

- [x] 3.1 In `pyproject.toml` under `[tool.pytest.ini_options]` (line 63), add `pythonpath = ["."]` after the existing `testpaths` line

## 4. Verification

- [x] 4.1 Run `uv run pytest -q` (NOT `python -m pytest`) and confirm all tests pass with no import errors
- [x] 4.2 Run `uv run ruff check backend/ --output-format=github` and confirm it succeeds
- [x] 4.3 Run `./scripts/lint.sh` and confirm no new issues
