## 1. Fix `tests/conftest.py`

- [x] 1.1 Remove the backup/restore of `config.yaml` and the `asyncio.run(init_db())` / `asyncio.run(engine.dispose())` calls from `setup_test_env`
- [x] 1.2 Add a monkey-patch of `inputs.load_yaml` in `setup_test_env` that returns the in-memory test config dict when called with `"config.yaml"`, and restores the original in teardown
- [x] 1.3 Keep the `data/` directory creation (needed by other tests) and the `data/test_planner.db` unlink in teardown

## 2. Fix `scripts/lint.sh`

- [x] 2.1 Replace `cd frontend && pnpm format && cd ..` with `(cd frontend && pnpm format)` to ensure the exit code propagates through `set -e`
- [x] 2.2 Replace `cd frontend && pnpm lint && cd ..` with `(cd frontend && pnpm lint)` for the same reason

## 3. Verify

- [x] 3.1 Run `uv run python -m pytest -q` and confirm all tests pass and `config.yaml` hash is unchanged before and after
- [x] 3.2 Run `./scripts/lint.sh` and confirm it exits non-zero when ESLint has warnings (verify by checking the ESLint `max-warnings 0` constraint still triggers)
