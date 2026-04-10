## 1. HAClient Timeout Error Handling

- [x] 1.1 Catch `TimeoutError` in `HAClient.call_service` in `executor/actions.py` and wrap it in `HACallError`

## 2. HAClient call_service Retry

- [x] 2.1 Wrap the HTTP call in `call_service` with `_retry_with_backoff` (same parameters as `get_state`: 3 attempts, 1 s base delay)

## 3. Executor Tick Robustness

- [x] 3.1 Move `set_water_temp` call and its `action_results.append` inside the `try...except` block in `_tick`
- [x] 3.2 Fix the `except` handler to *append* a failed `ActionResult` instead of replacing the entire `action_results` list

## 4. Tests

- [x] 4.1 Add `test_call_service_timeout_raises_ha_call_error` to `TestHAClientCallService` in `tests/executor/test_executor_actions.py`
