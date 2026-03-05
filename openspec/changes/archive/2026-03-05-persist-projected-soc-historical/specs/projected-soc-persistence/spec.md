## Purpose

Persist the projected SoC (State of Charge) percentage to the database for historical analysis and chart display. This enables the SoC projection chart to show the full 48-hour span of projected values, including historical slots.

## Requirements

### Requirement: slot_plans table stores projected_soc_percent

The `slot_plans` database table SHALL include a `projected_soc_percent` column to store the projected battery SoC percentage for each slot.

#### Scenario: Database column exists after migration
- **WHEN** the database migration runs
- **THEN** the `slot_plans` table SHALL have a `projected_soc_percent` column of type REAL (nullable)

#### Scenario: Historical slot has projected_soc_percent
- **WHEN** a slot plan is stored to the database
- **THEN** the `projected_soc_percent` value from the schedule SHALL be persisted to the `slot_plans` table

### Requirement: store_plan persists projected_soc_percent

The `LearningStore.store_plan()` method SHALL persist the `projected_soc_percent` value to the database when storing slot plans.

#### Scenario: store_plan saves projected_soc_percent
- **WHEN** `store_plan()` is called with a DataFrame containing `projected_soc_percent`
- **THEN** the value SHALL be written to the `slot_plans.projected_soc_percent` column

### Requirement: get_plans_range returns projected_soc_percent

The `LearningStore.get_plans_range()` method SHALL return the `projected_soc_percent` value for each slot plan.

#### Scenario: get_plans_range includes projected_soc_percent
- **WHEN** `get_plans_range()` is called
- **THEN** the returned dictionary for each slot SHALL include `projected_soc_percent`

### Requirement: Schedule API provides projected_soc_percent for historical slots

The schedule API SHALL attach `projected_soc_percent` from the database for historical slots in the response.

#### Scenario: Historical slot has projected_soc_percent in API response
- **WHEN** a historical slot is returned by the schedule API
- **AND** the slot has `projected_soc_percent` in the database
- **THEN** the API response SHALL include `projected_soc_percent` for that slot

#### Scenario: Future slot uses schedule.json projected_soc_percent
- **WHEN** a future slot is returned by the schedule API
- **THEN** `projected_soc_percent` SHALL come from `schedule.json` (existing behavior, unchanged)
