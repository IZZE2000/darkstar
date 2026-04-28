## ADDED Requirements

### Requirement: EV charging section renders inside Energy Resources card
The Energy Resources card SHALL include an EV Charging section when `has_ev_charger` is true. The section SHALL display per-charger status including plug state, current SoC percentage, and active charging power. When multiple chargers are configured, each charger SHALL have its own independent row with independent controls.

#### Scenario: Single charger plugged in, daily mode
- **WHEN** one EV charger is configured with `departure_time: "07:00"` and is plugged in at 42% SoC
- **THEN** the EV section SHALL show the charger name, "plugged" status, "42% SoC", and departure time "07:00"
- **AND** the mode dropdown SHALL show "Every day"
- **AND** no deadline, target, progress, or quota fields SHALL be visible

#### Scenario: Single charger plugged in, multi-day mode
- **WHEN** one EV charger has an active deadline (future datetime) and target percentage set
- **THEN** the EV section SHALL show the charger name, plug/SoC status, the mode dropdown set to "Ready by", the deadline date/time, target % slider, progress bar, today's quota, status indicator, and mini day-by-day quota schedule

#### Scenario: Charger unplugged
- **WHEN** a charger is not plugged in
- **THEN** the EV section SHALL show the charger name and "unplugged" status
- **AND** all controls (mode, deadline, target) SHALL remain visible and interactive (user can set a deadline before plugging in)

#### Scenario: Multiple chargers with different modes
- **WHEN** charger A is in "Every day" mode and charger B is in "Ready by" mode
- **THEN** each charger SHALL display independently with its own mode, controls, and status

### Requirement: Mode dropdown toggles between daily and multi-day display
The EV section SHALL include a mode dropdown per charger with two options: "Every day" (daily departure) and "Ready by" (multi-day deadline). Changing the mode SHALL immediately update the visible controls.

#### Scenario: Switch from "Every day" to "Ready by"
- **WHEN** user changes the mode dropdown from "Every day" to "Ready by"
- **THEN** the departure time display SHALL be hidden
- **AND** the deadline date picker, target % slider, and multi-day fields SHALL become visible
- **AND** the deadline field SHALL be empty until the user sets one

#### Scenario: Switch from "Ready by" to "Every day"
- **WHEN** user changes the mode dropdown from "Ready by" to "Every day" while a deadline is active
- **THEN** a confirmation prompt SHALL appear warning that the active deadline will be cleared
- **AND** if confirmed, the deadline SHALL be cleared via `POST /api/ev/chargers/{id}/deadline` with null values
- **AND** the display SHALL return to showing departure time only

### Requirement: Date picker sets departure deadline
The EV section in "Ready by" mode SHALL include a date/time picker for setting the departure deadline. The picker SHALL only allow future dates/times. Setting a date SHALL immediately call the write API.

#### Scenario: User sets a deadline 3 days out
- **WHEN** user picks "Friday April 11, 07:00" in the date picker
- **THEN** the frontend SHALL call `POST /api/ev/chargers/{id}/deadline` with `{ deadline: "2026-04-11T07:00", target_pct: <current slider value> }`
- **AND** the card SHALL display "Fri Apr 11, 07:00" as the deadline

#### Scenario: User attempts to set a past date
- **WHEN** user attempts to pick a date/time that has already passed
- **THEN** the date picker SHALL prevent selection (past dates/times disabled)

#### Scenario: User clears the deadline
- **WHEN** user clicks "Clear deadline"
- **THEN** the frontend SHALL call `POST /api/ev/chargers/{id}/deadline` with `{ deadline: null, target_pct: null }`
- **AND** the multi-day fields (progress, quota, status) SHALL clear

### Requirement: Target percentage slider sets desired SoC
The EV section in "Ready by" mode SHALL include a slider (or numeric input) for setting the target SoC percentage (0-100%). The default value SHALL be 80%. Changing the target SHALL call the write API with the updated value.

#### Scenario: User sets target to 90%
- **WHEN** user adjusts the target slider to 90% and a deadline is already set
- **THEN** the frontend SHALL call `POST /api/ev/chargers/{id}/deadline` with the current deadline and `target_pct: 90`
- **AND** the progress bar SHALL update to reflect the new target

#### Scenario: Target set without deadline
- **WHEN** user adjusts the target slider but no deadline is set
- **THEN** the target value SHALL be stored locally (frontend state) but no API call SHALL be made until a deadline is also set

### Requirement: Progress bar shows charging progress
The EV section in multi-day mode SHALL display a progress bar showing `energy_delivered_kwh` out of `target_kwh` (both from `GET /api/ev/chargers`). The bar SHALL include a percentage and kWh labels.

#### Scenario: Partial charging completed
- **WHEN** `energy_delivered_kwh` is 23.1 and `target_kwh` is 36.9
- **THEN** the progress bar SHALL show approximately 63% filled
- **AND** text SHALL read "23.1 / 36.9 kWh"

#### Scenario: Target reached
- **WHEN** `remaining_kwh` is 0 (or negative)
- **THEN** the progress bar SHALL show 100% filled
- **AND** text SHALL read "Complete" or "36.9 / 36.9 kWh"

### Requirement: Today's quota and status indicator display
The EV section in multi-day mode SHALL show today's `daily_quota_kwh` and the charger's `status` field from the API.

#### Scenario: Charger on track
- **WHEN** API returns `daily_quota_kwh: 12.0` and `status: "on_track"`
- **THEN** the card SHALL display "Today's quota: 12.0 kWh" and a green "On track" indicator

#### Scenario: Charger behind schedule
- **WHEN** API returns `status: "behind"`
- **THEN** the card SHALL display an amber/red "Behind schedule" indicator

#### Scenario: Charging complete
- **WHEN** API returns `status: "complete"`
- **THEN** the card SHALL display a "Charging complete" indicator and the progress bar at 100%

#### Scenario: Deadline missed
- **WHEN** API returns `status: "missed"` (deadline passed, remaining_kwh > 0)
- **THEN** the card SHALL display a red warning: "Deadline passed — X kWh not delivered"

#### Scenario: No quota calculated yet
- **WHEN** deadline is set but `daily_quota_kwh` is null (planner hasn't run yet)
- **THEN** the card SHALL display "Quota pending — next planner run will calculate"

### Requirement: Mini quota schedule shows day-by-day allocation
The EV section in multi-day mode SHALL display a compact day-by-day view of the `quota_schedule` array from the API, showing date labels, kWh per day, and relative price level.

#### Scenario: 3-day quota schedule
- **WHEN** API returns `quota_schedule` with 3 entries (Thu: 12 kWh at 0.45 SEK, Fri: 5 kWh at 0.72 SEK, Sat: 15 kWh at 0.28 SEK)
- **THEN** the card SHALL display 3 day columns with day labels, kWh values, and relative price indicators (e.g., $ / $$ / $$$ or color-coded bars)

#### Scenario: No quota schedule available
- **WHEN** API returns `quota_schedule` as null or empty
- **THEN** the mini schedule area SHALL not render

### Requirement: EV card polls for updates periodically
The dashboard SHALL fetch `GET /api/ev/chargers` on initial load and then poll periodically (every 60 seconds) to update charger status, progress, and quota data.

#### Scenario: Data refreshes after planner run
- **WHEN** the planner runs and updates `ev_multi_day_state.json`
- **THEN** within 60 seconds the dashboard SHALL reflect the updated quota, progress, and status
