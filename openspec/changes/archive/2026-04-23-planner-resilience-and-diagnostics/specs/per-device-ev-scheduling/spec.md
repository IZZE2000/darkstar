## ADDED Requirements

### Requirement: EV charger with invalid power is registered as disabled
The load registration service SHALL register EV chargers configured with `max_power_kw <= 0` (or missing `max_power_kw` entirely) as visible-but-disabled. The charger SHALL appear in the load registry with a `disabled_reason` of `"missing_power_kw"` so it remains visible in the UI and health surfaces. The planner's adapter SHALL exclude such chargers when building `KeplerConfig.ev_chargers`, and the solver SHALL NOT create decision variables for them.

A `HealthIssue` with `category="ev"`, `severity="critical"`, and `code="EV_MISSING_POWER"` SHALL be emitted for each such charger. The issue's `entity_id` SHALL be the charger ID, and `details` SHALL include the charger ID and the observed `max_power_kw` value.

This requirement SHALL apply equally when `max_power_kw` is entirely absent from the config (previously defaulted silently to `0.0` by `backend/loads/service.py`).

#### Scenario: Missing max_power_kw registers as disabled
- **GIVEN** an EV charger config entry with `enabled: true` and no `max_power_kw` field
- **WHEN** the load service loads configuration
- **THEN** the charger is registered with `disabled_reason="missing_power_kw"`
- **AND** the charger appears in the load registry
- **AND** a `HealthIssue` is emitted with category `ev`, severity `critical`, code `EV_MISSING_POWER`, and `entity_id` set to the charger ID

#### Scenario: Zero max_power_kw registers as disabled
- **GIVEN** an EV charger config entry with `enabled: true` and `max_power_kw: 0`
- **WHEN** the load service loads configuration
- **THEN** the charger is registered with `disabled_reason="missing_power_kw"`
- **AND** the planner's adapter excludes the charger from `KeplerConfig.ev_chargers`
- **AND** the solver does not create decision variables for the charger

#### Scenario: Valid max_power_kw registers normally
- **GIVEN** an EV charger config entry with `max_power_kw: 11.0`
- **WHEN** the load service loads configuration
- **THEN** the charger is registered without a `disabled_reason`
- **AND** no `EV_MISSING_POWER` HealthIssue is emitted for that charger

#### Scenario: Disabled-state charger is visible in UI
- **WHEN** the frontend fetches the load registry
- **THEN** a charger with `disabled_reason="missing_power_kw"` is included in the response
- **AND** the response field `disabled_reason` is set to `"missing_power_kw"` for that entry

#### Scenario: Fixing config re-enables charger without restart
- **GIVEN** a charger was registered with `disabled_reason="missing_power_kw"`
- **WHEN** the user updates `max_power_kw` to a positive value and the config is reloaded
- **THEN** the charger is re-registered without a `disabled_reason`
- **AND** the corresponding `EV_MISSING_POWER` HealthIssue is cleared
- **AND** the next planner run includes the charger in `KeplerConfig.ev_chargers`
