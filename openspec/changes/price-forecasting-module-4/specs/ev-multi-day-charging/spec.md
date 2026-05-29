## ADDED Requirements

### Requirement: EV charger config supports optional multi-day deadline and target energy
Each entry in `ev_chargers[]` SHALL support two new optional fields: `deadline` (ISO 8601 datetime string, e.g., `"2026-04-04T07:00"`) and `target_kwh` (float, total energy required by the deadline). Both fields SHALL be optional and default to `None`.

#### Scenario: Charger with multi-day deadline configured
- **WHEN** an EV charger has `deadline: "2026-04-04T07:00"` and `target_kwh: 60`
- **THEN** the config loader SHALL parse `deadline` as a timezone-aware datetime (using system timezone)
- **AND** `target_kwh` SHALL be stored as a float

#### Scenario: Charger with deadline but no target_kwh
- **WHEN** an EV charger has `deadline` set but `target_kwh` is absent
- **THEN** the config loader SHALL log a warning
- **AND** the multi-day mode SHALL NOT activate (fall back to single-day departure_time)

#### Scenario: Charger with no deadline (default behavior)
- **WHEN** an EV charger has no `deadline` field
- **THEN** the existing `departure_time` single-day behavior SHALL apply unchanged

#### Scenario: Deadline in the past
- **WHEN** an EV charger has a `deadline` that is in the past
- **THEN** the multi-day mode SHALL NOT activate
- **AND** the system SHALL log a warning and fall back to `departure_time` behavior

### Requirement: Pipeline invokes MultiDayPlanner for multi-day EV chargers
The planner pipeline SHALL invoke the `MultiDayPlanner` for each plugged-in EV charger that has a valid `deadline` and `target_kwh`, AND `price_forecast.enabled` is true. The resulting daily quota SHALL be attached to the charger's state dict as `daily_quota_kwh`.

#### Scenario: Multi-day charger gets quota from price forecast
- **WHEN** charger has `deadline` 3 days away, `target_kwh=60`, and price forecasts are available
- **THEN** the pipeline SHALL call `MultiDayPlanner.compute_quota()` with the charger's remaining energy, deadline, and daily price averages
- **AND** the resulting quota for today SHALL be set as `daily_quota_kwh` on the charger state

#### Scenario: Multi-day charger but price_forecast.enabled is false
- **WHEN** charger has a valid `deadline` but `price_forecast.enabled` is false
- **THEN** the pipeline SHALL NOT invoke the `MultiDayPlanner`
- **AND** the charger SHALL use its `deadline` as a simple deadline (like departure_time but further out) with no daily quota constraint

#### Scenario: Multi-day charger but charger is unplugged
- **WHEN** charger has a valid `deadline` but is not plugged in
- **THEN** the pipeline SHALL NOT invoke the `MultiDayPlanner` for that charger
- **AND** no quota SHALL be calculated

### Requirement: Pipeline calculates remaining energy from observations
The pipeline SHALL calculate `remaining_kwh` for multi-day chargers as `target_kwh - energy_delivered_kwh`, where `energy_delivered_kwh` is the total EV energy recorded in `slot_observations` since the charger was last plugged in (or since `deadline` was set, whichever is more recent).

#### Scenario: Partial charging already completed
- **WHEN** `target_kwh=60` and 25 kWh has been delivered since the charger was plugged in
- **THEN** `remaining_kwh` SHALL be 35
- **AND** the `MultiDayPlanner` SHALL distribute 35 kWh across remaining days

#### Scenario: Target already met
- **WHEN** `target_kwh=60` and 62 kWh has been delivered
- **THEN** `remaining_kwh` SHALL be 0 (clamped, not negative)
- **AND** today's quota SHALL be 0

### Requirement: Adapter passes daily quota to Kepler
The `EVChargerInput` dataclass SHALL gain an optional `daily_quota_kwh: float | None` field (default `None`). When set, the adapter SHALL pass it through to Kepler.

#### Scenario: Multi-day charger with quota
- **WHEN** the pipeline sets `daily_quota_kwh=15.0` on a charger
- **THEN** the `EVChargerInput` SHALL have `daily_quota_kwh=15.0`

#### Scenario: Single-day charger without quota
- **WHEN** a charger uses standard `departure_time` (no multi-day deadline)
- **THEN** `EVChargerInput.daily_quota_kwh` SHALL be `None`
- **AND** Kepler SHALL not apply any daily energy cap for that charger

### Requirement: Kepler enforces daily energy quota constraint
When a charger has `daily_quota_kwh` set (not None), the Kepler solver SHALL add a constraint: `sum(ev_energy[d][t] for t in all_slots) <= daily_quota_kwh`. This limits total energy for that charger across the entire solve horizon to the day's allocated quota.

#### Scenario: Quota limits total charging
- **WHEN** a charger has `daily_quota_kwh=15.0` and `max_power_kw=11`
- **THEN** the solver SHALL ensure total energy for that charger does not exceed 15.0 kWh
- **AND** the solver SHALL still optimize *when* to deliver that energy within the day using real Nordpool prices

#### Scenario: Quota is not set (single-day mode)
- **WHEN** a charger has `daily_quota_kwh=None`
- **THEN** no additional energy cap constraint SHALL be added
- **AND** existing behavior (charge up to capacity by deadline) SHALL apply

#### Scenario: Quota exceeds what Kepler can deliver
- **WHEN** `daily_quota_kwh=50.0` but the charger can only deliver 30 kWh before deadline
- **THEN** the solver SHALL deliver up to 30 kWh (limited by time and power constraints)
- **AND** the undelivered 20 kWh SHALL be picked up by tomorrow's quota recalculation

### Requirement: Multi-day deadline used as Kepler deadline
When a charger is in multi-day mode, the `deadline` datetime from config SHALL be used as the Kepler deadline (replacing the daily `departure_time` calculation). For days before the deadline day, the effective deadline SHALL be end-of-day (23:59) so Kepler can schedule charging across all slots.

#### Scenario: Multi-day charger on a non-deadline day
- **WHEN** today is Tuesday and the deadline is Friday 07:00
- **THEN** the Kepler deadline for this charger SHALL be today 23:59 (end of day)
- **AND** the charger MAY charge in any slot today, subject to its daily quota

#### Scenario: Multi-day charger on the deadline day
- **WHEN** today is Friday and the deadline is Friday 07:00
- **THEN** the Kepler deadline SHALL be Friday 07:00
- **AND** `ev_energy[d][t] == 0` for all slots ending after 07:00

### Requirement: Read-only API exposes per-charger multi-day state
A `GET /api/ev/chargers` endpoint SHALL return the state of all configured EV chargers, combining live HA sensor data with multi-day computation results from the last pipeline run.

#### Scenario: Multi-day charger with active quota
- **WHEN** a charger is in multi-day mode with an active deadline and the pipeline has run
- **THEN** the endpoint SHALL return `mode: "multi_day"` for that charger
- **AND** SHALL include `deadline`, `target_kwh`, `remaining_kwh`, `energy_delivered_kwh`, `daily_quota_kwh`, `days_remaining`, `quota_schedule`, and `status`
- **AND** `quota_schedule` SHALL contain one entry per remaining day with `date`, `quota_kwh`, and `avg_price_sek`

#### Scenario: Daily-mode charger
- **WHEN** a charger has `departure_time` set but no `deadline`
- **THEN** the endpoint SHALL return `mode: "daily"` for that charger
- **AND** multi-day fields (`deadline`, `remaining_kwh`, `daily_quota_kwh`, `quota_schedule`) SHALL be null

#### Scenario: Live sensor data merged with pipeline state
- **WHEN** the endpoint is called
- **THEN** each charger SHALL include live `plugged_in`, `soc_percent`, and `power_kw` from HA sensors
- **AND** these values SHALL be current (fetched on request, not cached from the pipeline run)

#### Scenario: Pipeline has not yet run or state file is missing
- **WHEN** the multi-day state file does not exist or is stale
- **THEN** all chargers SHALL be returned with `status: "idle"` and null multi-day fields
- **AND** live HA sensor data and config fields (departure_time, mode) SHALL still be populated

### Requirement: Pipeline persists multi-day state for API consumption
After computing multi-day quotas, the planner pipeline SHALL write the per-charger multi-day state to `data/ev_multi_day_state.json` with a `last_updated` ISO timestamp. The state file SHALL be overwritten on each pipeline run.

#### Scenario: Pipeline run with multi-day chargers
- **WHEN** the pipeline computes quotas for one or more multi-day chargers
- **THEN** the state file SHALL contain each charger's `id`, `deadline`, `target_kwh`, `remaining_kwh`, `energy_delivered_kwh`, `daily_quota_kwh`, `days_remaining`, `quota_schedule`, and `status`

#### Scenario: Pipeline run with no multi-day chargers
- **WHEN** no chargers are in multi-day mode
- **THEN** the state file SHALL be written with an empty chargers list and an updated `last_updated` timestamp
