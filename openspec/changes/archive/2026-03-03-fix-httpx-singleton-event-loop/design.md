## Context

The `inputs.py` module at line 22-30 used a module-level singleton pattern:

```python
_ha_client: httpx.AsyncClient | None = None

async def get_ha_client() -> httpx.AsyncClient:
    global _ha_client
    if _ha_client is None or _ha_client.is_closed:
        _ha_client = httpx.AsyncClient(timeout=10.0)
    return _ha_client
```

This singleton was shared across:
- FastAPI main thread (event loop for API routes)
- Executor background thread (separate event loop)
- Any other async contexts

**The Problem**: httpx.AsyncClient uses asyncio internally for connection pooling. When the client is created in the FastAPI event loop, its internal locks (asyncio.Event) are bound to that loop. When the executor's background thread tries to use the same client, it accesses these locks from a different event loop, causing:
```
asyncio.locks.Event is bound to a different event loop
```

**Impact**: All HA sensor reads fail, returning None. The recorder defaults to 0.0 for power readings, resulting in PV=0.0 in the database.

**Root Cause Commit**: `1a6790c` (feat(executor): migrate to async aiohttp HTTP client) introduced the executor's async architecture without accounting for the shared singleton in `inputs.py`.

## Goals / Non-Goals

**Goals:**
- Fix event loop corruption in `inputs.py`
- Ensure HA sensor reads work correctly from both FastAPI and executor threads
- Properly close httpx.AsyncClient resources to prevent connection pool leaks
- Update async-http-client spec to prevent future regressions

**Non-Goals:**
- No changes to executor architecture
- No performance optimization beyond the fix

## Decisions

### Decision 1: Remove Singleton Pattern with Proper Resource Management

**Option A: Inline async with context manager (SELECTED)**
- Replace `get_ha_client()` calls with `async with httpx.AsyncClient() as client:`
- Ensures automatic resource cleanup via context manager
- No singleton, no event loop issues, no resource leaks
- Delete `get_ha_client()` function entirely

**Option B: Keep get_ha_client() but return unopened client**
- Requires all call sites to use `async with await get_ha_client():`
- Error-prone - easy to forget the context manager
- More complex than inlining

**Option C: Manual close() calls**
- Try/finally blocks at every call site
- Verbose and error-prone

**Decision**: Choose Option A. Inline the client creation with `async with` context manager. This is the cleanest, safest approach. The function `get_ha_client()` is deleted entirely.

### Decision 2: Update Spec

**Update the async-http-client spec** to add:
- Requirement: Async HTTP clients SHALL NOT be shared across event loops
- Requirement: Async HTTP clients SHALL use context managers for proper resource cleanup
- Scenarios for cross-loop isolation and resource management

## Risks / Trade-offs

**Risk**: Performance degradation from creating clients per-call
→ **Mitigation**: httpx uses connection pooling at the TCP level. Client object creation is cheap compared to network I/O. The `async with` pattern is standard and efficient.

**Risk**: Resource leaks if context manager not used
→ **Mitigation**: All call sites now use `async with`. Regression tests verify context manager is used and `__aexit__` is called.

**Risk**: Breaking existing code that imported get_ha_client
→ **Mitigation**: Search codebase for all usages and inline them. The function is internal to inputs.py.

**Risk**: Test changes required
→ **Mitigation**: Update regression test to verify `async with` pattern and resource cleanup instead of testing the deleted function.

## Migration Plan

1. **Update `inputs.py`**:
   - Inline `async with httpx.AsyncClient()` at all call sites
   - Delete `get_ha_client()` function
2. **Update `services.py`**: Remove get_ha_client import, inline client usage
3. **Update tests**: Rewrite regression test to verify resource cleanup
4. **Update spec**: Add event loop isolation and resource management requirements
5. **Run tests**: Verify all tests pass
6. **Deploy**: Standard deployment

## Open Questions

None. The fix is straightforward and well-understood.
