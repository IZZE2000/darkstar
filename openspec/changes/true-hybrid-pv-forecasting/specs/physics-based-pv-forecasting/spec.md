## ADDED Requirements

### Requirement: Physics-Based PV Forecast as Base
The system SHALL use Open-Meteo physics calculation as the base PV forecast, with ML providing corrections rather than direct predictions.

#### Scenario: Sunny day uses physics base
- **WHEN** radiation exceeds 500 W/m² for a time slot
- **THEN** the base PV forecast SHALL be calculated using physics formula `(radiation/1000) × capacity × efficiency × 0.25`
- **AND** the ML model SHALL add a residual correction on top

#### Scenario: Cloudy day maintains accuracy
- **WHEN** radiation is below 200 W/m² for a time slot
- **THEN** the physics base SHALL provide appropriate low values
- **AND** ML corrections SHALL fine-tune based on learned patterns

#### Scenario: ML residual handles shadows
- **WHEN** actual PV is consistently lower than physics prediction at a specific time (indicating shading)
- **THEN** the ML residual model SHALL learn negative corrections for that time/condition
- **AND** future forecasts SHALL include the learned shadow correction

### Requirement: ML Learns Residuals
The ML training pipeline SHALL train PV models to predict the residual (actual - physics) rather than predicting PV directly.

#### Scenario: Training targets residual
- **WHEN** training data is prepared
- **THEN** the target variable SHALL be calculated as `pv_actual - physics_forecast`
- **AND** the model SHALL learn to predict this residual value

#### Scenario: Inference applies residual
- **WHEN** generating forecasts for future slots
- **THEN** the system SHALL calculate physics forecast first
- **AND** add the ML-predicted residual to get final forecast

### Requirement: Retroactive Physics Calculation
For historical training data, the system SHALL calculate physics forecasts retroactively using stored radiation data.

#### Scenario: Historical physics baseline
- **WHEN** training on historical data older than this change
- **THEN** the system SHALL calculate `physics_forecast` from stored radiation values
- **AND** use `actual_pv - calculated_physics` as the training target

#### Scenario: Missing radiation handling
- **WHEN** historical radiation data is unavailable for a slot
- **THEN** the system SHALL skip that slot for PV training
- **AND** log a warning about missing radiation data

### Requirement: Final Forecast Composition
The final PV forecast SHALL be the sum of physics base and ML residual.

#### Scenario: Final forecast calculation
- **WHEN** returning forecast via API
- **THEN** `final.pv_kwh` SHALL equal `physics_base + ml_residual`
- **AND** `base.pv_kwh` SHALL contain the physics value (not ML prediction)
- **AND** `correction.pv_kwh` SHALL contain the ML residual

#### Scenario: API backward compatibility
- **WHEN** API consumers request forecast data
- **THEN** the response structure SHALL remain compatible
- **AND** consumers SHALL receive physics-based final values transparently

### Requirement: Open-Meteo Physics Calculation
The system SHALL use Open-Meteo's native PV calculation when available, with simplified physics as fallback.

#### Scenario: Open-Meteo available
- **WHEN** Open-Meteo API returns radiation data with solar position calculations
- **THEN** the system SHALL use Open-Meteo's per-array PV calculation
- **AND** account for panel tilt and azimuth from config

#### Scenario: Open-Meteo unavailable
- **WHEN** Open-Meteo API fails or returns no data
- **THEN** the system SHALL fall back to simplified physics formula
- **AND** use aggregate capacity and default efficiency

### Requirement: Configurable Physics Parameters
Users SHALL be able to configure physics calculation parameters in config.yaml.

#### Scenario: System efficiency configuration
- **WHEN** user sets `pv_system_efficiency` in config.yaml
- **THEN** the physics calculation SHALL use that efficiency value (0.0-1.0)
- **AND** the default SHALL be 0.85 if not specified

#### Scenario: Capacity override
- **WHEN** user sets `pv_capacity_override_kwp` in config.yaml
- **THEN** the physics calculation SHALL use that capacity instead of summing solar_arrays
- **AND** this allows tuning without changing array definitions
