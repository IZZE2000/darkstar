## Why

The Darkstar executor currently uses synchronous `requests` library for all Home Assistant API calls. When the Fronius inverter (or any HA entity) becomes unresponsive, these blocking HTTP calls freeze the entire executor event loop, causing the system to stop executing for hours until manually rebooted. This is a critical reliability issue affecting production deployments.

## What Changes

- **BREAKING**: Replace synchronous `requests` library with `aiohttp` throughout the executor module
- Migrate `HAClient` class in `executor/actions.py` from sync to async
- Update `ExecutorEngine._gather_system_state()` to use async HA client methods
- Update action dispatcher to properly await async HA operations
- Add request timeout handling with proper exception management
- Ensure backward compatibility with existing configuration

## Capabilities

### New Capabilities
- `async-http-client`: Asynchronous HTTP client for Home Assistant API with proper timeout and retry handling

### Modified Capabilities
<!-- No existing spec requirements are changing - this is an implementation detail fix -->

## Impact

- **Code**: `executor/actions.py` (HAClient class), `executor/engine.py` (state gathering and action execution)
- **Dependencies**: Add `aiohttp` to requirements, remove `requests` from executor usage
- **API**: HAClient methods become async (internal breaking change, no external API impact)
- **Testing**: All executor tests need async updates
- **Risk**: Low - isolated to executor module, extensive test coverage exists
