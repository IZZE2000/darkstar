## Purpose

Enhance the StrategyDomain price view with a training progress bar during cold-start and expose training sample counts via the status endpoint.

## Requirements

### Requirement: Training progress bar during cold-start
When the price view is active and price forecasting is enabled but no forecast data is available, the StrategyDomain card SHALL display a progress bar showing training data accumulation instead of a static text message.

#### Scenario: Progress bar displayed during accumulation
- **WHEN** `view === 'price'` and `price_forecast.enabled` is `true` and no outlook data exists (empty `days` array)
- **THEN** the card SHALL fetch `GET /api/price-forecast/status` and display a horizontal progress bar
- **AND** the progress bar SHALL show `training_samples_count / min_training_samples` as both a bar fill and text label (e.g., "127 / 500 samples")

#### Scenario: Progress percentage computed correctly
- **WHEN** the status endpoint returns `training_samples_count: 250` and `min_training_samples: 500`
- **THEN** the progress bar SHALL be filled to 50%
- **AND** the text SHALL read "250 / 500 samples"

#### Scenario: Zero samples collected
- **WHEN** the status endpoint returns `training_samples_count: 0`
- **THEN** the progress bar SHALL be empty (0% fill)
- **AND** the text SHALL read "0 / 500 samples"

#### Scenario: Progress heading and icon preserved
- **WHEN** the progress bar is displayed
- **THEN** the "Price Forecasting Active" heading and AI icon SHALL remain above the progress bar

### Requirement: Training sample count in status endpoint
The `GET /api/price-forecast/status` endpoint SHALL return the current count of accumulated training samples.

#### Scenario: Sample count returned
- **WHEN** the status endpoint is called
- **THEN** the response SHALL include a `training_samples_count` integer field representing the total number of rows in the `price_forecasts` table

#### Scenario: No samples yet
- **WHEN** no rows exist in `price_forecasts`
- **THEN** `training_samples_count` SHALL be `0`
