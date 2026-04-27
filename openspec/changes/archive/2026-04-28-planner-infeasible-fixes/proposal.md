## Why

The planner intermittently enters a permanent `SOLVER_INFEASIBLE` failure loop when the ML PV forecast exceeds the inverter AC output limit — a constraint that was written in a way that becomes mathematically impossible. When this happens, the dashboard shows no error (warnings are silenced by the health system) and the UI freezes at "solving" indefinitely.

## What Changes

- Fix the `max_inverter_ac_kw` constraint in the solver so it never produces an impossible (negative) upper bound on discharge when PV forecast exceeds inverter capacity
- Fix the health system so planner warning-level issues are visible on the dashboard even when the system is otherwise "healthy"
- Fix the planner service to emit a `"failed"` progress phase on error so the UI does not get stuck at "solving"

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `planner`: Inverter AC constraint must never become infeasible when PV forecast exceeds inverter limit
- `planner-diagnostics`: Planner warning issues must be visible on the dashboard; the planner must emit a terminal phase on failure

## Impact

- `planner/solver/kepler.py` — one-line constraint fix
- `backend/health.py` — severity or healthy-flag logic
- `frontend/src/components/SystemAlert.tsx` — render warnings regardless of `health.healthy`
- `backend/services/planner_service.py` — emit `"failed"` phase in error paths
