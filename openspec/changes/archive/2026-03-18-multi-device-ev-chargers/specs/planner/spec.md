## MODIFIED Requirements

### Requirement: Solver blocks battery discharge during EV charging
The solver SHALL force battery discharge to zero in any slot where ANY EV charger is charging. This SHALL be enforced by introducing an auxiliary binary `any_ev_charging[t]` that is 1 when any charger's `ev_charge[d][t]` is 1, then applying the Big-M constraint: `discharge[t] <= (1 - any_ev_charging[t]) * M`, where `M = max_discharge_kw * slot_hours[t]`. The linking constraints SHALL be: `any_ev_charging[t] >= ev_charge[d][t]` for each device d, and `any_ev_charging[t] <= sum(ev_charge[d][t] for d)`. This constraint SHALL only be added when at least one EV charger is present in the solver input.

#### Scenario: One of two chargers active forces zero discharge
- **WHEN** the solver schedules charger A to charge in slot t (`ev_charge[A][t] = 1`) and charger B is idle (`ev_charge[B][t] = 0`)
- **THEN** `any_ev_charging[t]` is forced to 1
- **AND** `discharge[t]` is forced to 0.0 by the Big-M constraint

#### Scenario: No chargers active allows normal discharge
- **WHEN** no charger is scheduled in slot t (all `ev_charge[d][t] = 0`)
- **THEN** `any_ev_charging[t]` is 0
- **AND** `discharge[t]` is bounded only by its normal upper bound

#### Scenario: EV disabled users are unaffected
- **WHEN** no EV chargers are present in the solver input
- **THEN** no EV-related discharge constraint is added to the MILP model
- **AND** solver behavior is identical to before this change

## ADDED Requirements

### Requirement: Adapter passes per-device EV configs to solver
The planner adapter SHALL build a list of `EVChargerInput` objects from the `ev_chargers[]` config array, fetching per-device SoC and plug state from Home Assistant. Only enabled chargers SHALL be included. The adapter SHALL NOT aggregate EV chargers into a single blob.

#### Scenario: Two enabled chargers with different states
- **WHEN** charger A has SoC 30% and is plugged in, charger B has SoC 80% and is unplugged
- **THEN** the adapter SHALL pass both chargers to the solver with their individual states

#### Scenario: Disabled charger excluded
- **WHEN** charger A is enabled and charger B has `enabled: false`
- **THEN** only charger A SHALL be passed to the solver

### Requirement: Per-device deadline calculation
The pipeline SHALL calculate `ev_deadline` independently for each charger using that charger's `departure_time` field. Chargers without a departure time SHALL have `deadline: None`.

#### Scenario: Two chargers with different departure times
- **WHEN** charger A has `departure_time: "07:00"` and charger B has `departure_time: "09:00"`
- **AND** current time is 22:00
- **THEN** charger A's deadline SHALL be tomorrow 07:00 and charger B's deadline SHALL be tomorrow 09:00

#### Scenario: Charger with no departure time
- **WHEN** a charger has `departure_time: ""`
- **THEN** its deadline SHALL be `None` (no deadline constraint in solver)

### Requirement: Per-device initial state fetching
The `get_initial_state()` function SHALL fetch SoC and plug state for ALL enabled chargers from Home Assistant, returning per-device state instead of scalar values.

#### Scenario: All chargers' states fetched
- **WHEN** three chargers are enabled with different SoC and plug sensors
- **THEN** `get_initial_state()` SHALL return SoC and plug state for each charger individually

#### Scenario: Missing SoC sensor defaults to 0%
- **WHEN** a charger has no `soc_sensor` configured
- **THEN** its SoC SHALL default to 0% (conservative: assumes empty battery)

#### Scenario: Missing plug sensor defaults to true
- **WHEN** a charger has no `plug_sensor` configured
- **THEN** its plug state SHALL default to `True` (assume plugged in, let user control via enabled flag)

### Requirement: Replan plug state override applies per-device
When a replan is triggered by a specific charger's plug-in event, the known plug state (`plugged_in=True`) SHALL be passed as an override for that specific charger only. Other chargers SHALL still fetch their plug state from the HA REST API.

#### Scenario: Charger A plug-in triggers replan
- **WHEN** charger A's plug sensor fires a plug-in event
- **THEN** `get_initial_state()` SHALL use `plugged_in=True` for charger A
- **AND** charger B's plug state SHALL be fetched from HA REST API
