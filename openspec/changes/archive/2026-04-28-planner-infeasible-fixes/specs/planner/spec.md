## ADDED Requirements

### Requirement: Inverter AC constraint permits zero discharge when PV forecast exceeds inverter capacity
The Kepler MILP SHALL enforce the `max_inverter_ac_kw` constraint as `discharge[t] <= max(0.0, inverter_ac_kwh - s.pv_kwh)` where `inverter_ac_kwh = max_inverter_ac_kw * slot_hours[t]`. When `pv_forecast[t] >= inverter_ac_kwh` the upper bound SHALL be `0.0` (discharge forced to zero). The previous formulation `discharge[t] + s.pv_kwh <= inverter_ac_kwh` SHALL be replaced; it is mathematically equivalent when `pv < inverter_ac` but produces an infeasible negative upper bound when `pv >= inverter_ac`.

#### Scenario: PV forecast within inverter limit — normal discharge bound
- **WHEN** `pv_forecast[t] = 1.5 kWh` and `inverter_ac_kwh = 2.0 kWh`
- **THEN** `discharge[t] <= 0.5 kWh`
- **AND** the LP is feasible for this slot

#### Scenario: PV forecast equals inverter limit — discharge forced to zero
- **WHEN** `pv_forecast[t] = 2.0 kWh` and `inverter_ac_kwh = 2.0 kWh`
- **THEN** `discharge[t] <= 0.0`
- **AND** the LP is feasible (discharge = 0 satisfies the constraint)

#### Scenario: PV forecast exceeds inverter limit — discharge still zero, no infeasibility
- **WHEN** `pv_forecast[t] = 2.1177 kWh` and `inverter_ac_kwh = 2.0 kWh`
- **THEN** the effective upper bound is `max(0.0, 2.0 - 2.1177) = 0.0`
- **AND** `discharge[t] <= 0.0` is satisfiable (discharge = 0)
- **AND** the solver returns `Optimal`, not `Infeasible`
