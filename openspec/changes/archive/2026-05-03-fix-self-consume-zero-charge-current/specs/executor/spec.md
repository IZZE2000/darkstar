## ADDED Requirements

### Requirement: Default self_consumption fallback allows PV charging

When the controller selects `self_consumption` mode as the default fallback (no charge, export, or discharge planned), the `charge_value` in the resulting `ControllerDecision` SHALL use the user's configured maximum charge current (`max_charge_a` or `max_charge_w` depending on `control_unit`), not 0.

This ensures that even when the planner schedules no explicit charging action, PV power can still charge the battery. The intentional PV surplus export path (where `charge_kw > 0` results in `charge_value = planned`) SHALL NOT be affected.

#### Scenario: Default self_consumption with no planned charge

- **WHEN** the controller evaluates a slot where `charge_kw = 0`, `export_kw = 0`, `discharge_kw = 0`
- **AND** the battery SoC is above the plan target
- **AND** no EV charging is active
- **THEN** the mode intent SHALL be `"self_consumption"`
- **AND** `charge_value` SHALL equal the user's configured `max_charge_a` (or `max_charge_w` for watt-based control)
- **AND** `write_charge_current` SHALL be `True`

#### Scenario: Planned PV surplus still uses planned charge value

- **WHEN** the controller evaluates a slot where `charge_kw > 0` and `export_kw > 0` and `discharge_kw = 0`
- **THEN** the mode intent SHALL be `"self_consumption"`
- **AND** `charge_value` SHALL be the computed planned charge value from `_calculate_charge_limit`
- **AND** `charge_value` SHALL NOT be overridden to the user's max

#### Scenario: Default self_consumption with watt-based control unit

- **WHEN** the controller evaluates a slot with the default self_consumption fallback
- **AND** the profile's `control_unit` is `"W"`
- **THEN** `charge_value` SHALL equal the user's configured `max_charge_w`
