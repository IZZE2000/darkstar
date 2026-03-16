## MODIFIED Requirements

### Requirement: Load Isolation from Deferrable Loads
The recorder SHALL subtract energy from controllable loads (EV charging, water heating) from the total load before storing `load_kwh` in `slot_observations`. This ensures `load_kwh` represents base load only, enabling accurate ML training and forecast analysis.

When an `energy_sensor` is configured on a device entry, the recorder SHALL compute energy for that device using a cumulative delta (end reading minus start reading) rather than a power snapshot. When no `energy_sensor` is configured, the recorder SHALL fall back to `power_kw × 0.25h`.

#### Scenario: Recorder uses cumulative delta for EV when energy_sensor is configured
- **WHEN** the EV charger config has a non-empty `energy_sensor`
- **AND** the cumulative reading at slot start is `120.5 kWh` and at slot end is `121.5 kWh`
- **THEN** the recorder SHALL use `1.0 kWh` as `ev_charging_kwh` for the slot
- **AND** this value SHALL be subtracted from total load to produce `load_kwh`

#### Scenario: Recorder uses cumulative delta for water heater when energy_sensor is configured
- **WHEN** the water heater config has a non-empty `energy_sensor`
- **AND** the cumulative reading at slot start is `50.0 kWh` and at slot end is `50.75 kWh`
- **THEN** the recorder SHALL use `0.75 kWh` as `water_kwh` for the slot

#### Scenario: Recorder falls back to snapshot when energy_sensor is empty
- **WHEN** `energy_sensor` is empty or absent for a device
- **AND** the power sensor reads `4.0 kW` at recording time
- **THEN** the recorder SHALL use `4.0 × 0.25 = 1.0 kWh` for that device's energy contribution

#### Scenario: Recorder subtracts EV charging energy from total load
- **WHEN** the recorder calculates `total_load_kwh` as `5.0 kWh` from the cumulative sensor
- **AND** EV charging consumed `2.0 kWh` during the slot
- **THEN** the recorder SHALL store `3.0 kWh` as `load_kwh`

#### Scenario: Recorder subtracts water heating energy from total load
- **WHEN** the recorder calculates `total_load_kwh` as `4.0 kWh`
- **AND** water heating consumed `0.75 kWh` during the slot
- **THEN** the recorder SHALL store `3.25 kWh` as `load_kwh`

#### Scenario: Recorder subtracts both EV and water from total load
- **WHEN** the recorder calculates `total_load_kwh` as `6.0 kWh`
- **AND** EV charging consumed `2.0 kWh`
- **AND** water heating consumed `0.75 kWh`
- **THEN** the recorder SHALL store `3.25 kWh` as `load_kwh`

#### Scenario: Recorder clamps negative base load to zero
- **WHEN** the recorder calculates `total_load_kwh` as `1.0 kWh`
- **AND** EV charging consumed `2.0 kWh` (sensor drift or timing mismatch)
- **THEN** the recorder SHALL store `0.0 kWh` as `load_kwh`
- **AND** the recorder SHALL log a warning about the negative base load

#### Scenario: Recorder uses power snapshot fallback when no cumulative sensor
- **WHEN** no `total_load_consumption` sensor is configured
- **AND** the LoadDisaggregator provides `base_load_kw` from power snapshot isolation
- **THEN** the recorder SHALL use `base_load_kw * 0.25` for `load_kwh`

#### Scenario: Recorder falls back to snapshot when energy_sensor has no prior state
- **WHEN** an EV charger has `energy_sensor` configured
- **AND** this is the first recording slot (no prior cumulative reading in state store)
- **THEN** the recorder SHALL fall back to `power_kw × 0.25h` for that device's energy contribution
- **AND** the current cumulative reading SHALL be stored for use in the next slot
