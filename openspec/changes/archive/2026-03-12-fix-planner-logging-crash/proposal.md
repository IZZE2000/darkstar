## Why

The planner crashes with a `ValueError: incomplete format` when parsing a logging message in `inputs.py` due to an unescaped percent sign (`%`). Furthermore, the resulting error notification displayed on the frontend is unhelpful because it only provides the string representation of the error (`str(e)`), which is merely `"incomplete format"` and lacks context.

## What Changes

- Fix the logging statement in `inputs.py` to correctly escape percent signs (e.g., `0%%`).
- Update `planner_service.py` exception handling to emit a more descriptive error payload (like including the exception type `type(e).__name__`) over the WebSocket so the frontend shows a clearer message.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
None.

## Impact

- `backend/services/planner_service.py`: Improved error handling logic for WebSocket notifications.
- `inputs.py`: Logging format syntax corrected.
