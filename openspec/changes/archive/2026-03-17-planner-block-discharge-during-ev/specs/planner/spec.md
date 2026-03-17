## ADDED Requirements

### Requirement: Solver blocks battery discharge during EV charging
The solver SHALL force battery discharge to zero in any slot where EV charging is active. This SHALL be enforced via a Big-M MILP constraint: `discharge[t] <= (1 - ev_charge[t]) * M`, where `M = max_discharge_kw * slot_hours[t]`. This constraint SHALL only be added when EV optimization is enabled (`ev_enabled = True`). The existing grid-only constraint (`ev_energy[t] <= grid_import[t] + pv + epsilon`) SHALL remain unchanged.

#### Scenario: EV charging slot has zero discharge
- **WHEN** the solver schedules EV charging in slot t (`ev_charge[t] = 1`)
- **THEN** `discharge[t]` is forced to 0.0 by the Big-M constraint

#### Scenario: Non-EV slot allows normal discharge
- **WHEN** the solver does not schedule EV charging in slot t (`ev_charge[t] = 0`)
- **THEN** `discharge[t]` is bounded only by its normal upper bound (`max_discharge_kw * slot_hours`)

#### Scenario: Solver chooses between EV charging and discharge under load pressure
- **WHEN** house load is high and both EV charging and battery discharge would reduce cost
- **THEN** the solver picks the combination that minimizes total cost (may skip EV charging in that slot to allow discharge, or vice versa)
- **AND** load shedding penalty (10,000 SEK/kWh) ensures the solver never sheds load when discharge alone could serve it

#### Scenario: EV disabled users are unaffected
- **WHEN** `ev_enabled` is False
- **THEN** no EV-related discharge constraint is added to the MILP model
- **AND** solver behavior is identical to before this change
