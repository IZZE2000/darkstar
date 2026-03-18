## MODIFIED Requirements

### Requirement: EV replan config path reads from `ev_chargers[]`
The `_trigger_ev_replan()` function SHALL read the `replan_on_plugin` and `replan_on_unplug` settings from the specific charger whose plug sensor fired the event, not from the first enabled charger or a global setting.

#### Scenario: Charger A has replan disabled, charger B has replan enabled
- **WHEN** charger A has `replan_on_plugin: false` and charger B has `replan_on_plugin: true`
- **AND** charger A's plug sensor fires a plug-in event
- **THEN** `_trigger_ev_replan()` SHALL NOT trigger a replan

#### Scenario: Charger B plug-in triggers replan
- **WHEN** charger B has `replan_on_plugin: true`
- **AND** charger B's plug sensor fires a plug-in event
- **THEN** `_trigger_ev_replan()` SHALL trigger a replan

#### Scenario: Charger with default replan settings
- **WHEN** a charger has no explicit `replan_on_plugin` setting (defaults to true)
- **AND** its plug sensor fires a plug-in event
- **THEN** a replan SHALL be triggered

### Requirement: EV plug-in triggers immediate replan
When an EV plug-in event is received via WebSocket, the system SHALL schedule an immediate replan using the correct async cross-thread dispatch mechanism (`asyncio.run_coroutine_threadsafe`), ensuring the coroutine executes in the main application event loop rather than the WebSocket thread's event loop. The replan trigger SHALL pass the charger ID that triggered the event.

#### Scenario: Replan fires on plug-in with charger context
- **WHEN** the WebSocket receives a plug sensor state change to `on` / `1` / `connected` / `true`
- **THEN** `scheduler_service.trigger_now()` is dispatched with the triggering charger's ID
- **AND** a new schedule is generated with that charger's plug state overridden to `True`

#### Scenario: Silent failure is eliminated
- **WHEN** `_trigger_ev_replan()` is invoked from a background thread
- **THEN** no `RuntimeError` is raised and the error is not silently swallowed

### Requirement: Planner receives live WebSocket plug state on replan-on-plugin
When a replan is triggered by a plug-in WebSocket event, the system SHALL pass the known plug state (`ev_plugged_in=True`) directly into `get_initial_state()` as an override for the specific charger that triggered the event, bypassing the HA REST API re-fetch for that charger only.

#### Scenario: REST lag does not cause empty EV plan
- **WHEN** the planner is triggered within 3 seconds of charger A's plug-in event
- **THEN** the generated schedule includes charging slots for charger A (assuming price and SoC conditions are met)
- **AND** charger B's plug state is fetched from HA REST API as normal

#### Scenario: Override applies only for plug-in trigger
- **WHEN** the planner is triggered by the normal scheduled cycle (not a plug-in event)
- **THEN** `get_initial_state()` fetches plug state for all chargers from HA REST API as usual

## ADDED Requirements

### Requirement: Per-device plug sensor to charger ID mapping
The WebSocket client SHALL maintain a mapping from plug sensor entity IDs to charger IDs. When a plug sensor fires, the system SHALL look up the corresponding charger ID and use that charger's `replan_on_plugin`/`replan_on_unplug` setting.

#### Scenario: Plug sensor mapped to correct charger
- **WHEN** charger "tesla" has `plug_sensor: "binary_sensor.tesla_plug"` and charger "leaf" has `plug_sensor: "binary_sensor.leaf_plug"`
- **AND** `binary_sensor.tesla_plug` fires a state change
- **THEN** the system SHALL identify this as charger "tesla" and check tesla's replan settings

#### Scenario: Unknown plug sensor ignored
- **WHEN** a state change arrives for a sensor not mapped to any charger
- **THEN** the system SHALL ignore the event (no replan triggered)

### Requirement: Per-device unplug replan
The WebSocket client SHALL trigger a replan on unplug events for chargers that have `replan_on_unplug: true`. The charger ID SHALL be passed to the replan trigger.

#### Scenario: Charger with replan_on_unplug enabled
- **WHEN** charger A has `replan_on_unplug: true`
- **AND** charger A's plug sensor fires an unplug event
- **THEN** a replan SHALL be triggered
- **AND** the new schedule SHALL reflect charger A as unplugged

#### Scenario: Charger with replan_on_unplug disabled (default)
- **WHEN** charger B has `replan_on_unplug: false` (or default)
- **AND** charger B's plug sensor fires an unplug event
- **THEN** no replan SHALL be triggered
