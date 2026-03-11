## Context

Two independent bugs both stem from the same session-level fixture in `tests/conftest.py`:

1. **Config clobber**: `setup_test_env` (autouse, session scope) writes an 11-line stub over `config.yaml` and relies on a backup/restore in its teardown. If the process is interrupted before `yield` — e.g. because `scripts/lint.sh` uses `set -euo pipefail` and exits early — the teardown never runs, leaving `config.yaml` destroyed.

2. **lint.sh exit-code swallowing**: `cd frontend && pnpm lint && cd ..` — the `cd ..` resets the exit code to 0. `set -e` never fires on an ESLint failure. The script prints "✅ All checks passed!" and exits 0.

## Goals / Non-Goals

**Goals:**
- `config.yaml` is never touched by any test run, under any termination scenario
- `lint.sh` faithfully propagates non-zero exit codes from every step (including frontend lint)
- No call-site changes to `inputs.load_yaml` across the codebase

**Non-Goals:**
- Rewriting all tests to be config-independent
- Changing `inputs.load_yaml` signature or behaviour in production code
- Fixing other potential lint.sh fragilities beyond the frontend lint exit-code bug

## Decisions

### Decision 1: Patch `inputs.load_yaml` instead of touching `config.yaml`

**Chosen**: In `setup_test_env`, monkey-patch `inputs.load_yaml` at the module level to return a parsed in-memory dict when called with `"config.yaml"`. Restore the original in teardown.

**Alternatives considered**:
- *Backup/restore*: Current approach — fragile against kills/interrupts.
- *`DARKSTAR_CONFIG` env var*: `load_yaml` doesn't read env vars; would require patching anyway plus a production code change.
- *`tmp_path_factory` + real file*: Still touches the filesystem; the patch is simpler and zero-filesystem.

**Rationale**: The patch is the single smallest change that eliminates the mutation. Session scope is correct because `load_yaml` is stateless and the test config is constant for a session.

### Decision 2: Remove the async DB init from the session fixture

The session fixture currently calls `asyncio.run(init_db())` to pre-create the DB schema. In `pytest-asyncio` 1.x (strict mode), this works today but is explicitly unsafe if the event loop policy changes. The per-test DB fixtures in `tests/backend/test_recorder_deltas.py` already handle their own schema init; the session-level init is redundant.

**Chosen**: Remove `asyncio.run(init_db())` and `asyncio.run(engine.dispose())` from the session fixture entirely.

### Decision 3: Fix lint.sh frontend step with explicit exit-code capture

**Chosen**: Change `cd frontend && pnpm lint && cd ..` to:
```bash
(cd frontend && pnpm lint)
```
A subshell `(...)` scope-limits the `cd` and the exit code of the subshell is the exit code of the last command (`pnpm lint`). `set -e` then fires correctly on failure.

Apply the same pattern to `pnpm format`.

## Risks / Trade-offs

- [Risk]: Tests that import `inputs` at module level (before the fixture runs) won't see the patched `load_yaml`. → Mitigation: All current callers use `load_yaml` lazily at function call time, not at import time. Verified by grep.
- [Risk]: Removing the session-level DB init could break a test that depended on it. → Mitigation: Run the full suite after the change to confirm.
