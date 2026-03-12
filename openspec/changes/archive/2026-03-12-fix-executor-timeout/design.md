## Context

The `HAClient` sends HTTP requests to Home Assistant using `aiohttp`. Occasionally, Home Assistant may take too long to respond, leading `aiohttp` to raise an `asyncio.TimeoutError`. Currently, this exception is not caught within `call_service`, meaning it bubbles up to the caller unchecked.

In `_tick`, `dispatcher.execute(decision)` is wrapped in a `try...except Exception` block. However, two problems exist: (1) `set_water_temp` is called *before* this block, so a timeout there crashes the whole tick; (2) the `except` handler replaces the entire `action_results` list with a single error entry, which would discard the water heater result that was already appended.

## Goals / Non-Goals

**Goals:**
- Gracefully handle `TimeoutError` inside `HAClient.call_service`.
- Make `call_service` as resilient as `get_state` by adding retry-with-backoff.
- Prevent isolated action failures from crashing the tick or corrupting the result log.
- Cover the new timeout path with a unit test.

**Non-Goals:**
- Changing the timeout duration (remains 5 seconds as configured).
- Refactoring the `ActionDispatcher` structure.

## Decisions

1. **Catch `TimeoutError` in `call_service`:**
   Explicitly catch `TimeoutError` (the built-in, which covers `asyncio.TimeoutError` in Python 3.11+) alongside `aiohttp.ClientError`, translating it into `HACallError`. This makes all callers handle timeouts identically to connection errors.

2. **Add retry-with-backoff to `call_service`:**
   `get_state` already uses `_retry_with_backoff`. `call_service` is the critical write path and should be equally resilient. All HA write operations in this system are idempotent (setting the same value twice produces the same result), so retrying is safe. Use the same parameters as `get_state` (3 attempts, 1 s base delay).

3. **Move `set_water_temp` inside the execution `try` block and fix the `except` handler:**
   Move the `set_water_temp` call and its `action_results.append` inside the `try` block. Change the `except` handler so that on failure it *appends* a single failed `ActionResult` rather than replacing the entire list. This preserves all results collected before the failure and allows the tick to continue normally.

4. **Add a unit test for `TimeoutError` in `call_service`:**
   Add `test_call_service_timeout_raises_ha_call_error` to `TestHAClientCallService`. Simulate a `TimeoutError` from the mock session and assert that `HACallError` is raised with an appropriate `exception_type`.

## Risks / Trade-offs

- **Retry on write:** Retrying a write that actually succeeded but whose HTTP response timed out would result in the same value being written twice. For setting temperatures and mode selects this is harmless. Acceptable risk.
- Minimal overall risk. These are strictly robustness improvements with no behaviour change under normal conditions.
