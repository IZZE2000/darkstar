## 1. Fix Resource Leaks in Call Sites

- [x] 1.1 Fix `get_ha_entity_state()` to use `async with httpx.AsyncClient()` context manager
- [x] 1.2 Fix `get_load_profile_from_ha()` to use `async with httpx.AsyncClient()` context manager
- [x] 1.3 Fix `backend/api/routers/services.py` to use `async with httpx.AsyncClient()` context manager

## 2. Remove get_ha_client() Function

- [x] 2.1 Delete `get_ha_client()` function from `inputs.py`
- [x] 2.2 Remove `get_ha_client` import from `backend/api/routers/services.py`

## 3. Update Regression Tests

- [x] 3.1 Rewrite test to verify `async with` context manager pattern is used
- [x] 3.2 Add test to verify client is closed on exceptions
- [x] 3.3 Add test for `get_load_profile_from_ha()` resource cleanup
- [x] 3.4 Run tests - verify all pass

## 4. Verification

- [x] 4.1 Run regression test: `uv run python -m pytest tests/test_inputs_ha_client.py -v`
- [x] 4.2 Run full test suite: `uv run python -m pytest tests/ -v`
- [x] 4.3 Run linter: `uv run ruff check inputs.py backend/api/routers/services.py`
- [x] 4.4 Run type checker: `uv run pyright inputs.py backend/api/routers/services.py`

## 5. Update Specs

- [x] 5.1 Update `openspec/specs/async-http-client/spec.md` with resource management requirements
- [x] 5.2 Update archived OpenSpec design.md with corrected approach
- [x] 5.3 Update archived OpenSpec tasks.md to reflect actual changes

## 6. Deployment

- [x] 6.1 Commit with conventional format (user action)
- [x] 6.2 Deploy to production (user action)
- [x] 6.3 Monitor logs for 24 hours for event loop errors (user action)
