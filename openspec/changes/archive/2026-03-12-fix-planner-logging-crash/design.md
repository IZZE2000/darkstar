## Context

The planner service is crashing due to a `ValueError: incomplete format` caused by an unescaped percent sign in `inputs.py` logging statement. The error catching mechanism in `planner_service.py` emits the exception to the frontend WebSocket as a string (`str(e)`), which only provides `"incomplete format"` and lacks context.

## Goals / Non-Goals

**Goals:**
- Fix the logging statement syntax error in `inputs.py`.
- Improve the error message emitted over WebSocket when the planner fails, making it more informative for the frontend.

**Non-Goals:**
- Comprehensive overhaul of the logging system.
- Full refactoring of error handling in `planner_service.py` beyond the specific WebSocket event payload.

## Decisions

- **Escape Percent Sign:** Update `0%` to `0%%` in the logging string in `inputs.py` to correctly escape it when using standard python percent-formatting.
- **Enrich Error Payload:** Update the `run_once` generic exception handler in `planner_service.py` (line 144) to include the exception type in the error message (e.g., `f"{type(e).__name__}: {str(e)}"`). This is the only handler that feeds into `PlannerResult.error` and then surfaces over WebSocket. The four other `except` blocks in the file handle internal failures (WebSocket emit errors, slot counting) and already log with `logger.warning`/`logger.exception` — enriching those is out of scope.

## Risks / Trade-offs

- **Risk:** Other similar string formatting issues might exist in `inputs.py`. **Mitigation:** A grep for bare `%` in logger calls across `inputs.py` **must** be performed as part of this change. Based on review, only line 942 is affected, but this must be confirmed before closing the task.
