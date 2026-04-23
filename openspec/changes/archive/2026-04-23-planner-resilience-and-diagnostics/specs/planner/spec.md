## ADDED Requirements

### Requirement: Soft max-SoC bound with penalty
The Kepler MILP SHALL enforce `battery.max_soc_percent` as a soft constraint. The solver SHALL introduce a per-slot `soc_overshoot[t] >= 0` slack variable and replace the previous hard upper bound `soc[t] <= max_soc_kwh` with `soc[t] <= max_soc_kwh + soc_overshoot[t]`. The objective SHALL include a penalty term `MAX_SOC_PENALTY * sum(soc_overshoot[t])` where `MAX_SOC_PENALTY = 1000.0` (mirroring the existing `MIN_SOC_PENALTY`).

The clipping of `initial_soc` to the physical range SHALL use `[0, capacity_kwh]` only; it SHALL NOT clip to `[min_soc_kwh, max_soc_kwh]`.

#### Scenario: Initial SoC above max produces a feasible plan
- **GIVEN** `battery.max_soc_percent = 95` and `capacity_kwh = 19.2` (max_soc_kwh = 18.24)
- **AND** measured initial SoC is 18.989 kWh (98.9%)
- **WHEN** the planner runs
- **THEN** the solver returns status `Optimal`
- **AND** the resulting plan's first slot begins with a discharge action (battery_charge_kw < 0) or an export action sufficient to reduce SoC toward the ceiling
- **AND** the `soc_overshoot` penalty is reflected in the total cost

#### Scenario: Initial SoC below max is unaffected
- **GIVEN** `battery.max_soc_percent = 95` and measured SoC is 10.0 kWh (52%)
- **WHEN** the planner runs
- **THEN** the solver returns status `Optimal`
- **AND** `soc_overshoot[t]` is zero for all slots

#### Scenario: Lower bound behavior unchanged
- **GIVEN** measured initial SoC is below `min_soc_kwh`
- **WHEN** the planner runs
- **THEN** the existing `soc_violation` slack and `MIN_SOC_PENALTY` are applied
- **AND** no change to the lower-bound enforcement is observed

### Requirement: Pre-flight validator runs before solver
The planner pipeline SHALL invoke a deterministic pre-flight validator before constructing the Kepler MILP. The validator SHALL perform an ordered sequence of checks and SHALL raise a typed `PlannerError` carrying a `PlannerErrorCode` and a structured diagnostic payload on the first failed check. The checks SHALL include at minimum:

1. Battery config: `min_soc_percent < max_soc_percent`, `capacity_kwh > 0` if battery enabled, and `max_charge_power_kw > 0 AND max_discharge_power_kw > 0` if battery enabled (code `CONFIG_INVALID`).
2. Initial SoC within `[0, capacity_kwh]` (code `INITIAL_SOC_OUT_OF_RANGE`).
3. Initial SoC reading timestamp within 30 minutes of now (code `DATA_STALE`, warning — does not halt).
4. Every plugged-in EV charger has `max_power_kw > 0` (code `EV_MISSING_POWER`).
5. Every plugged-in EV charger has `battery_capacity_kwh > 0` (code `EV_INVALID_CAPACITY`).
6. Every EV charger with a `deadline` has `deadline > now` (code `EV_DEADLINE_PAST`, warning — does not halt, EV excluded from deadline constraints for that run).
7. Price data covers at least 4 hours ahead of now (code `PRICES_UNAVAILABLE`).
8. Forecast data is non-empty and covers the planning horizon (code `FORECAST_UNAVAILABLE`).
9. No NaN or Inf values in prices or forecasts (code `NUMERIC_INVALID`).

On a blocking failure, the validator SHALL raise immediately without running additional checks. On warning-only conditions, the validator SHALL log the warning and continue.

The 30-minute SoC staleness threshold SHALL be hardcoded; no configuration surface is introduced.

#### Scenario: Invalid battery config halts before solver
- **GIVEN** `battery.min_soc_percent = 50` and `battery.max_soc_percent = 40`
- **WHEN** the planner runs
- **THEN** the pre-flight validator raises `PlannerError` with code `CONFIG_INVALID`
- **AND** the Kepler solver is not invoked
- **AND** the error details include `min_soc_percent` and `max_soc_percent` values

#### Scenario: EV missing power halts with specific code
- **GIVEN** an EV charger is plugged in with `max_power_kw = 0`
- **WHEN** the planner runs
- **THEN** the pre-flight validator raises `PlannerError` with code `EV_MISSING_POWER`
- **AND** the error details include the offending `charger_id`

#### Scenario: Missing prices halt with transient code
- **GIVEN** no price slots are available for the next 4 hours
- **WHEN** the planner runs
- **THEN** the pre-flight validator raises `PlannerError` with code `PRICES_UNAVAILABLE`
- **AND** the error details include the price horizon range observed

#### Scenario: Stale SoC reading produces warning only
- **GIVEN** the battery SoC reading timestamp is 45 minutes old
- **WHEN** the planner runs
- **THEN** the pre-flight validator emits a `DATA_STALE` warning but does not halt
- **AND** the solver still runs with the observed SoC value

#### Scenario: EV deadline in the past produces warning only
- **GIVEN** an EV charger has `deadline` set to 1 hour before now
- **WHEN** the planner runs
- **THEN** the pre-flight validator emits an `EV_DEADLINE_PAST` warning but does not halt
- **AND** the Kepler solver runs without applying a deadline constraint for that charger

#### Scenario: NaN in forecast data halts
- **GIVEN** at least one forecast slot contains a NaN value
- **WHEN** the planner runs
- **THEN** the pre-flight validator raises `PlannerError` with code `NUMERIC_INVALID`
- **AND** the error details identify the offending field and slot

## MODIFIED Requirements

### Requirement: Meaningful Planner Error Notifications
The planner error handler SHALL emit structured error records carrying a `PlannerErrorCode`, a human-readable message, a fix hint, and a diagnostic payload for every failure. The previous generic `ValueError("Planner generated invalid schedule (safety guard)")` SHALL be replaced by a typed `PlannerError` with code `INVALID_SCHEDULE` and diagnostics including the solver status, the last observed `initial_soc_kwh`, `max_soc_kwh`, and `capacity_kwh`.

Solver-level failures SHALL be mapped to codes `SOLVER_INFEASIBLE` (when PuLP reports `LpStatusInfeasible`), `SOLVER_UNDEFINED` (when PuLP reports `LpStatusUndefined`), and `SOLVER_TIMEOUT` (when the solver's `timeLimit` is exceeded). The solver status string SHALL be included in the diagnostics payload for each.

The WebSocket `planner_error` event payload SHALL include the `code` and `details` fields. The existing `error` string field SHALL continue to be populated for backwards compatibility.

#### Scenario: Generic ValueError is replaced by typed error
- **WHEN** the planner would previously have raised `ValueError("Planner generated invalid schedule (safety guard)")`
- **THEN** it raises `PlannerError` with code `INVALID_SCHEDULE`
- **AND** the diagnostics include solver status, `initial_soc_kwh`, `max_soc_kwh`, and `capacity_kwh`

#### Scenario: Infeasible solver status maps to SOLVER_INFEASIBLE
- **WHEN** PuLP reports `LpStatusInfeasible` after the solver returns
- **THEN** the emitted error has code `SOLVER_INFEASIBLE`
- **AND** the diagnostics include the solver status string

#### Scenario: Undefined solver status maps to SOLVER_UNDEFINED
- **WHEN** PuLP reports `LpStatusUndefined`
- **THEN** the emitted error has code `SOLVER_UNDEFINED`
- **AND** the diagnostics include the solver status string

#### Scenario: WebSocket payload carries structured fields
- **WHEN** the backend emits a `planner_error` event
- **THEN** the payload includes `error` (string, legacy), `code` (string), and `details` (object) fields
