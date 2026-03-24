## 1. Fix entity category filtering

- [x] 1.1 Add optional `category` parameter to `generateProfileEntityFields` in `types.ts` — when provided, filter `profile.entities` to only those matching the category; when omitted, return all (preserving existing behavior for `useSettingsForm`)
- [x] 1.2 Update SystemTab's `dynamicSections` memo to pass `'system'` as category to `generateProfileEntityFields`, so only system-category entities appear in "Required HA Control Entities"

## 2. Fix BatteryTab custom entity key mismatch

- [x] 2.1 Replace BatteryTab's inline `.filter().map()` dynamic field generation (lines 40-54) with a call to `generateProfileEntityFields(selectedProfile, 'battery')`, eliminating the key mismatch for non-standard entity keys
- [x] 2.2 Verify that BatteryTab's `dynamicSections` fields now use the same key format as `useSettingsForm`'s internal fields (standard keys → `executor.inverter.{key}`, custom keys → `executor.inverter.custom_entities.{key}`)

## 3. Add dedicated save buttons to tabs

- [x] 3.1 Add save button + status message block to BatteryTab — destructure `statusMessage` from `useSettingsForm`, add button/status JSX after the sections loop (matching SystemTab pattern)
- [x] 3.2 Add save button + status message block to SolarTab — destructure `statusMessage` from `useSettingsForm`, add button/status JSX
- [x] 3.3 Add save button + status message block to WaterTab — destructure `statusMessage` from `useSettingsForm`, add button/status JSX
- [x] 3.4 Add save button + status message block to EVTab — destructure `statusMessage` from `useSettingsForm`, add button/status JSX
- [x] 3.5 Add save button + status message block to ParametersTab — destructure `statusMessage` from `useSettingsForm`, add button/status JSX

## 4. Verification

- [x] 4.1 With a multi-category profile (e.g., Deye), confirm system-category entities appear only in System tab and battery-category entities appear only in Battery tab
- [x] 4.2 With a profile that has custom entities (e.g., Fronius — `grid_discharge_power`), confirm changing a custom battery entity in Battery tab triggers dirty detection and the save banner appears
- [x] 4.3 Confirm all five tabs (Battery, Solar, Water, EV, Parameters) show a dedicated save button at the bottom
