# AGENTS.md - Development Guidelines for Darkstar Energy Manager

## Build & Test Commands

### Python Environment
- **Python version**: 3.12.0 (see .python-version)
- **Virtual environment**: Located in `.venv/` (managed by `uv`)
- **Install dependencies**: `uv pip install -r requirements.txt` (Source of Truth)
- **Preferred interpreter**: `./.venv/bin/python` (Explicitly use this if sandboxed; assume `PYTHONPATH=.` for repo-local tools).
- **Run main planner**: `uv run python bin/run_planner.py`
- **Test inputs module**: `uv run python inputs.py`
- **Run full test suite**: `uv run python -m pytest -q`
- **Run single test**: `uv run python -m pytest tests/test_module.py::test_function -v`
- **Run Dev Environment**: `pnpm run dev` (Runs Frontend + Backend + WebSockets concurrently).

### Fish Shell (Important!)
The development environment uses **fish shell**. Special characters in commit messages cause issues:
- **Avoid parentheses** `()` in commit messages - fish interprets them as command substitution
- **Use simple messages**: `git commit -m "Short description without special chars"`
- **For complex messages**: Use `git commit` without `-m` to open editor

### Key Dependencies
- `pandas` - Data manipulation and analysis
- `pyyaml` - YAML configuration file parsing
- `nordpool` - Electricity price data fetching
- `pytz` - Timezone handling
- `requests` - REST clients for Home Assistant and forecasts
- `fastapi` - Modern async API framework (ASGI)
- `uvicorn` - ASGI server
- `python-socketio` - Async WebSocket support
- `lightgbm`: Aurora ML models
- `sqlalchemy` / `aiosqlite`: Database and async ORM


## Code Style Guidelines

### Imports
- Group imports: standard library, third-party, local modules
- Use explicit imports: `import yaml` not `from yaml import *`
- Order alphabetically within groups
- Example:
```python
import json
from datetime import datetime, timedelta

import pandas as pd
import pytz
import yaml

### Linting & Quality Control
*   **Mandatory Checks**: At the end of **every revision** (before marking as done), you MUST run the standard linting and testing suite.
    *   **Frontend**: `pnpm lint` (must be error-free) and `pnpm format`.
    *   **Backend Linting**: `uv run ruff check .` and `uv run pyright .` (if Python files were touched).
    *   **Backend Testing**: `uv run python -m pytest -q` (MUST pass 100% to ensure no regressions).
    *   **Scripts**: If `sys.path` manipulation is required before imports, use `# noqa: E402`.
*   **Zero-Error Policy**: Do not leave known lint errors. If a rule cannot be satisfied, use a specific suppression comment with a justification, but prefer fixing the code.

from inputs import get_all_input_data
```

### Formatting & Types
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 88 characters (Black default)
- Use type hints for function signatures and return types
- Follow PEP 8 naming conventions:
  - `snake_case` for variables and functions
  - `PascalCase` for classes
  - `UPPER_CASE` for constants

### Error Handling
- Use specific exceptions: `except ValueError:` not `except:`
- Handle external API calls with try/except blocks
- Log errors with context information
- Fail gracefully with meaningful error messages

### Configuration
- All user-configurable parameters in `config.yaml`
- **Structural Enforcement**: `config.yaml` is strictly reordered on startup to match the order and comments of `config.default.yaml` (via "Template Fill" strategy).
- **Comment Preservation**: Official comments from `config.default.yaml` are always preserved; user comments on standard keys are overwritten.
- **Custom Keys**: Non-standard user keys are preserved and appended.
- Use nested structure with logical groupings (battery, thresholds, etc.)
- `charging_strategy.price_smoothing_sek_kwh` controls price tolerance (smoothing block now covers only hysteresis settings)
- `charging_strategy.block_consolidation_tolerance_sek` allows merging adjacent charge slots when price spread is within tolerance (fallback to smoothing when unset)
- `charging_strategy.consolidation_max_gap_slots` caps how many zero-capacity slots can exist inside a consolidated block
- `learning.sqlite_path` stores planner telemetry (ensure parent directory exists before running)
- `s_index` supports `mode` (`probabilistic` or `dynamic`), `base_factor`, `max_factor`, `pv_deficit_weight`, `temp_weight`, `temp_baseline_c`, `temp_cold_c`, `s_index_horizon_days` (integer, default 4), and `risk_appetite` (1-5)
- `secrets.yaml` must include Home Assistant sensor IDs: `battery_soc_entity_id` and `water_heater_daily_entity_id`
- `arbitrage` adds peak export controls: `export_percentile_threshold`, `enable_peak_only_export`, `export_future_price_guard`, `future_price_guard_buffer_sek`

### Data Processing
- Use pandas DataFrames for time-series data
- Apply timezone-aware datetime handling
- Process data in logical passes (see planner.py structure)
- Maintain data immutability where possible

### Testing & Validation
- Test edge cases (empty data, missing config, API failures)
- Validate output JSON schema matches expected format
- Test with realistic data ranges
- Verify timezone handling across daylight saving transitions

### Documentation
- Use docstrings for all public functions and classes
- Include parameter types and return value descriptions
- Add inline comments for complex business logic
- Maintain README with setup and usage instructions

### Process Policy
- Before implementing any newly drafted revision/plan section (e.g., after we agree on a fix plan), switch to the designated implementation model. Planning and discussion should happen first; code changes should only be made after switching models.
- **Planning**: Before implementing, ensure the revision is active in `docs/PLAN.md`.
- **History / Archival**:
  - A revision may be moved from `docs/PLAN.md` to `docs/CHANGELOG_PLANS.md` **only** when:
    - The relevant project phase is fully completed and validated, and
    - The Product Owner has explicitly confirmed that the revision is ready to be archived.
  - Once moved, the revision should live in **one place only** (the changelog), not duplicated in `docs/PLAN.md` (a short pointer is fine if needed).
  - While a project phase is active, keep its revisions in `docs/PLAN.md` for context; do not archive them without prior confirmation.

### Git & Data Hygiene
- Treat `config.yaml` as environment-specific. Do **not** commit server-only edits; keep long-lived defaults in `config.default.yaml` and copy/merge locally.
- Never commit runtime data:
  - `data/planner_learning.db` (SQLite telemetry)
  - `data/scheduler_status.json`
  - `schedule.json`
- **Local Exclusions**: Use `.git/info/exclude` for personal or generated files (e.g., `docs/reports/`) to avoid polluting the global `.gitignore`.
- When deploying to a server, prefer `git stash` / `git restore` to keep local DB and schedules, then `git checkout` the desired branch.

### Releasing a New Version
When releasing a new version:
1. **Mandatory: Create/Update Release Notes**: Update [docs/RELEASE_NOTES.md](file:///home/s/sync/documents/projects/darkstar/docs/RELEASE_NOTES.md) with the changes for this version.
2. **Bump version/notes** in all 8 locations:
   - `/docs/RELEASE_NOTES.md` (Update with latest changes)
   - `/package.json` (root)
   - `/VERSION` (root)
   - `/config.yaml` (root)
   - `/config.default.yaml` (root)
   - `darkstar/config.yaml` (HA add-on manifest)
   - `darkstar/run.sh` (startup banner)
   - `frontend/package.json`
3. **Commit and Tag**:
   ```bash
   git add .
   git commit -m "chore(release): bump to vX.Y.Z"
   git tag vX.Y.Z
   ```
4. **Push**:
   ```bash
   git push origin main --tags
   ```

> **Note**: The CI/CD pipeline (`build-addon.yml`) is triggered **automatically** when you push a tag starting with `v`. It will:
> 1. Build the Docker image and publish it to GHCR.
> 2. **Automatically create a GitHub Release** using the notes extracted from `docs/RELEASE_NOTES.md`.

The sidebar version is fetched from `/api/version` which uses `git describe --tags`. Without a proper tag, it shows `vX.Y.Z-N-ghash` format.

### Tooling
- After major code changes or a completed revision:
  - **Frontend**:
    - Run `pnpm format` in `frontend/` to fix formatting issues automatically.
    - Run `pnpm lint` in `frontend/` to verify code quality.
  - **Backend/General**:
    - Run `uv run ruff format .` to normalize formatting.
    - Run `uv run ruff check .` to lint and catch issues.
    - Run `uv run pyright .` to verify type safety (strict mode).
    - Run `uv run python -m pytest -q` to verify no regressions.
    - Or simply run `./scripts/lint.sh` for all checks at once.

### Development Protocol
- **Production-Grade Only**: Always implement production-grade solutions. Never take shortcuts or use quick-fix approaches. Prefer clean, maintainable, and robust implementations.
- **Investigate First**: Before fixing any issue (except small bug fixes with no architectural impact):
  1. Investigate the problem thoroughly.
  2. Report findings to the user.
  3. Present options if multiple approaches exist.
  4. Wait for user approval before implementing.
- **One Problem at a Time**: When the user mentions multiple issues, handle them sequentially. Store all items in a task list and work through them one by one.
- **Regular Commits**: Commit changes after completing a defined task or revision. This should occur after each task or batch of tasks. It has to follow the semantic versioning rules.
- **UI Design Guide**: All UI changes must strictly follow the design system:
  - **AI Guidelines**: [docs/design-system/AI_GUIDELINES.md](docs/design-system/AI_GUIDELINES.md)
  - **Live Preview**: `/design-system` route shows all components
  - **SSOT**: `frontend/src/index.css` contains all tokens and component classes
- **Documentation Always Updated**: When making any code changes, update relevant documentation (`architecture.md`, `README.md`, etc.). Documentation must always reflect the current implementation.
- **Unified Validation**: All configuration changes MUST pass the unified validation in `backend/api/routers/config.py:_validate_config_for_save`. Critical entities (SoC, Work Mode, Grid Charging) are mandatory for the executor to avoid 404 errors.
- **Error Tracking**: Complex background tasks (like the Executor) must track recent errors using a bounded queue (e.g. `deque`) and expose them via a `/health` endpoint for real-time UI feedback.
- **User Consultation**: Consult the user before:
  - Making major architectural changes.
  - Archiving revisions.
  - **Updating any files in the `docs/` directory.**

### Terminal & Command Execution Troubleshooting
- **Hanging Commands**: If a command (like `pytest` or a `git` hook) freezes indefinitely and does not output anything:
  1. **Do NOT use `Ctrl+Z`** to suspend the process. This sends a `SIGTSTP` signal and leaves the process alive in the background (state `T` in `ps`), actively holding the terminal's output pipe open, which will freeze ALL future commands in the AI agent framework due to lack of EOF.
  2. **Use `Ctrl+C` first** (`SIGINT`) to cancel a stuck command gracefully.
  3. **Find and Kill**: If `Ctrl+C` fails, leave the hanging command alone (do not suspend it), invoke a separate terminal task, investigate the process list (`ps fux | grep -E "pytest|uv|git"`), and explicitly kill the frozen PIDs with `kill -9 <PID>` to release the file descriptors.
  4. **Always Fix the Root Cause**: Investigate *why* it froze (e.g., unclosed background threads, missing timeouts) and patch the code rather than repeatedly canceling the command.
  5. **AI Extension UI Desync**: If a command like `git commit -m "..."` completes instantly but the AI UI still shows it as "Running", the AI's internal parser lost the prompt marker. This is caused by **multi-line string literals** (newlines inside quotes) generating `> ` continuation prompts that confuse the UI.
     * **Prevention**: Always use single-line `git commit -m "message"` or `git commit -am` commands from the AI. Never send raw newlines inside the `-m` string. If long messages are needed, use an editor or format the string carefully without literal mid-string newlines.
     * **Fix**: Run `kill -9 $(pgrep -f "bash")` (specifically the hidden background bash spawned by the extension) to forcefully reset the AI's internal PTY state.

### Git & Commit Standards
- **Strict Conventional Commits**: Mandatory for all commits.
- **Format**: `type(scope): description`
- **Allowed Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`.
- **Commitlint**: Automatically enforced via hooks. Ensure messages pass `commitlint` before pushing.
- **Fish Shell**: Avoid `()` in commit messages if using `-m`.

## Project Structure
- `backend/` - FastAPI API, Strategy Engine (`backend/strategy/`), and internal `SchedulerService`.
- `frontend/` - React + Vite UI application.
- `ml/` - Aurora Machine Learning pipeline (`train.py`, `forward.py`).
- `inputs.py` - Data fetching (Home Assistant, Nordpool).
- `planner.py` - Core MPC scheduling logic.
- `config.yaml` - Master configuration.
- `backend/themes/` - UI theme files (JSON/YAML).

### Key Business Logic
- Multi-pass Model Predictive Control (MPC) approach
- Strategic charging during low-price periods
- Cascading responsibility between time windows
- Integrated water heating scheduling
- "Hold in cheap windows" principle to preserve battery

### Output Requirements
- Generate `schedule.json` with proper schema
- Include slot numbers, timestamps, classifications
- Round numerical values to 2 decimal places
- Ensure timezone-aware ISO format timestamps
