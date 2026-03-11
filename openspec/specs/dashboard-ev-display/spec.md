# Dashboard EV Display

## Purpose

Dashboard display of energy resources and EV charging metrics with conditional rendering based on system configuration.

## Requirements

### Requirement: Dashboard Energy Resources card renders metrics conditionally
The Dashboard Energy Resources card SHALL display metrics conditionally based on system `has_*` configuration flags. Metrics SHALL only appear when the corresponding feature is enabled.

| Metric | Condition |
|--------|-----------|
| Solar Production | `has_solar: true` |
| Battery Charge / Discharge | `has_battery: true` |
| Water Heating | `has_water_heater: true` |
| EV Charging | `has_ev_charger: true` |

The "House Load" metric SHALL always be displayed.

#### Scenario: Full configuration (all features enabled)
- **WHEN** the Dashboard loads with all `has_*` flags `true`
- **THEN** all metrics (Solar, Battery, Water, EV, House Load) are displayed

#### Scenario: Minimal configuration (no optional features)
- **WHEN** the Dashboard loads with all optional `has_*` flags `false`
- **THEN** only "House Load" is displayed
- **AND** no Solar, Battery, Water, or EV fields are rendered

#### Scenario: EV-only conditional example
- **WHEN** `has_ev_charger: true`
- **THEN** the "EV Charging" field displays today's total EV energy
- **AND** "House Load" reflects base load (EV excluded, as stored in DB)

### Requirement: Frontend fetches config once at Dashboard initialization
The Dashboard frontend SHALL fetch the system configuration once on initialization to determine which metrics to display.

#### Scenario: Frontend reads has_* flags
- **WHEN** the Dashboard initializes
- **THEN** the frontend fetches the system configuration
- **AND** reads `has_solar`, `has_battery`, `has_water_heater`, and `has_ev_charger`
- **AND** renders only the applicable metric fields
