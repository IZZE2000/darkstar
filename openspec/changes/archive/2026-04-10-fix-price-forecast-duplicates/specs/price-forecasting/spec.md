## MODIFIED Requirements

### Requirement: D+1 fallback null safety
The D+1 fallback query SHALL filter out weather-only (null-prediction) rows before returning results to the planner. A row with a null spot_p50 SHALL never be served as a price forecast to downstream consumers. The query SHALL return at most one forecast record per `slot_start`, preferring the row with the latest `issue_timestamp` when multiple forecast runs exist for the same slot.

#### Scenario: Fallback excludes null-prediction rows
- **WHEN** `get_d1_price_forecast_fallback()` queries the database and weather-only rows exist for D+1
- **THEN** those rows SHALL be excluded from the returned results
- **AND** if no non-null D+1 forecast rows exist, the function SHALL return None

#### Scenario: Fallback deduplicates by slot_start
- **WHEN** `get_d1_price_forecast_fallback()` queries the database and multiple forecast runs exist for the same `slot_start` (different `issue_timestamp`)
- **THEN** the query SHALL return only the row with the latest `issue_timestamp` per `slot_start`
- **AND** the returned list SHALL contain at most one record per unique `slot_start`

#### Scenario: Fallback returns correct count after dedup
- **WHEN** `get_d1_price_forecast_fallback()` queries the database with `limit=96` and 48 unique slots each have 2 forecast runs (96 total rows)
- **THEN** the function SHALL return exactly 48 records (one per unique slot, each the latest run)
