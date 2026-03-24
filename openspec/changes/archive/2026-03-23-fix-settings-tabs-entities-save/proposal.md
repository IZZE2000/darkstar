## Why

The Settings UI has three bugs related to inverter profile entity fields and save behavior:

1. **Duplicated entities**: The System tab's "Required HA Control Entities" section shows ALL profile entities (both `category: system` and `category: battery`), duplicating fields that also appear in the Battery tab's "HA Control Entities" section.
2. **Custom entity key mismatch**: BatteryTab's dynamic field rendering uses `executor.inverter.${key}` for all entity keys, while `useSettingsForm`'s internal field list uses `executor.inverter.custom_entities.${key}` for non-standard keys. This mismatch means changes to custom entities are invisible to dirty detection and never get saved.
3. **Missing save buttons**: Several settings tabs (Battery, Solar, Water, EV, Parameters) rely solely on the `UnsavedChangesBanner` for saving, with no always-visible save button. System, Advanced, and UI tabs all have dedicated save buttons at the bottom — the others should match.

## What Changes

- Filter `generateProfileEntityFields` (or SystemTab callsite) to only include `category === 'system'` entities, removing battery entities from the System tab
- Fix BatteryTab's dynamic field key generation to use `standardInverterKeys` for correct standard/custom key routing (matching `useSettingsForm`'s logic)
- Add dedicated save buttons (with status message display) to Battery, Solar, Water, EV, and Parameters tabs, matching the pattern used by SystemTab

## Capabilities

### New Capabilities
_(none)_

### Modified Capabilities
- `sensor-configuration`: Entity fields must be routed to the correct settings tab by category, and custom entity keys must use the `custom_entities` config path consistently

## Impact

- `frontend/src/pages/settings/types.ts` — `generateProfileEntityFields` gains category filter parameter
- `frontend/src/pages/settings/SystemTab.tsx` — passes `'system'` category filter
- `frontend/src/pages/settings/BatteryTab.tsx` — fixes dynamic field key generation, adds save button
- `frontend/src/pages/settings/SolarTab.tsx` — adds save button
- `frontend/src/pages/settings/WaterTab.tsx` — adds save button
- `frontend/src/pages/settings/EVTab.tsx` — adds save button
- `frontend/src/pages/settings/ParametersTab.tsx` — adds save button
