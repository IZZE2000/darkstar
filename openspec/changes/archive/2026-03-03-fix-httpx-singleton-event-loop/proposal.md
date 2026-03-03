## Why

The `inputs.py` module uses a module-level singleton `_ha_client` (httpx.AsyncClient) that is shared across all async HA sensor reads. When commit `1a6790c` migrated the executor to async aiohttp running in a background thread with its own event loop, this caused event loop corruption. The httpx client's internal asyncio locks get bound to the FastAPI event loop, but are accessed from the executor's thread event loop, causing "bound to a different event loop" errors. This results in HA sensor reads returning None, which causes PV data to be recorded as 0.0 in the database.

## What Changes

- **Fix**: Remove the singleton pattern in `inputs.py` `get_ha_client()` function
- **Change**: Create fresh httpx.AsyncClient per call (httpx handles connection pooling internally)
- **Update**: Add event loop isolation requirement to async-http-client capability spec
- **Update**: Document the cross-thread event loop safety requirement

## Capabilities

### New Capabilities
<!-- None - this is a fix to existing capability -->

### Modified Capabilities
- `async-http-client`: Add requirement that async HTTP clients SHALL NOT be shared across event loops. Add scenario for cross-loop isolation to prevent event loop corruption.

## Impact

- **inputs.py**: Core change to `get_ha_client()` function (line 22-30)
- **All callers**: Recorder, LoadDisaggregator, API routes - no code changes needed, they all call `get_ha_client()`
- **Behavior**: Fixes PV=0.0 recording bug caused by event loop corruption
- **Performance**: No degradation - httpx has built-in connection pooling
- **Testing**: No test changes needed - tests mock `get_ha_client()` already

## Success Criteria

- [ ] No more "bound to a different event loop" errors in logs
- [ ] PV data is correctly recorded in database instead of staying at 0.0
- [ ] All existing tests pass without modification
