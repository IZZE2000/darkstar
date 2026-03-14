# Purpose

TBD - EV charging replanning functionality manages when and how the system triggers schedule recalculations in response to EV plug-in events, ensuring correct async handling, configuration reading, state propagation, and executor switch control.

## Requirements

### Requirement: EV plug-in triggers immediate replan

When an EV plug-in event is received via WebSocket, the system SHALL schedule an immediate replan using the correct async cross-thread dispatch mechanism (`asyncio.run_coroutine_threadsafe`), ensuring the coroutine executes in the main application event loop rather than the WebSocket thread's event loop.

#### Scenario: Replan fires on plug-in

- **WHEN** the WebSocket receives a plug sensor state change to `on` / `1` / `connected` / `true`
- **THEN** `scheduler_service.trigger_now()` is dispatched into the main event loop and a new schedule is generated

#### Scenario: Silent failure is eliminated

- **WHEN** `_trigger_ev_replan()` is invoked from a background thread
- **THEN** no `RuntimeError` is raised and the error is not silently swallowed

### Requirement: EV replan config path reads from `ev_chargers[]`

The `_trigger_ev_replan()` function SHALL read the `replan_on_plugin` setting from the `ev_chargers[]` array (ARC15 config path) rather than the deprecated `executor.ev_charger` path.

#### Scenario: replan_on_plugin disabled

- **WHEN** the first enabled EV charger has `replan_on_plugin: false`
- **THEN** `_trigger_ev_replan()` returns without triggering a replan

#### Scenario: replan_on_plugin enabled (default)

- **WHEN** `replan_on_plugin` is absent or `true` for the first enabled EV charger
- **THEN** the replan is triggered normally

### Requirement: Planner receives live WebSocket plug state on replan-on-plugin

When a replan is triggered by a plug-in WebSocket event, the system SHALL pass the known plug state (`ev_plugged_in=True`) directly into `get_initial_state()` as an override, bypassing the HA REST API re-fetch for that field.

#### Scenario: REST lag does not cause empty EV plan

- **WHEN** the planner is triggered within 3 seconds of a plug-in event
- **THEN** the generated schedule includes EV charging slots (assuming price and SoC conditions are met), even if the HA REST API has not yet reflected the plugged state

#### Scenario: Override applies only for plug-in trigger

- **WHEN** the planner is triggered by the normal scheduled cycle (not a plug-in event)
- **THEN** `get_initial_state()` fetches `ev_plugged_in` from HA REST API as usual

### Requirement: EV charger switch is controlled exclusively by schedule

The executor SHALL only enable the EV charger switch when `scheduled_ev_charging` is `True`. Actual detected power draw (`actual_ev_charging`) SHALL NOT be used as a gate to allow charging — it is used only for source isolation (blocking battery discharge).

#### Scenario: No plan, car draws power

- **WHEN** no EV charging slot exists in the current schedule AND the EV is physically drawing power
- **THEN** the executor does NOT assert `ev_should_charge = True` for switch control purposes

#### Scenario: Plan exists, car is not drawing power yet

- **WHEN** a schedule slot with `ev_charging_kw > 0.1` exists for the current interval
- **THEN** the executor asserts `ev_should_charge = True` and opens the EV switch

#### Scenario: Source isolation still active when unscheduled charging detected

- **WHEN** `actual_ev_charging` is `True` and `scheduled_ev_charging` is `False`
- **THEN** battery discharge is still blocked (source isolation) even though the switch is not actively commanded ON

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
