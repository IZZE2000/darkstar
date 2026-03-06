## ADDED Requirements

### Requirement: Load Isolation from Deferrable Loads
The recorder SHALL subtract energy from controllable loads (EV charging, water heating) from the total load before storing `load_kwh` in `slot_observations`. This ensures `load_kwh` represents base load only, enabling accurate ML training and forecast analysis.

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
