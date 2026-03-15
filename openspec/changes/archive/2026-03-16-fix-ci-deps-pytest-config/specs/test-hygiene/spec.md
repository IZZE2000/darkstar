## ADDED Requirements

### Requirement: Consistent pytest invocation

The test suite SHALL be runnable via both `uv run pytest` and `uv run python -m pytest` with identical behavior.

#### Scenario: Bare pytest invocation
- **WHEN** a developer runs `uv run pytest` from the project root
- **THEN** all tests pass without `ModuleNotFoundError`
- **AND** the behavior is identical to `uv run python -m pytest`

### Requirement: CI pipeline reflects current source layout

The CI pipeline SHALL only reference source paths that exist in the current project structure.

#### Scenario: Ruff lint step
- **WHEN** the CI pipeline runs the ruff lint step
- **THEN** it checks all Python source directories that exist (e.g., `backend/`)
- **AND** it does not reference deleted files (e.g., the former root-level `inputs.py`)

### Requirement: Critical dependencies pinned with version bounds

Database-layer dependencies (SQLAlchemy, Alembic) SHALL have explicit version bounds to prevent uncontrolled major-version upgrades.

#### Scenario: Fresh install
- **WHEN** running `pip install -r requirements.txt` on a clean environment
- **THEN** SQLAlchemy installs within the 2.x range
- **AND** Alembic installs within the 1.x range
