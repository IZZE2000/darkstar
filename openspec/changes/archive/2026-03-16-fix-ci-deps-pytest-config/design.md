## Context

Three infrastructure issues remain after the inputs.py and services.py refactorings:

1. **Stale CI path**: `.github/workflows/ci.yml` line 25 runs `ruff check backend/ inputs.py --output-format=github`. The `inputs.py` file was deleted in commit 42681b6 (split-move-inputs) and its contents moved to `backend/core/`. Ruff silently skips the non-existent path, so linting still runs on `backend/` but the stale reference is confusing and will cause issues if ruff changes its behavior on missing paths.

2. **Unpinned database deps**: `requirements.txt` lists `alembic` (line 4) and `sqlalchemy` (line 24) with no version constraints. Currently installed: SQLAlchemy 2.0.48, Alembic 1.18.4. A `pip install --upgrade` or fresh install could pull SQLAlchemy 3.x when released, breaking the codebase silently.

3. **pytest pythonpath**: `pyproject.toml` `[tool.pytest.ini_options]` only has `testpaths = ["tests"]` but no `pythonpath` setting. Running `uv run pytest` directly fails with `ModuleNotFoundError: No module named 'backend.core'` because bare pytest doesn't add CWD to `sys.path`. Running `uv run python -m pytest` works because `python -m` adds CWD automatically. There is no root-level `conftest.py` and the test conftest files don't manipulate `sys.path`.

## Goals / Non-Goals

**Goals:**
- Fix the stale CI reference so the pipeline accurately reflects the current source layout
- Pin SQLAlchemy and Alembic to prevent surprise major-version breakage
- Make `uv run pytest` and `uv run python -m pytest` behave identically

**Non-Goals:**
- No changes to application code
- No CI pipeline restructuring beyond the path fix
- No dependency upgrades

## Decisions

**1. Remove `inputs.py` from CI ruff check**

Change line 25 from:
```yaml
run: ruff check backend/ inputs.py --output-format=github
```
to:
```yaml
run: ruff check backend/ --output-format=github
```

Rationale: `backend/` already covers `backend/core/` where the inputs code now lives. No additional paths needed.

**2. Pin SQLAlchemy and Alembic with major-version upper bounds**

```
sqlalchemy>=2.0.48,<3.0.0
alembic>=1.18.4,<2.0.0
```

Rationale: Matches current installed versions. Allows minor/patch updates but blocks major version jumps that could introduce breaking changes. Consistent with the pinning style used for other deps (e.g., `fastapi>=0.109.0`).

**3. Add `pythonpath = ["."]` to pytest config**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Rationale: This is the standard pytest solution for projects that aren't installed as packages. Makes CWD available for imports regardless of how pytest is invoked.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Version pins could block needed updates | Upper bounds are major-version only — minor/patch updates still flow through |
| Other stale CI references may exist | Checked — no other stale file references found in ci.yml |

## Migration Plan

1. Fix CI ruff path
2. Pin sqlalchemy and alembic in requirements.txt
3. Add pythonpath to pyproject.toml
4. Verify: `uv run pytest` passes, CI pipeline lints correctly

Rollback: Revert single commit.
