## 1. Error code taxonomy (backend)

- [x] 1.1 Create `planner/errors.py` with `PlannerErrorCode` enum (string-valued) containing exactly these members: `CONFIG_INVALID`, `INITIAL_SOC_OUT_OF_RANGE`, `DATA_STALE`, `EV_MISSING_POWER`, `EV_INVALID_CAPACITY`, `EV_DEADLINE_PAST`, `PRICES_UNAVAILABLE`, `FORECAST_UNAVAILABLE`, `NUMERIC_INVALID`, `SOLVER_INFEASIBLE`, `SOLVER_TIMEOUT`, `SOLVER_UNDEFINED`, `INVALID_SCHEDULE`, `UNKNOWN`.
- [x] 1.2 Add `user_message(code: PlannerErrorCode) -> str` function in `planner/errors.py` returning a short banner-suitable string for each code.
- [x] 1.3 Add `fix_hints(code: PlannerErrorCode) -> list[str]` function in `planner/errors.py` returning an actionable list for each code (≥1 hint per code).
- [x] 1.4 Define `PlannerError(Exception)` class in `planner/errors.py` with fields `code: PlannerErrorCode`, `message: str`, `fix_hint: str`, `details: dict[str, Any]` and a `to_dict()` method.
- [x] 1.5 Add a `is_config_blocking(code: PlannerErrorCode) -> bool` helper returning `True` for `CONFIG_INVALID`, `EV_MISSING_POWER`, `EV_INVALID_CAPACITY`, `INITIAL_SOC_OUT_OF_RANGE`.
- [x] 1.6 Add `is_transient(code: PlannerErrorCode) -> bool` helper returning `True` for `PRICES_UNAVAILABLE`, `FORECAST_UNAVAILABLE`, `SOLVER_TIMEOUT`.
- [x] 1.7 Add `is_warning_only(code: PlannerErrorCode) -> bool` helper returning `True` for `DATA_STALE`, `EV_DEADLINE_PAST`.
- [x] 1.8 Unit test in `tests/planner/test_errors.py`: every enum member has non-empty `user_message` and at least one `fix_hints` entry.
- [x] 1.9 Unit test: `is_config_blocking`, `is_transient`, `is_warning_only` cover every enum member exactly once (mutually exclusive and complete).

## 2. Soft max-SoC constraint in Kepler solver

- [x] 2.1 In `planner/solver/kepler.py`, add `MAX_SOC_PENALTY = 1000.0` constant next to `MIN_SOC_PENALTY`.
- [x] 2.2 Create `soc_overshoot` LpVariable.dicts (range `T+1`, `lowBound=0.0`) similarly to how `soc_violation` is created.
- [x] 2.3 Replace `prob += soc[t] <= max_soc_kwh` (both the per-slot line and the terminal line) with `prob += soc[t] <= max_soc_kwh + soc_overshoot[t]`.
- [x] 2.4 Add `MAX_SOC_PENALTY * pulp.lpSum(soc_overshoot)` term into the objective aggregation (same place `MIN_SOC_PENALTY * lpSum(soc_violation)` is added).
- [x] 2.5 Verify `initial_soc` clipping (line 218) still uses `max(0.0, min(config.capacity_kwh, input_data.initial_soc_kwh))` — no change required, but confirm it does NOT clip to `max_soc_kwh`.
- [x] 2.6 Unit test in `tests/planner/test_kepler_soft_max_soc.py`: `initial_soc > max_soc_kwh` yields `Optimal` status with non-zero `soc_overshoot[0]` and a discharge/export action in slot 0.
- [x] 2.7 Unit test: `initial_soc <= max_soc_kwh` yields `Optimal` with all `soc_overshoot[t] == 0`.
- [x] 2.8 Unit test: lower bound (soc_violation) behavior is unchanged when `initial_soc < min_soc_kwh`.

## 3. Pre-flight validator

- [x] 3.1 Create `planner/preflight.py` with a `run_preflight(input_data, config) -> None` function that raises `PlannerError` on blocking failures and logs warnings otherwise.
- [x] 3.2 Implement `check_battery_config(config) -> None`: raises `CONFIG_INVALID` when `min_soc_percent >= max_soc_percent`, when `capacity_kwh <= 0` with battery enabled, or when `max_charge_power_kw <= 0` / `max_discharge_power_kw <= 0` with battery enabled. Details payload includes the offending field names and values.
- [x] 3.3 Implement `check_initial_soc(input_data, config) -> None`: raises `INITIAL_SOC_OUT_OF_RANGE` when `initial_soc_kwh < 0` or `initial_soc_kwh > capacity_kwh`. Details include `initial_soc_kwh` and `capacity_kwh`.
- [x] 3.4 Implement `check_soc_staleness(input_data) -> None`: logs a `DATA_STALE` warning (does not raise) when the SoC reading timestamp is more than 30 minutes old. Threshold hardcoded as `SOC_STALENESS_WARNING_MINUTES = 30`.
- [x] 3.5 Implement `check_ev_chargers(config) -> None`: for each plugged-in charger, raise `EV_MISSING_POWER` when `max_power_kw <= 0` and raise `EV_INVALID_CAPACITY` when `battery_capacity_kwh <= 0`. Details include the charger ID.
- [x] 3.6 Implement `check_ev_deadlines(config, now) -> None`: log an `EV_DEADLINE_PAST` warning (does not raise) for any charger whose deadline is before `now`. Populate details with charger ID and deadline timestamp.
- [x] 3.7 Implement `check_price_data(input_data, now) -> None`: raise `PRICES_UNAVAILABLE` when fewer than 4 hours of price slots exist from `now` forward. Details include the observed price horizon bounds.
- [x] 3.8 Implement `check_forecast_data(input_data) -> None`: raise `FORECAST_UNAVAILABLE` when forecast data is empty or does not cover the planning horizon. Details include observed horizon bounds.
- [x] 3.9 Implement `check_numeric_sanity(input_data) -> None`: raise `NUMERIC_INVALID` when any price or forecast value is NaN or Inf. Details include the offending field, slot index, and observed value.
- [x] 3.10 Wire the checks into `run_preflight` in the order: battery → initial SoC → SoC staleness (warning) → EV chargers → EV deadlines (warning) → price data → forecast data → numeric sanity. Blocking checks raise on first failure; warnings continue.
- [x] 3.11 In `planner/pipeline.py` `generate_schedule()`, call `run_preflight(input_data, config)` immediately before the Kepler solve step.
- [x] 3.12 Unit test in `tests/planner/test_preflight.py`: one failing case and one passing case per check (17 tests total).
- [x] 3.13 Unit test: blocking checks halt; pre-flight never raises for warning-only conditions; warning details are logged.

## 4. Replace generic ValueError safety guard

- [x] 4.1 In `planner/pipeline.py:753`, replace `raise ValueError("Planner generated invalid schedule (safety guard)")` with `raise PlannerError(code=PlannerErrorCode.INVALID_SCHEDULE, ...)` carrying diagnostics `{"solver_status": ..., "initial_soc_kwh": ..., "max_soc_kwh": ..., "capacity_kwh": ...}`.
- [x] 4.2 In `planner/solver/kepler.py`, after `prob.solve()`, map PuLP status values to `PlannerErrorCode`: `LpStatusInfeasible` → `SOLVER_INFEASIBLE`, `LpStatusUndefined` → `SOLVER_UNDEFINED`, and detect `solve_duration >= timeLimit` → `SOLVER_TIMEOUT`. Raise `PlannerError` with the solver status string in details.
- [x] 4.3 Unit test: running Kepler with a deliberately infeasible constraint (e.g., conflicting hard lock) raises `PlannerError` with code `SOLVER_INFEASIBLE` and populated solver status.
- [x] 4.4 Unit test: `INVALID_SCHEDULE` path runs when Kepler returns an optimal but malformed result; diagnostics include all four keys.

## 5. PlannerService retry policy

- [x] 5.1 In `backend/services/planner_service.py`, add attributes to `PlannerService`: `_last_error_code: PlannerErrorCode | None`, `_last_error_at: datetime | None`, `_next_retry_at: datetime | None`, `_consecutive_failures: int = 0`, `_retry_suspended: bool = False`.
- [x] 5.2 Extend `PlannerResult` dataclass with optional `error_code: str | None = None`, `error_details: dict[str, Any] | None = None`, `fix_hint: str | None = None`.
- [x] 5.3 When `run_once()` catches a `PlannerError`, populate the new `PlannerResult` fields from the exception.
- [x] 5.4 Implement `_apply_retry_policy(code: PlannerErrorCode)` method: for config-blocking codes set `_retry_suspended=True` and `_next_retry_at=None`; for transient codes compute exponential backoff (60, 120, 240, 300 cap); for invariant codes set `_next_retry_at=now+60s`; for warning-only codes do nothing (treat as success for retry purposes).
- [x] 5.5 On successful run, reset `_consecutive_failures=0`, `_retry_suspended=False`, `_last_error_code=None`.
- [x] 5.6 Add method `clear_retry_suspension()` that sets `_retry_suspended=False` and schedules an immediate next retry.
- [x] 5.7 Add `retry_in_s` property returning seconds until `_next_retry_at` (or `None` if suspended or in future indefinitely).
- [x] 5.8 Subscribe `PlannerService` to a `settings_saved` event (emit point already exists in settings router; if not, create one) and call `clear_retry_suspension()` on receipt.
- [x] 5.9 Ensure `SchedulerService` (or the scheduling loop) consults `planner_service.next_retry_at` and `retry_suspended` before running; skip scheduling when suspended or before the next retry time.
- [x] 5.10 On backend startup after service initialization, perform exactly one planner attempt regardless of prior persisted suspension state (suspension state is in-memory and resets on restart — confirm this is the case and document).
- [x] 5.11 Unit test: config-blocking failure sets `_retry_suspended=True`; `clear_retry_suspension()` called manually resets it and schedules immediate retry.
- [x] 5.12 Unit test: three consecutive transient failures produce backoff intervals of approximately 60s, 120s, 240s; fourth caps at 300s; success resets to 60s baseline.
- [x] 5.13 Unit test: invariant failures use 60s cadence; warning-only codes do not set `_last_error_code`.

## 6. HealthIssue structured fields

- [x] 6.1 In `backend/health.py`, extend `@dataclass class HealthIssue` with three optional fields: `code: str | None = None`, `details: dict[str, Any] | None = None`, `retry_in_s: int | None = None`.
- [x] 6.2 Update `HealthIssue.to_dict()` to include `code`, `details`, `retry_in_s` only when non-None.
- [x] 6.3 In `frontend/src/components/SystemAlert.tsx`, extend `HealthIssue` interface with the same three optional fields.
- [x] 6.4 In `frontend/src/lib/api.ts`, confirm `HealthStatus` / `HealthIssue` types mirror the backend additions.
- [x] 6.5 Unit test (backend): `HealthIssue` without the new fields serializes without those keys (backwards compat).
- [x] 6.6 Unit test (backend): `HealthIssue` with all three fields serializes them correctly.
- [x] 7.1 In `backend/health.py`, add `check_planner(self) -> list[HealthIssue]` method to `HealthChecker`.
- [x] 7.2 `check_planner()` reads from `planner_service` singleton: if `_last_error_code is None`, return `[]`. Otherwise return a single `HealthIssue` with `category="planner"`, `code=_last_error_code.value`, `details=planner_service._last_error_details`, `retry_in_s=planner_service.retry_in_s`, `message=user_message(_last_error_code)`, `guidance=fix_hints(_last_error_code)[0]` (first hint as single-line guidance).
- [x] 7.3 Severity is `"critical"` when `is_config_blocking(code)` else `"warning"`.
- [x] 7.4 Wire `check_planner()` into `HealthChecker.check_all()`.
- [x] 7.5 Unit test: no planner error → no issue returned.
- [x] 7.6 Unit test: config-blocking error → critical issue with correct code and details.
- [x] 7.7 Unit test: transient error → warning issue with positive `retry_in_s`.

## 8. EV register-as-disabled

- [x] 8.1 In `backend/loads/service.py`, extend `DeferrableLoad` (or its equivalent dataclass) with an optional `disabled_reason: str | None = None` field.
- [x] 8.2 In the EV registration loop (service.py around line 95–132), when `nominal_power_kw <= 0` for an enabled charger, call `register_load(load)` with `disabled_reason="missing_power_kw"` instead of the silent 0.0 fallback.
- [x] 8.3 Emit a `HealthIssue` with `category="ev"`, `severity="critical"`, `code="EV_MISSING_POWER"`, `entity_id=load_id`, `details={"charger_id": load_id, "max_power_kw": 0.0}` when this path is taken. The issue must be persistent until resolved (add to HealthChecker state, not transient).
- [x] 8.4 In `planner/solver/adapter.py` (around line 156), filter out EV chargers where `disabled_reason is not None` (or where the LoadService reports disabled) when building `KeplerConfig.ev_chargers`.
- [x] 8.5 Expose `disabled_reason` in the load registry API response (whichever endpoint the frontend already consumes for load listings).
- [x] 8.6 On settings save, reload load configuration; a previously disabled charger with a newly valid `max_power_kw` is re-registered without `disabled_reason` and its HealthIssue cleared.
- [x] 8.7 Unit test: EV config with missing `max_power_kw` → load is registered with `disabled_reason="missing_power_kw"` and a HealthIssue is emitted.
- [x] 8.8 Unit test: EV config with `max_power_kw: 0` → same behavior.
- [x] 8.9 Unit test: EV config with `max_power_kw: 11.0` → registered without `disabled_reason`, no HealthIssue.
- [x] 8.10 Unit test: adapter excludes disabled chargers from `KeplerConfig.ev_chargers`.
- [x] 8.11 Unit test: fixing the config path re-registers and clears the HealthIssue without a restart.

## 9. Frontend: persistent banner + details drawer

- [x] 9.1 In `frontend/src/components/SystemAlert.tsx`, for any `HealthIssue` with a non-null `details` payload render a "View details" button alongside the existing message/guidance.
- [x] 9.2 Clicking "View details" opens a drawer by setting selected-issue state and rendering `<PlannerErrorDetails issue={issue} onClose={...}/>`.
- [x] 9.3 Create `frontend/src/components/PlannerErrorDetails.tsx` implementing a right-side drawer using the project's existing drawer pattern (reuse whatever drawer primitive is already in the codebase; do not introduce a new one).
- [x] 9.4 Drawer content: error code rendered as monospace chip, human message + fix hint text, diagnostics table iterating `details` key/value pairs (with long strings truncated and copy-on-click), live retry countdown, "Copy diagnostic bundle" button, "Open Settings" link when `code` is config-blocking.
- [x] 9.5 Implement a `useRetryCountdown(retry_in_s: number | null)` hook that returns a seconds-remaining integer, ticking down once per second, resetting to a new value when `retry_in_s` prop changes, and showing "Suspended — fix configuration" when `retry_in_s === null` and the code is config-blocking.
- [x] 9.6 Implement a `redactSecrets(details: Record<string, unknown>) -> Record<string, unknown>` utility that recursively replaces values under keys matching `/token|api_key|password|secret/i` with the string `***`. Apply it both to the displayed diagnostics table and the clipboard bundle.
- [x] 9.7 "Copy diagnostic bundle" copies a JSON string of the redacted issue (code, message, guidance, entity_id, details, retry_in_s, timestamp) to `navigator.clipboard`.
- [x] 9.8 Add a collapse toggle to the banner: clicking it shrinks the banner to a one-line indicator showing an icon and the error code; clicking the indicator re-expands to full banner. The banner cannot be fully hidden — the indicator remains visible while the issue is present in `/api/health`.
- [x] 9.9 In `frontend/src/components/QuickActions.tsx`, remove the `socket.on('planner_error', handlePlannerError)` binding and the `handlePlannerError` function. Remove the `socket.off('planner_error', ...)` unsubscribe. Remove the `feedback` toast-setting call for planner errors.
- [x] 9.10 Unit test (Vitest/Jest): `useRetryCountdown` decrements once per second and resets when prop changes.
- [x] 9.11 Unit test: `redactSecrets` redacts values under secret-matching keys at any nesting depth.
- [x] 9.12 Component test: `PlannerErrorDetails` with a populated issue renders code, message, fix hint, diagnostics table, and copy button; copy button calls `navigator.clipboard.writeText` with a JSON string containing the redacted issue.
- [x] 9.13 Component test: `SystemAlert` renders "View details" only when `issue.details` is non-null; renders collapse toggle and collapses/restores banner correctly.

## 10. Tooltip and config-comment updates

- [x] 10.1 In `frontend/src/config-help.json`, rewrite the `battery.max_soc_percent` tooltip to be explicit that the value is a **soft** penalty ceiling, the BMS enforces the absolute limit, and starting above the ceiling triggers a discharge action rather than a failure.
- [x] 10.2 In `frontend/src/config-help.json`, rewrite the `system.battery.max_soc_percent` tooltip with identical guidance to 10.1.
- [x] 10.3 In `frontend/src/config-help.json`, rewrite the `input_sensors.total_load_consumption` tooltip to explicitly describe: a cumulative monotonically-increasing energy counter; `device_class: energy`; units kWh/Wh/MWh; explicit warning that power sensors (W/kW) are not valid; one or more example entity naming patterns.
- [x] 10.4 Apply the same treatment to the other five cumulative energy sensors: `total_grid_import`, `total_grid_export`, `total_pv_production`, `total_battery_charge`, `total_battery_discharge`.
- [x] 10.5 In `frontend/src/pages/settings/components/EntityArrayEditor.tsx` (or wherever the EV `max_power_kw` field is rendered), ensure the helper/tooltip text for that field explicitly states: required, example values (7.4, 11, 22 kW), and warns that missing/zero disables the charger.
- [x] 10.6 In `config.default.yaml`, update the comment next to `battery.max_soc_percent` to reflect soft semantics (match the tooltip wording).
- [x] 10.7 Manual visual check: open Settings in the dev UI, hover each updated tooltip, verify the new text renders correctly.

## 11. Regression and integration tests

- [x] 11.1 Create `tests/planner/test_regression_max_soc_infeasibility.py`: reproduce the reported incident. Setup: `capacity_kwh=19.2`, `min_soc_percent=15`, `max_soc_percent=95`, `initial_soc_kwh=18.989`. Run full pipeline with realistic price/forecast fixtures. Assert: solver returns `Optimal`, resulting plan's first slot has a negative `battery_charge_kw` (i.e., discharge) or positive `grid_export_kwh`, and SoC drops below 18.24 kWh within the first 2 hours.
- [x] 11.2 Create `tests/loads/test_ev_missing_power_registration.py`: an EV charger config without `max_power_kw` produces a registered-as-disabled load and an `EV_MISSING_POWER` HealthIssue; the planner runs successfully and excludes that charger from the MILP.
- [x] 11.3 Create `tests/health/test_planner_health_surface.py`: after a deliberate config-blocking failure (e.g., max < min SoC), `/api/health` returns a planner issue with the correct code, severity `critical`, and populated details.
- [x] 11.4 Create `tests/services/test_retry_policy_e2e.py`: simulate a sequence of [config-blocking fail, settings_saved event, success] and assert retry suspension is applied then cleared and planning resumes.
- [x] 11.5 Frontend integration test: render `App` with a mocked health endpoint returning a planner critical issue; assert banner is visible, clicking "View details" opens the drawer, copy button copies redacted JSON.

## 12. Documentation

- [x] 12.1 Update `openspec/specs/planner/spec.md` after archive to reflect the new ADDED/MODIFIED requirements (handled automatically by openspec archive — verify the diff matches).
- [x] 12.2 Add a brief section to `docs/DEVELOPER.md` under "Planner Internals" describing the pre-flight validator, the error-code enum, and the retry policy table. One paragraph each, with a pointer to `planner/errors.py` and `planner/preflight.py`.
- [x] 12.3 Confirm that `docs/BACKLOG.md` still contains the `[Planner] Inverter AC Limit Constraint Overcounts PV-to-Battery Path` entry — no removal.
