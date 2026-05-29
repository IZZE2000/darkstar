## MODIFIED Requirements

### Requirement: Dashboard Energy Resources card renders metrics conditionally
The Dashboard Energy Resources card SHALL display metrics conditionally based on system `has_*` configuration flags. Metrics SHALL only appear when the corresponding feature is enabled.

| Metric | Condition |
|--------|-----------|
| Solar Production | `has_solar: true` |
| Battery Charge / Discharge | `has_battery: true` |
| Water Heating | `has_water_heater: true` |
| EV Charging | `has_ev_charger: true` |

The "House Load" metric SHALL always be displayed.

When `has_ev_charger` is true, the EV Charging metric SHALL be an expandable section (not just a static kWh line). The expanded section SHALL display per-charger status with interactive controls as defined in the `ev-dashboard-card` capability spec.

#### Scenario: Full configuration (all features enabled)
- **WHEN** the Dashboard loads with all `has_*` flags `true`
- **THEN** all metrics (Solar, Battery, Water, EV, House Load) are displayed
- **AND** the EV Charging section SHALL be expandable with per-charger details and controls

#### Scenario: Minimal configuration (no optional features)
- **WHEN** the Dashboard loads with all optional `has_*` flags `false`
- **THEN** only "House Load" is displayed
- **AND** no Solar, Battery, Water, or EV fields are rendered

#### Scenario: EV-only conditional example
- **WHEN** `has_ev_charger: true`
- **THEN** the "EV Charging" section displays today's total EV energy as a summary line
- **AND** the section is expandable to show per-charger details with mode toggle, deadline controls, and charging progress
- **AND** "House Load" reflects base load (EV excluded, as stored in DB)
