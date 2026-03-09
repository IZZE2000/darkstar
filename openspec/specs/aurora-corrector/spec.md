## Purpose

The AURORA corrector is responsible for post-processing and applying corrections to ML-generated forecasts. It handles statistical bias correction and ML error model corrections to improve forecast accuracy.

## Requirements

### Requirement: Slot start type conversion
The AURORA corrector SHALL convert `slot_start` from ISO string format to timezone-aware pandas Timestamp immediately after receiving forecast data from the API.

#### Scenario: Forecast data retrieval
- **WHEN** the corrector retrieves base records from `get_forecast_slots()`
- **THEN** each record's `slot_start` field SHALL be converted from string to `pd.Timestamp` with proper timezone conversion

#### Scenario: Timezone-aware datetime for downstream processing
- **WHEN** processing forecast slots for correction
- **THEN** the `slot_start` field SHALL be usable for timezone conversion via `.astimezone()` without AttributeError

#### Scenario: Merge compatibility with weather data
- **WHEN** merging forecast data with weather DataFrame
- **THEN** the merge SHALL succeed on `slot_start` column without type mismatch errors between string and datetime64

#### Scenario: Merge compatibility with vacation mode data
- **WHEN** merging forecast data with vacation mode flag DataFrame
- **THEN** the merge SHALL succeed on `slot_start` column without type mismatch errors
