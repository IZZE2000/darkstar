## MODIFIED Requirements

### Requirement: Water Heater Energy Recording via Power History
The recorder SHALL calculate water heater energy for each slot per-device by fetching each enabled heater's power sensor history over the slot window. The recorder SHALL store both aggregate `water_kwh` (sum across all heaters) and per-device energy in the slot observation.

#### Scenario: Single water heater recording unchanged
- **WHEN** one enabled water heater has `sensor: sensor.wh_power` configured
- **THEN** the recorder SHALL call the power history function for the slot window
- **AND** store the result as `water_kwh`

#### Scenario: Multiple water heaters with per-device tracking
- **WHEN** two enabled water heaters are configured (heater A: 0.75 kWh, heater B: 0.50 kWh)
- **THEN** the recorder SHALL store `water_kwh = 1.25` (aggregate)
- **AND** the recorder SHALL store per-device energy keyed by heater ID

#### Scenario: Water heater history API fallback to power snapshot
- **WHEN** the power history function returns `None` for a water heater
- **THEN** the recorder SHALL fall back to `current_power_kw * 0.25` using the point-in-time power reading for that specific heater

## ADDED Requirements

### Requirement: Per-device water energy storage
The recorder SHALL store per-device water energy in the slot observation metadata or as a JSON field, keyed by heater ID. This enables future per-device analytics without requiring schema changes per heater.

#### Scenario: Per-device energy stored as JSON
- **WHEN** the recorder stores a slot observation with two active water heaters
- **THEN** the observation SHALL include a field (e.g., `water_heater_energy`) containing `{"main_tank": 0.75, "upstairs_tank": 0.50}`

#### Scenario: Single heater backward compatible
- **WHEN** only one heater is active
- **THEN** `water_kwh` SHALL contain the total (same as before)
- **AND** `water_heater_energy` SHALL contain `{"main_tank": 0.75}`

#### Scenario: No active heaters
- **WHEN** no water heaters are enabled or none are heating
- **THEN** `water_kwh` SHALL be `0.0`
- **AND** `water_heater_energy` SHALL be `{}` or omitted
