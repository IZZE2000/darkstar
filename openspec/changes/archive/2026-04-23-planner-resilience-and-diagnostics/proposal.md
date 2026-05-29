## Why

A user reported "Darkstar does not even work for them, they say they don't get a plan". The production log reveals that the MILP planner silently fails every minute on two distinct infeasibilities: (1) the solver treats `battery.max_soc_percent` as a hard upper bound while `initial_soc` is an equality, so any time the real battery is above the configured ceiling the LP is structurally infeasible; (2) an EV charger is registered with `max_power_kw=0` because the config field is missing and defaults silently to zero, so the planner can never schedule it. Both failures surface to the user only as a grey "Planner failed" toast that disappears after 3 seconds, with no reason, no fix hint, and no retry visibility. The planner keeps re-failing every 60s forever.

This change makes the planner never fail silently: infeasibility caused by soft constraints is eliminated at the solver level, broken configuration is caught with a typed error before the solver runs, and every failure produces a persistent banner with a specific reason, a fix hint, structured diagnostics, and a live retry countdown. It also patches two config-grade bugs (0 kW EV registration, vague sensor tooltips that led the user to pick a lifetime energy counter for `total_load_consumption`).

## What Changes

- **BREAKING**: `battery.max_soc_percent` is now a *soft* penalty ceiling in the Kepler MILP, mirroring how `min_soc_percent` already works. Plans that start with SoC above the ceiling now succeed and begin with a discharge action instead of failing. Behavior under normal conditions (SoC ≤ max) is unchanged.
- Add a deterministic pre-flight validator that runs before Kepler and returns typed errors for invalid battery config, out-of-range initial SoC, EV chargers missing `max_power_kw`, EV deadlines in the past, missing price data, missing forecast data, and NaN/Inf in prices/forecasts.
- Add a typed `PlannerErrorCode` enum with per-code user message and fix-hint methods. Replace the generic `ValueError("Planner generated invalid schedule (safety guard)")` with structured errors that carry code + solver status + diagnostics payload.
- EV chargers configured with `max_power_kw ≤ 0` are registered *as disabled* (visible in UI, skipped by planner) with a HealthIssue instead of silently defaulting to 0 kW.
- Extend `HealthIssue` with optional `code: str`, `details: dict`, and `retry_in_s: int` fields to carry structured diagnostic data.
- Add `check_planner()` to `HealthChecker` that reports the last planner failure as a HealthIssue with category `planner`.
- Track `last_error`, `last_error_code`, `last_error_details`, and `next_retry_at` on `PlannerService`. Suspend automatic retries after config-blocking errors (codes that require user action) until settings are saved; apply exponential backoff (60s → 5min) for transient errors; normal 60s cadence for invariant violations. On backend restart, perform one retry attempt before re-entering suspended state.
- Extend `SystemAlert` to render structured health issues with a `details` drawer and a live retry countdown. Banner is dismissible in the sense that the user can collapse it, but it cannot be hidden entirely — a small indicator remains visible until the underlying failure clears.
- Add `components/PlannerErrorDetails.tsx` drawer showing error code, human message, fix hint, diagnostics table, live retry countdown, and a "Copy diagnostic bundle" button.
- Remove the 3-second "Planner failed" toast from `QuickActions.tsx` (superseded by persistent banner).
- Update `config-help.json` tooltips: `battery.max_soc_percent` is documented as soft/preference; EV `max_power_kw` is documented as required; all `input_sensors.total_*` tooltips explain that a cumulative energy counter (kWh) is required and that power sensors (W/kW) are wrong.
- Update `config.default.yaml` comments to reflect the soft semantics of `max_soc_percent`.
- Hardcoded pre-flight thresholds: initial SoC staleness warning at 30 minutes; no new config surface introduced.

## Capabilities

### New Capabilities
- `planner-diagnostics`: Structured error codes for planner failures, health integration via an extended `HealthIssue` record (adds `code`, `details`, `retry_in_s`), planner health check reading from `PlannerService` state, smart retry policy (suspend/backoff/normal) keyed on error code, persistent error banner with details drawer and live retry countdown.

### Modified Capabilities
- `planner`: Max-SoC becomes a soft constraint with a penalty mirroring `MIN_SOC_PENALTY`; new pre-flight validator runs before Kepler and raises typed errors for invalid battery config, out-of-range initial SoC, missing price/forecast data, and NaN/Inf values; the generic `ValueError` safety-guard exception is replaced with structured errors.
- `per-device-ev-scheduling`: EV chargers with `max_power_kw ≤ 0` are registered as disabled (visible in UI, excluded from MILP) with a corresponding HealthIssue, instead of silently defaulting to 0 kW.
- `sensor-configuration`: Tooltip strings for `battery.max_soc_percent`, EV `max_power_kw`, and the six `input_sensors.total_*` sensors are rewritten to be explicit about units, required attributes, and required sensor shape. No runtime validation added (deferred).

## Impact

Affected code:
- `planner/solver/kepler.py`: soft max-SoC slack variable + penalty; replace `ValueError` with typed errors
- `planner/solver/types.py`: no changes to existing fields; new fields added in `planner/errors.py`
- `planner/pipeline.py`: wire new pre-flight validator; propagate typed errors
- `planner/preflight.py`: NEW — pre-flight validator module
- `planner/errors.py`: NEW — `PlannerErrorCode` enum and helpers
- `backend/loads/service.py`: register EVs with missing power as disabled
- `backend/health.py`: extend `HealthIssue`; add `check_planner()`
- `backend/services/planner_service.py`: track last error state + retry policy; populate structured fields
- `frontend/src/components/SystemAlert.tsx`: support `code`, `details`, `retry_in_s`, "View details" link
- `frontend/src/components/PlannerErrorDetails.tsx`: NEW — details drawer
- `frontend/src/components/QuickActions.tsx`: remove toast-only error handler
- `frontend/src/config-help.json`: tooltip updates
- `config.default.yaml`: comment updates for soft semantics

Affected APIs:
- `GET /api/health` response: `issues[]` items gain optional `code`, `details`, `retry_in_s` fields (backwards compatible — additive)
- WebSocket `planner_error` event payload: gains `code` and `details` fields (still emitted; frontend now reads from health instead of binding to this toast)

Dependencies: none added or removed.

Out of scope (tracked in `docs/BACKLOG.md`):
- Inverter AC-limit constraint that currently overcounts PV-to-battery DC path — see the `[Planner] Inverter AC Limit Constraint Overcounts PV-to-Battery Path` backlog entry.
- Home Assistant sensor attribute validation at selection time (device_class / state_class / unit checks) — deferred; improved tooltips are the mitigation for now.
