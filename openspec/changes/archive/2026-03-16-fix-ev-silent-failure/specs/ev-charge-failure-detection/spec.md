## ADDED Requirements

### Requirement: Executor detects EV charge failure when actual power stays zero

The executor SHALL track consecutive ticks where scheduled EV power exceeds 0.1 kW but actual EV power is below 0.1 kW. After 5 consecutive zero-power ticks, the executor SHALL raise an error through the existing "On Error" notification path and mark the execution record's success field as 0 (failed).

#### Scenario: EV wallbox rejects charge command

- **WHEN** the schedule has `ev_charging_kw = 10.0` for the current slot
- **AND** actual EV power remains below 0.1 kW for 5 consecutive executor ticks
- **THEN** the executor sends an error notification via `dispatcher.notify_error()` with message including scheduled and actual power
- **AND THEN** the execution record for that tick has `success = 0`

#### Scenario: EV charger ramps up within threshold

- **WHEN** the schedule has `ev_charging_kw > 0.1` for the current slot
- **AND** actual EV power exceeds 0.1 kW within 4 ticks
- **THEN** no error is raised
- **AND THEN** the zero-power tick counter resets to 0

#### Scenario: Error fires only once per EV slot

- **WHEN** the EV charge failure error has already been sent for the current EV charging period
- **AND** actual EV power remains at 0 on subsequent ticks
- **THEN** no additional error notifications are sent

#### Scenario: Counter resets when EV slot ends

- **WHEN** the current slot no longer has scheduled EV charging (`ev_charging_kw <= 0.1`)
- **THEN** the zero-power tick counter resets to 0
- **AND THEN** the failure-notified flag resets to false
