## Context

Three bugs all converge on the same symptom: the planner silently enters a permanent infeasibility loop with no visible error on the dashboard.

**Root cause chain:**
1. The `max_inverter_ac_kw` LP constraint is written as `discharge[t] + pv_forecast[t] <= inverter_ac_kwh`. When the ML PV residual pushes `pv_forecast` above `inverter_ac_kwh` for any slot, the constraint requires `discharge <= negative_number`, which contradicts `discharge >= 0`. The LP is infeasible before the solver even starts.
2. When infeasibility is caught, the planner service error paths set `_current_phase = None` without emitting a `"failed"` WebSocket phase. The frontend is left waiting forever for a terminal phase that never comes.
3. `SOLVER_INFEASIBLE` is classified as `severity="warning"` in the health system. The `SystemAlert` component renders `null` when `health.healthy === true`. Since `healthy = not has_critical` (warnings don't affect it), the warning issue exists in `health.issues` but is never displayed.

## Goals / Non-Goals

**Goals:**
- The solver MUST never produce an infeasible LP due to PV forecast exceeding inverter capacity
- The frontend MUST show a planner warning banner even when the system is otherwise healthy
- The frontend MUST receive a terminal phase on planner failure so the UI does not freeze

**Non-Goals:**
- Fixing the ML model's tendency to produce inflated PV residuals (separate data quality issue)
- Changing the retry cadence or severity classification of `SOLVER_INFEASIBLE`
- Changing the meaning of `health.healthy` (it correctly reflects only critical issues)

## Decisions

### Decision: Clamp discharge upper bound, not PV forecast

**Options considered:**
- A: Pre-clip `pv_forecast` to `inverter_ac_kwh` before building the LP (would affect energy balance too)
- B: Rewrite constraint as `discharge[t] <= max(0.0, inverter_ac_kwh - s.pv_kwh)` — surgical, correct

**Decision: Option B.** The constraint's intent is "inverter AC output (PV + discharge) ≤ inverter rated output". When PV already fills the inverter, discharge must be zero — exactly what `max(0.0, ...)` expresses. The PV forecast constant in the energy balance constraint is unaffected.

### Decision: SystemAlert shows warnings independently of `health.healthy`

**Options considered:**
- A: Change `healthy` to `not (has_critical or has_warning)` — too aggressive, small sensor warnings would mark whole system unhealthy
- B: Remove the `if health.healthy return null` guard entirely and let the component always render if issues exist

**Decision: Option B.** The `health.healthy` flag correctly controls the global health indicator. The `SystemAlert` should render whenever there are issues to show (critical OR warning), regardless of the healthy flag. One condition change: `if (!health || (!health.healthy === false && issues.length === 0))` → simplified as: only return null when there are no issues.

### Decision: Emit `"failed"` phase before clearing `_current_phase`

No alternatives considered. Adding `await self._emit_progress("failed")` in both `except PlannerError` and `except Exception` blocks before `self._current_phase = None` is the minimal correct fix.

## Risks / Trade-offs

- **Inverter fix**: The change makes `discharge[t]` more constrained when PV is high (forced to 0 when pv >= inverter_ac). This is correct physical behavior — the inverter can't simultaneously push PV and discharge at the same time when already at capacity. No behavior regression on normal days.

- **SystemAlert always showing warnings**: If multiple warning-level issues accumulate (e.g., sensor issues + planner warning), the banner may feel noisy. This is acceptable — the banner already supports collapse and the alternative is silent failures.

- **"failed" phase on frontend**: The frontend must handle a new `"failed"` phase value. Existing consumers that only know `"complete"` and phase names up to `"solving"` will need to treat `"failed"` as a terminal state (not an error in itself).

## Migration Plan

All three changes are non-breaking and backward compatible. No data migration needed. Deploy as a single atomic commit.
