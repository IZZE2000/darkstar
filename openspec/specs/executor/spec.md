## Purpose

The Executor is responsible for executing scheduled energy management decisions by controlling Home Assistant entities (inverters, water heaters, EV chargers). It bridges the planner's decisions with physical device control.

## Requirements

### Requirement: Executor handles Home Assistant service failures gracefully
The executor SHALL NOT crash when Home Assistant service calls fail or time out. Any errors encountered when communicating with Home Assistant MUST be logged and wrapped in `HACallError` so the executor tick can continue safely and the result log remains intact.

#### Scenario: Home Assistant API times out during a service call
- **WHEN** any `call_service` HTTP request takes longer than the configured timeout
- **THEN** the timeout is caught and wrapped as `HACallError`
- **AND THEN** the retry-with-backoff mechanism attempts up to 3 times before giving up
- **AND THEN** if all retries are exhausted, `HACallError` is raised to the caller

#### Scenario: Home Assistant API times out during water heater control
- **WHEN** the `set_water_temp` service call fails after all retries
- **THEN** the water heater action is recorded as a failed `ActionResult` in the tick result log
- **AND THEN** the rest of the executor tick continues normally (profile actions are still executed)
- **AND THEN** no previously collected action results are lost

### Requirement: call_service uses retry-with-backoff
`HAClient.call_service` SHALL use the same `_retry_with_backoff` mechanism as `get_state`, with 3 attempts and a 1-second base delay, treating `TimeoutError` and `aiohttp.ClientError` as retryable.

### Requirement: Timeout handling is tested
A unit test SHALL exist verifying that a `TimeoutError` raised by the HTTP session during `call_service` results in an `HACallError` being raised by the client.
