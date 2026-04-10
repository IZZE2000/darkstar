## ADDED Requirements

### Requirement: WebSocket EV monitoring respects config reload

The WebSocket EV monitoring SHALL fully tear down EV charger state when `system.has_ev_charger` is set to false and config is reloaded. This ensures the system-level toggle acts as a proper master gate for all EV monitoring.

#### Scenario: Disabling has_ev_charger clears EV monitoring

- **WHEN** `system.has_ev_charger` is changed from `true` to `false` and config is reloaded
- **THEN** the WebSocket client SHALL clear `ev_charger_configs` to an empty list
- **AND** remove `ev_chargers` from `latest_values`
- **AND** stop monitoring all EV charger sensor entities

#### Scenario: Re-enabling has_ev_charger restores EV monitoring

- **WHEN** `system.has_ev_charger` is changed from `false` to `true` and config is reloaded
- **THEN** the WebSocket client SHALL rebuild EV charger monitoring from the `ev_chargers[]` config array
- **AND** only monitor chargers with `enabled: true`

#### Scenario: Disabling all individual chargers clears EV state

- **WHEN** `system.has_ev_charger` is `true` but all chargers in `ev_chargers[]` have `enabled: false`
- **THEN** the WebSocket client SHALL have an empty `ev_charger_configs` list
- **AND** `latest_values["ev_chargers"]` SHALL be an empty list
