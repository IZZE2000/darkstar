## Why

The executor tick crashes completely if a Home Assistant service call times out (e.g., when setting water heater temperature). The `aiohttp` library raises an `asyncio.TimeoutError` which bubbles up unhandled because `HAClient.call_service` only catches `aiohttp.ClientError`, not `TimeoutError`. Furthermore, the water heater control logic in `engine.py` is executed outside the main `try...except` block that protects the rest of the profile actions, so the unhandled timeout crashes the entire tick cycle.

## What Changes

- Catch `TimeoutError` in `HAClient.call_service` in `executor/actions.py` and wrap it in `HACallError` so it is handled uniformly alongside other network errors.
- Add retry-with-backoff to `HAClient.call_service`, consistent with `get_state`. Write operations to HA are idempotent (setting the same value twice is safe), and the retry helper already exists.
- Move the water heater control call in `executor/engine.py` inside the `try...except` block, and fix that block so it does not wipe previously collected results on error — instead, it appends a failed `ActionResult` for the specific step that failed.
- Add a unit test covering `TimeoutError → HACallError` conversion in `call_service`.

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- None (This is an implementation bug fix, not a change in capability requirements)

## Impact

- `executor/actions.py`: Modified `call_service` to catch `TimeoutError` and use retry-with-backoff.
- `executor/engine.py`: Refactored error handling in `_tick` so isolated failures do not abort the full tick or corrupt the result log.
- `tests/executor/test_executor_actions.py`: New test for timeout error handling in `call_service`.
