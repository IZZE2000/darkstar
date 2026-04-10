## 1. Fix Planner Crash

- [x] 1.1 Update `inputs.py` (line 942) to correctly escape the percent sign (`0%%`).
- [x] 1.2 Grep `inputs.py` for any other bare `%` in logger calls to confirm no further instances exist (`grep -n "logger.*%[^%sd(]" inputs.py`).
- [x] 1.3 Run the lint suite (`./scripts/lint.sh`) and confirm zero errors before committing.

## 2. Improve Error Notifications

- [x] 2.1 Update `planner_service.py` `run_once` generic exception handler (line 144) to prepend `type(e).__name__` to the stringified error payload (e.g. `f"{type(e).__name__}: {str(e)}"`). Confirm the other four `except` blocks in the file are untouched.
- [x] 2.2 Verify that the frontend WebSocket `planner_error` event payload reflects the enriched message format on failure.

## 3. Add Test Coverage (Bonus)

- [x] 3.1 Add test `test_ev_soc_fallback_logging_no_crash` in `tests/test_inputs_ha_client.py` to verify EV SoC fallback logging with escaped percent sign works correctly.
- [x] 3.2 Add test `test_planner_service_error_includes_exception_type` in `tests/planner/test_scheduler_services.py` to verify error messages include exception type.
