## Why

`tests/conftest.py` overwrites `config.yaml` with an 11-line stub every test session and relies on a backup/restore pattern that silently fails if the session is interrupted (e.g. `Ctrl+C` during `./scripts/lint.sh`). Separately, `lint.sh` uses `set -euo pipefail` but the frontend linting step swallows its exit code through a shell pipe, printing "✅ All checks passed!" even on ESLint failure.

## What Changes

- Replace the backup/restore pattern in `conftest.py` with a monkey-patch of `inputs.load_yaml` — `config.yaml` is never touched during tests.
- Remove the async DB init from the session fixture entirely; DB initialisation already happens per-test or can be handled inline.
- Fix `lint.sh` so that `pnpm lint` exit code is correctly propagated and `set -e` catches it.

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `test-hygiene`: The session fixture requirement for DB engine disposal and test isolation changes — the conftest no longer uses `asyncio.run()` or file mutation for test setup. The "Clean Test Suite Baseline" scenario remains valid but the mechanism changes.

## Impact

- `tests/conftest.py` — rewritten fixture
- `scripts/lint.sh` — fix frontend lint step exit code propagation
- No production code changes — `inputs.load_yaml` call sites are untouched
