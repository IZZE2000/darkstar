## Why

The `has_*` toggles (has_solar, has_battery, has_ev_charger, has_water_heater) in the System settings tab control visibility of conditional tabs (Solar, Battery, EV, Water). Currently, when users toggle these switches and save, the tabs don't appear or disappear until the page is refreshed. This creates a poor user experience as users expect immediate visual feedback.

## What Changes

- Add event listener in Settings component to listen for `config-changed` events
- When settings are saved, automatically refresh `systemFlags` state to update tab visibility
- Tabs will instantly appear/disappear based on toggle state without requiring page refresh

## Capabilities

### New Capabilities
- *(none)*

### Modified Capabilities
- *(none - this is a UI implementation fix only)*

## Impact

- **Frontend**: Settings page (`frontend/src/pages/settings/index.tsx`)
- **No breaking changes**: Only improves UX, no API or behavior changes
