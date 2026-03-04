## Purpose

Physics-first hybrid PV forecasting that uses panel orientation (tilt/azimuth) to calculate theoretical production, with ML learning residuals to capture local effects like shadows and efficiency differences.

## Requirements

### Requirement: Physics-Based PV Forecast as Base
The system SHALL use `OpenMeteoSolarForecast` with panel tilt/azimuth as the base PV forecast, with ML providing residual corrections rather than direct predictions.

#### Scenario: Sunny day uses physics base
- **WHEN** radiation exceeds 500 W/m² for a time slot
- **THEN** the base PV forecast SHALL be calculated using `OpenMeteoSolarForecast` with tilt/azimuth from config
- **AND** the ML model SHALL add a residual correction on top

#### Scenario: Physics uses panel orientation
- **WHEN** calculating physics forecast
- **THEN** the system SHALL read tilt and azimuth from `solar_arrays` config
- **AND** use POA (Plane of Array) irradiance for accurate per-array estimates

#### Scenario: Cloudy day maintains accuracy
- **WHEN** radiation is below 200 W/m² for a time slot
- **THEN** the physics base SHALL provide appropriate low values
- **AND** ML corrections SHALL fine-tune based on learned patterns

#### Scenario: ML residual handles shadows
- **WHEN** actual PV is consistently lower than physics prediction at a specific time (indicating shading)
- **THEN** the ML residual model SHALL learn negative corrections for that hour
- **AND** future forecasts SHALL include the learned shadow correction

### Requirement: Three-Layer Forecast Composition
The final PV forecast SHALL be composed of three layers: physics base, ML residual, and corrector residual.

#### Scenario: Full composition flow
- **WHEN** generating forward forecasts
- **THEN** the system SHALL calculate: `physics_kwh = OpenMeteoSolarForecast(radiation, tilt, azimuth, kWp)`
- **AND** calculate: `ml_residual_kwh = pv_model.predict(features)`
- **AND** calculate: `corrector_residual_kwh = corrector.predict(intermediate)`
- **AND** compose: `final = physics + ml_residual + corrector_residual`

#### Scenario: Layer separation of concerns
- **WHEN** analyzing forecast components
- **THEN** physics SHALL handle theoretical max based on radiation and panel geometry
- **AND** ML residual SHALL learn long-term patterns (fixed shadows, degradation, efficiency)
- **AND** corrector SHALL learn short-term patterns (weather forecast errors)

### Requirement: ML Learns Residuals
The ML training pipeline SHALL train PV models to predict the residual (actual - physics) rather than predicting PV directly.

#### Scenario: Training targets residual
- **WHEN** training data is prepared
- **THEN** the target variable SHALL be calculated as `pv_actual - physics_forecast`
- **AND** the model SHALL learn to predict this residual value

#### Scenario: Inference applies residual
- **WHEN** generating forecasts for future slots
- **THEN** the system SHALL calculate physics forecast first
- **AND** add the ML-predicted residual to get intermediate forecast

#### Scenario: Efficiency auto-learned
- **WHEN** actual system efficiency differs from physics model assumptions
- **THEN** the ML residual SHALL learn the consistent difference
- **AND** no user configuration of efficiency SHALL be required

### Requirement: Training Data Filter
The ML training pipeline SHALL only train on slots with actual PV data and sun-up conditions.

#### Scenario: Sun-up filter
- **WHEN** preparing training data
- **THEN** the system SHALL filter slots where `pv_kwh IS NOT NULL`
- **AND** filter slots where `radiation > 10 OR pv_kwh > 0.01`
- **AND** skip nighttime slots where both radiation and production are zero

#### Scenario: Filter rationale
- **WHEN** a slot has radiation=0 and pv=0
- **THEN** the residual SHALL be 0 - 0 = 0
- **AND** this SHALL be excluded from training as it provides no learning signal

### Requirement: Corrector Integration
The corrector SHALL learn residuals against the hybrid forecast (physics + ML residual).

#### Scenario: Corrector target
- **WHEN** training the corrector model
- **THEN** the target SHALL be `actual - (physics + ml_residual)`
- **AND** the corrector SHALL refine the hybrid forecast, not just the physics

#### Scenario: Corrector catches short-term errors
- **WHEN** today's weather forecast has errors (e.g., unexpected clouds)
- **THEN** the corrector SHALL learn to adjust for these short-term patterns
- **AND** the ML residual SHALL continue handling long-term patterns

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
The final PV forecast SHALL be the sum of physics base, ML residual, and corrector residual.

#### Scenario: Final forecast calculation
- **WHEN** returning forecast via API
- **THEN** `final.pv_kwh` SHALL equal `physics_base + ml_residual + corrector_residual`
- **AND** `base.pv_kwh` SHALL contain the physics value only
- **AND** `correction.pv_kwh` SHALL contain `ml_residual + corrector_residual`

#### Scenario: API transparency
- **WHEN** API consumers request forecast data
- **THEN** the response SHALL include `physics.pv_kwh` and `ml_residual.pv_kwh` fields
- **AND** consumers SHALL be able to see the component breakdown

#### Scenario: API backward compatibility
- **WHEN** API consumers request forecast data
- **THEN** the response structure SHALL remain compatible
- **AND** `final.pv_kwh` SHALL remain the authoritative forecast value

### Requirement: Open-Meteo Fallback
The system SHALL have a fallback when `OpenMeteoSolarForecast` is unavailable.

#### Scenario: Open-Meteo unavailable
- **WHEN** Open-Meteo API fails or `OpenMeteoSolarForecast` throws an error
- **THEN** the system SHALL fall back to simplified physics formula `(rad/1000) × kWp × 0.85 × 0.25`
- **AND** use aggregate capacity from `solar_arrays` config

### Requirement: Multi-Array Support
The physics calculation SHALL support systems with multiple solar arrays at different orientations.

#### Scenario: Multiple arrays with different tilts
- **WHEN** config defines multiple arrays with different tilt/azimuth values
- **THEN** `OpenMeteoSolarForecast` SHALL calculate per-array estimates
- **AND** the physics base SHALL be the sum of all array estimates
