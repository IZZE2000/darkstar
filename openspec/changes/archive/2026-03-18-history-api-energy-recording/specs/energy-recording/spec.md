## ADDED Requirements

### Requirement: HA History API Power-to-Energy Conversion
The system SHALL provide a generic function that fetches power sensor history from the HA History API for a given time window and computes energy as `mean(power_kw) × duration_hours` in kWh.

#### Scenario: Power sensor with regular updates
- **WHEN** the function is called for `sensor.ev_power` from `03:00` to `03:15`
- **AND** the HA History API returns 15 data points averaging 5.0 kW
- **THEN** the function SHALL return `1.25 kWh` (5.0 × 0.25)

#### Scenario: Power sensor with sparse updates
- **WHEN** the function is called for `sensor.ev_power` from `03:00` to `03:15`
- **AND** the HA History API returns 3 data points: [5.0, 4.9, 5.1]
- **THEN** the function SHALL return `1.25 kWh` (mean of 5.0 × 0.25)

#### Scenario: History API returns empty data
- **WHEN** the function is called for `sensor.ev_power` from `03:00` to `03:15`
- **AND** the HA History API returns an empty response or no valid data points
- **THEN** the function SHALL return `None`

#### Scenario: History API call fails
- **WHEN** the function is called and the HTTP request fails (timeout, connection error)
- **THEN** the function SHALL return `None`

#### Scenario: Power values require unit normalization
- **WHEN** the HA History API returns values in Watts (unit_of_measurement: "W")
- **THEN** the function SHALL normalize to kW before computing the average

#### Scenario: Non-numeric and unavailable states are excluded
- **WHEN** the HA History API returns states including "unknown", "unavailable", or non-numeric values
- **THEN** the function SHALL exclude those data points from the average calculation

### Requirement: EV Energy Recording via Power History
The recorder SHALL calculate EV charging energy for each slot by fetching the EV charger power sensor history over the slot window and computing average power × time.

#### Scenario: EV charger recording with history API
- **WHEN** the recorder records a slot observation
- **AND** an enabled EV charger has `sensor: sensor.ev_power` configured
- **THEN** the recorder SHALL call the power history function for the slot window
- **AND** store the result as `ev_charging_kwh`

#### Scenario: Multiple EV chargers
- **WHEN** multiple enabled EV chargers are configured
- **THEN** the recorder SHALL sum the energy from all chargers' power history

#### Scenario: EV history API fallback to power snapshot
- **WHEN** the power history function returns `None` for an EV charger
- **THEN** the recorder SHALL fall back to `current_power_kw × 0.25` using the point-in-time power reading

### Requirement: Water Heater Energy Recording via Power History
The recorder SHALL calculate water heater energy for each slot by fetching the water heater power sensor history over the slot window and computing average power × time.

#### Scenario: Water heater recording with history API
- **WHEN** the recorder records a slot observation
- **AND** an enabled water heater has `sensor: sensor.wh_power` configured
- **THEN** the recorder SHALL call the power history function for the slot window
- **AND** store the result as `water_kwh`

#### Scenario: Multiple water heaters
- **WHEN** multiple enabled water heaters are configured
- **THEN** the recorder SHALL sum the energy from all heaters' power history

#### Scenario: Water heater history API fallback to power snapshot
- **WHEN** the power history function returns `None` for a water heater
- **THEN** the recorder SHALL fall back to `current_power_kw × 0.25` using the point-in-time power reading

### Requirement: Generic Function Robustness
The power history function SHALL be production-grade: it SHALL use a reasonable HTTP timeout (10-15s), SHALL return `None` on any failure without raising exceptions, and SHALL log failures at warning level. The function SHALL NOT implement its own retry logic — retry is handled at the recorder service layer.

#### Scenario: HTTP timeout
- **WHEN** the HA History API does not respond within the timeout
- **THEN** the function SHALL return `None`
- **AND** log a warning with the entity ID and error

#### Scenario: Connection error
- **WHEN** the HTTP connection to HA fails
- **THEN** the function SHALL return `None`
- **AND** log a warning with the entity ID and error

#### Scenario: Unexpected exception
- **WHEN** any unexpected error occurs during processing
- **THEN** the function SHALL catch the exception, return `None`, and log a warning

## MODIFIED Requirements

### Requirement: Snapshot Fallback
The recorder SHALL fall back to power-snapshot based estimation (kW × 0.25h) when the HA History API power-to-energy function returns `None` for a specific metric.

#### Scenario: History API unavailable for EV
- **WHEN** the power history function returns `None` for an EV charger power sensor
- **THEN** the recorder SHALL use `ev_power_kw × 0.25` to estimate energy for the slot

#### Scenario: History API unavailable for water heater
- **WHEN** the power history function returns `None` for a water heater power sensor
- **THEN** the recorder SHALL use `water_power_kw × 0.25` to estimate energy for the slot

#### Scenario: PV/load/grid unchanged
- **WHEN** the recorder calculates PV, load, or grid energy
- **THEN** the recorder SHALL continue using cumulative energy sensor deltas as the primary method
- **AND** fall back to power snapshot only when no cumulative sensor is configured

### Requirement: Load Isolation from Deferrable Loads
The recorder SHALL subtract energy from controllable loads (EV charging, water heating) from the total load before storing `load_kwh` in `slot_observations`. This ensures `load_kwh` represents base load only, enabling accurate ML training and forecast analysis.

#### Scenario: Recorder subtracts EV charging energy from total load
- **WHEN** the recorder calculates `total_load_kwh` as `5.0 kWh`
- **AND** EV charging consumed `2.0 kWh` during the slot (from power history or snapshot)
- **THEN** the recorder SHALL store `3.0 kWh` as `load_kwh`

#### Scenario: Recorder subtracts water heating energy from total load
- **WHEN** the recorder calculates `total_load_kwh` as `4.0 kWh`
- **AND** water heating consumed `0.75 kWh` during the slot (from power history or snapshot)
- **THEN** the recorder SHALL store `3.25 kWh` as `load_kwh`

#### Scenario: Recorder subtracts both EV and water from total load
- **WHEN** the recorder calculates `total_load_kwh` as `6.0 kWh`
- **AND** EV charging consumed `2.0 kWh`
- **AND** water heating consumed `0.75 kWh`
- **THEN** the recorder SHALL store `3.25 kWh` as `load_kwh`

#### Scenario: Recorder clamps negative base load to zero
- **WHEN** the recorder calculates `total_load_kwh` as `1.0 kWh`
- **AND** EV charging consumed `2.0 kWh` (timing mismatch)
- **THEN** the recorder SHALL store `0.0 kWh` as `load_kwh`
- **AND** the recorder SHALL log a warning about the negative base load

#### Scenario: Load isolation always applies
- **WHEN** EV or water energy is calculated via power history or snapshot fallback
- **THEN** the recorder SHALL always subtract those values from total load
- **AND** isolation SHALL NOT be conditional on any sensor type configuration

## REMOVED Requirements

### Requirement: Support for Cumulative Energy Sensors (EV/Water only)
**Reason**: Replaced by HA History API power averaging which is more robust and requires no state tracking. Cumulative sensor support remains for PV, load, and grid (Phase 2 will evaluate those separately).
**Migration**: Remove `energy_sensor` field from `ev_chargers[]` and `water_heaters[]` config. The system automatically uses the power sensor (already required) with the HA History API.

### Requirement: Delta-based Energy Calculation (EV/Water only)
**Reason**: Delta calculation with time-proportional scaling is fragile for sensors with update intervals longer than the 15-minute recording interval. The HA History API approach eliminates the need for delta tracking entirely for EV and water energy.
**Migration**: No user action required. The `ev_energy_*` and `water_energy_*` keys in `recorder_state.json` become orphaned and harmless.

### Requirement: Persistent Sensor Timestamp Storage (EV/Water only)
**Reason**: No longer needed for EV/water since we don't track cumulative deltas for these loads.
**Migration**: Orphaned state keys are harmless and can remain in the state file.
