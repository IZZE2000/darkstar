## MODIFIED Requirements

### Requirement: EV Energy Recording via Power History
The recorder SHALL calculate EV charging energy for each slot per-device by fetching each enabled charger's power sensor history over the slot window. The recorder SHALL store both aggregate `ev_charging_kwh` (sum across all chargers) and per-device energy in the slot observation.

#### Scenario: Single EV charger recording unchanged
- **WHEN** one enabled EV charger has `sensor: sensor.ev_power` configured
- **THEN** the recorder SHALL call the power history function for the slot window
- **AND** store the result as `ev_charging_kwh`

#### Scenario: Multiple EV chargers with per-device tracking
- **WHEN** two enabled EV chargers are configured (charger A: 2.0 kWh, charger B: 1.5 kWh)
- **THEN** the recorder SHALL store `ev_charging_kwh = 3.5` (aggregate)
- **AND** the recorder SHALL store per-device energy keyed by charger ID

#### Scenario: EV history API fallback to power snapshot
- **WHEN** the power history function returns `None` for an EV charger
- **THEN** the recorder SHALL fall back to `current_power_kw * 0.25` using the point-in-time power reading for that specific charger

## ADDED Requirements

### Requirement: Per-device EV energy storage
The recorder SHALL store per-device EV energy in the slot observation metadata or as a JSON field, keyed by charger ID. This enables future per-device analytics without requiring schema changes per charger.

#### Scenario: Per-device energy stored as JSON
- **WHEN** the recorder stores a slot observation with two active EV chargers
- **THEN** the observation SHALL include a field (e.g., `ev_charger_energy`) containing `{"ev_charger_1": 2.0, "ev_charger_2": 1.5}`

#### Scenario: Single charger backward compatible
- **WHEN** only one charger is active
- **THEN** `ev_charging_kwh` SHALL contain the total (same as before)
- **AND** `ev_charger_energy` SHALL contain `{"ev_charger_1": 2.0}`

#### Scenario: No active chargers
- **WHEN** no EV chargers are enabled or none are charging
- **THEN** `ev_charging_kwh` SHALL be `0.0`
- **AND** `ev_charger_energy` SHALL be `{}` or omitted
