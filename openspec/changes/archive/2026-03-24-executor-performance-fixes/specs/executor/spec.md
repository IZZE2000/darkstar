## MODIFIED Requirements

### Requirement: Executor fetches current Nordpool import price for battery cost tracking
The executor tick SHALL fetch the current Nordpool import price using `await get_nordpool_data()` directly within the async tick context. If the fetch fails or returns no data, the executor SHALL fall back to 0.5 SEK/kWh.

#### Scenario: Nordpool price fetch succeeds
- **WHEN** the executor tick runs battery cost tracking
- **AND** the Nordpool integration returns price data
- **THEN** the executor uses the real spot price for the current time slot
- **AND** the battery cost record reflects the actual import price

#### Scenario: Nordpool price fetch fails
- **WHEN** the executor tick runs battery cost tracking
- **AND** the Nordpool fetch raises an exception or returns empty data
- **THEN** the executor falls back to 0.5 SEK/kWh
- **AND** the tick continues without interruption

#### Scenario: Nordpool price fetch does not block the event loop
- **WHEN** the executor tick fetches Nordpool prices
- **THEN** the fetch is awaited as a coroutine within the existing async event loop
- **AND** no `asyncio.run()` or nested event loop is used

## ADDED Requirements

### Requirement: Water heater sensor reads are gated by has_water_heater flag
The executor and recorder SHALL NOT fetch water heater power sensors when `system.has_water_heater` is `false`. The `water_heaters[]` sensor loop SHALL be skipped entirely when the system flag is disabled.

#### Scenario: Water heating disabled skips sensor reads
- **WHEN** the recorder or executor gathers power sensor readings
- **AND** `system.has_water_heater` is `false`
- **THEN** no HTTP requests are made for water heater sensors
- **AND** no 404 warnings are logged for missing water heater entities

#### Scenario: Water heating enabled reads sensors normally
- **WHEN** the recorder or executor gathers power sensor readings
- **AND** `system.has_water_heater` is `true`
- **THEN** enabled water heater sensors from `water_heaters[]` are fetched as before

### Requirement: EV charger sensor reads are gated by has_ev_charger flag
The recorder SHALL NOT fetch EV charger power sensors when `system.has_ev_charger` is `false`.

#### Scenario: EV charging disabled skips sensor reads
- **WHEN** the recorder gathers power sensor readings
- **AND** `system.has_ev_charger` is `false`
- **THEN** no HTTP requests are made for EV charger sensors

#### Scenario: EV charging enabled reads sensors normally
- **WHEN** the recorder gathers power sensor readings
- **AND** `system.has_ev_charger` is `true`
- **THEN** enabled EV charger sensors from `ev_chargers[]` are fetched as before
