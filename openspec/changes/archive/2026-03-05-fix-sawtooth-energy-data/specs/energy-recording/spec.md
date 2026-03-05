## MODIFIED Requirements

### Requirement: Delta-based Energy Calculation
The recorder SHALL calculate the energy for a 15-minute slot by subtracting the cumulative meter reading at the start of the slot from the reading at the end of the slot, then scaling the result proportionally to represent exactly 15 minutes of energy when the sensor's update timing differs from the recording interval.

#### Scenario: Recorder calculates energy with matching timing
- **WHEN** the recorder has a previous reading of `1000.0 kWh` for PV at `12:00`
- **AND** the current reading at `12:15` is `1001.2 kWh`
- **AND** the sensor's `last_updated` timestamp indicates exactly 15 minutes elapsed
- **THEN** the recorder SHALL store `1.2 kWh` as the `pv_kwh` for the `12:00` slot

#### Scenario: Recorder scales energy when timing differs
- **WHEN** the recorder reads PV cumulative `1000.0 kWh` at `11:00:05` with sensor timestamp `10:53`
- **AND** the previous reading was `998.0 kWh` with sensor timestamp `10:43`
- **AND** the raw delta is `2.0 kWh` over 10 actual minutes
- **THEN** the recorder SHALL scale to `3.0 kWh` (2.0 × 15/10) for the 15-minute slot

#### Scenario: Recorder handles missing sensor timestamp gracefully
- **WHEN** the sensor's `last_updated` field is unavailable
- **THEN** the recorder SHALL use the raw delta without scaling

#### Scenario: Recorder skips scaling for extreme time gaps
- **WHEN** the time between sensor timestamps is less than 5 minutes or greater than 60 minutes
- **THEN** the recorder SHALL use the raw delta without scaling

## ADDED Requirements

### Requirement: Persistent Sensor Timestamp Storage
The recorder SHALL store the sensor's `last_updated` timestamp alongside each cumulative meter reading in the state file to enable time-proportional scaling on subsequent recordings.

#### Scenario: State file includes sensor timestamp
- **WHEN** the recorder successfully reads a cumulative sensor value
- **THEN** the state file entry SHALL include `sensor_timestamp` with the ISO format timestamp from the sensor's `last_updated` field

#### Scenario: Backward compatible with old state files
- **WHEN** the recorder reads a state file entry without `sensor_timestamp`
- **THEN** the recorder SHALL proceed without scaling for that recording cycle

### Requirement: Backfill Interpolation for Cumulative Sensors
The learning engine's `etl_cumulative_to_slots` function SHALL use linear interpolation to estimate cumulative values at exact slot boundaries, ensuring consistent delta calculations across all slots.

#### Scenario: Backfill interpolates to slot boundaries
- **WHEN** backfill processes cumulative sensor data with readings at irregular times
- **THEN** the function SHALL interpolate cumulative values at `:00, :15, :30, :45` boundaries
- **AND** delta calculations SHALL use these interpolated boundary values

#### Scenario: Backfill handles edge cases with fill
- **WHEN** interpolation leaves NaN values at series edges
- **THEN** the function SHALL apply forward-fill then backward-fill to ensure complete coverage
