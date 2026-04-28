## MODIFIED Requirements

### Requirement: Price forecast inference
The system SHALL generate price forecasts for D+1 through D+7 at 15-minute slot resolution. D+1 forecasts SHALL serve as fallback before the ~13:00 CET Nordpool day-ahead auction. Once real Nordpool D+1 prices are available, they SHALL take precedence over the D+1 forecast. When no trained model exists, the system SHALL still fetch regional weather and persist rows with null spot prediction columns to accumulate training data.

`get_price_forecasts_from_db` SHALL return exactly one record per `slot_start` value. When multiple DB rows share the same `slot_start` (due to duplicate writes), the function SHALL keep the row with the latest `issue_timestamp`; if rows also tie on `issue_timestamp`, any single row for that slot is acceptable. This guarantee applies regardless of whether `days_ahead` filtering is active.

`get_d1_price_forecast_fallback` SHALL deduplicate its return value on `slot_start` before returning, so that callers never receive two entries with the same slot timestamp. `get_d1_price_forecast_fallback` SHALL filter out any slots whose `slot_start` date is on or before the current date (today), returning only slots that are strictly in the future (tomorrow or later).

`_process_nordpool_data` SHALL deduplicate the assembled entry list by `start_time` before returning, keeping the first occurrence of each timestamp. Because real Nordpool entries are always prepended before fallback entries, this ensures real prices take precedence.

#### Scenario: Daily forecast generation
- **WHEN** the forecast pipeline runs and a trained price model exists
- **THEN** the system SHALL generate p10/p50/p90 spot price forecasts for all 15-minute slots from D+1 through D+7

#### Scenario: D+1 fallback before auction
- **WHEN** a downstream consumer requests prices and real Nordpool D+1 prices are not yet available (before ~13:00 CET)
- **THEN** the system SHALL provide the D+1 price forecast as a fallback
- **AND** the system SHALL only return rows where spot_p50 is not null

#### Scenario: D+1 fallback excludes today and past slots
- **WHEN** `get_d1_price_forecast_fallback` retrieves forecast rows from the DB
- **THEN** the function SHALL discard any rows whose `slot_start` date is today or earlier
- **AND** the returned list SHALL contain only slots for tomorrow or later

#### Scenario: Real prices replace D+1 forecast
- **WHEN** real Nordpool D+1 prices become available (after auction publication)
- **THEN** the system SHALL use real prices for D+1 instead of the forecast

#### Scenario: Weather accumulation without trained model
- **WHEN** the forecast pipeline runs and no trained price model exists
- **THEN** the system SHALL still fetch regional weather data and build feature rows for D+1 through D+7
- **AND** the system SHALL persist those rows with spot_p10, spot_p50, and spot_p90 set to null
- **AND** the system SHALL NOT return these rows to downstream consumers as price forecasts

#### Scenario: DB query deduplicates by slot_start
- **WHEN** `get_price_forecasts_from_db` is called and the DB contains multiple rows for the same `slot_start` with the same `days_ahead`
- **THEN** the function SHALL return exactly one row for that `slot_start`
- **AND** the returned row SHALL have the latest `issue_timestamp` among all candidates

#### Scenario: Fallback deduplicates before returning
- **WHEN** `get_d1_price_forecast_fallback` retrieves rows from the DB and two rows share the same `slot_start`
- **THEN** the function SHALL return only one entry per `slot_start`
- **AND** the returned list SHALL have no duplicate `slot_start` values

#### Scenario: Assembled price data has no duplicate timestamps
- **WHEN** `_process_nordpool_data` assembles the final price entry list from Nordpool and fallback sources
- **THEN** the returned list SHALL contain at most one entry per `start_time` value
- **AND** when two sources provide the same `start_time`, the entry that appeared first in the input (real Nordpool) SHALL be kept
