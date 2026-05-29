## ADDED Requirements

### Requirement: Executor background loop cleans up async resources on exit

The `_async_run_loop` method SHALL wrap its main loop in a `try/finally` block that cancels all tracked background tasks and closes the `HAClient` session on every exit path (normal stop, early return, exception).

#### Scenario: Normal shutdown closes session
- **WHEN** the stop event is set and the while loop exits
- **THEN** all in-flight background tasks are cancelled
- **AND THEN** `ha_client.close()` is called
- **AND THEN** no `Unclosed client session` warning is logged

#### Scenario: Early return during wait closes session
- **WHEN** the stop event is set during the wait-sleep loop and an early `return` is executed
- **THEN** the `finally` block still executes
- **AND THEN** `ha_client.close()` is called

#### Scenario: Uncaught exception does not mask original error
- **WHEN** an uncaught exception escapes the while loop
- **AND THEN** the `finally` block raises while closing the session
- **THEN** the close error is logged as a warning, not raised
- **AND THEN** the original exception propagates to the caller

### Requirement: Background tasks are cancelled before session close

The `finally` block SHALL cancel all tasks in `_background_tasks` and await their completion (with `return_exceptions=True`) before calling `ha_client.close()`.

#### Scenario: In-flight water boost task cancelled on shutdown
- **WHEN** a water boost task is running when the stop event is set
- **THEN** the task is cancelled before the session is closed
- **AND THEN** no `RuntimeError: Session is closed` occurs

#### Scenario: Empty task set is a no-op
- **WHEN** no background tasks are running
- **THEN** the cancellation step is skipped
- **AND THEN** `ha_client.close()` proceeds normally
