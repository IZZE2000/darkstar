## Context

The Settings UI dynamically generates entity fields from inverter profiles. Each profile entity has a `category` field (`"system"` or `"battery"`) that determines which tab should display it. Currently:

- **SystemTab** calls `generateProfileEntityFields(profile)` which returns ALL entities regardless of category
- **BatteryTab** correctly filters to `category === 'battery'` in its local `dynamicSections` memo, but its key generation doesn't match `useSettingsForm`'s key logic for non-standard entities
- Five tabs (Battery, Solar, Water, EV, Parameters) lack dedicated save buttons — they rely only on `UnsavedChangesBanner` which depends on dirty detection

The key mismatch specifically: BatteryTab generates keys as `executor.inverter.${key}` for all entities, while `useSettingsForm` uses `executor.inverter.custom_entities.${key}` for non-standard keys (those not in `standardInverterKeys`). This means custom entity changes are invisible to `buildPatch` → `isDirty` stays false → the banner never shows.

## Goals / Non-Goals

**Goals:**
- System tab shows only `category: system` profile entities
- Battery tab shows only `category: battery` profile entities (already correct in rendering, needs key fix)
- Custom entity keys are consistent between rendering and form state
- All settings tabs have a dedicated save button for consistent UX

**Non-Goals:**
- Changing the profile schema or category assignments
- Refactoring `useSettingsForm` internals beyond the key consistency fix
- Adding save buttons to tabs that already have them (System, Advanced, UI)

## Decisions

### 1. Add category filter parameter to `generateProfileEntityFields`

Add an optional `category` parameter to filter entities. SystemTab passes `'system'`, keeping its current callsite clean. BatteryTab will also use this function (instead of inline filtering) to ensure key generation is consistent.

**Alternative considered**: Filtering at the SystemTab callsite after calling the function. Rejected because it wouldn't fix the key generation — the function already handles standard vs. custom key routing correctly, so both tabs should use it.

### 2. Refactor BatteryTab dynamic field generation to use `generateProfileEntityFields`

Replace BatteryTab's inline `.filter().map()` (lines 40-54) with a call to `generateProfileEntityFields(profile, 'battery')`. This eliminates the key mismatch since the shared function already uses `standardInverterKeys` to route keys correctly.

### 3. Consistent save button pattern across all tabs

Extract a reusable save footer pattern matching SystemTab's existing implementation. Each tab will include a save button + status message block at the bottom. The `UnsavedChangesBanner` remains as a supplementary sticky indicator.

Pattern (from SystemTab):
```tsx
<div className="flex flex-wrap items-center gap-3">
    <button disabled={saving} onClick={() => save()} className="...btn-glow-primary...">
        {saving ? 'Saving...' : 'Save <Tab> Settings'}
    </button>
    {statusMessage && <div className="...">statusMessage</div>}
</div>
```

Tabs that need `statusMessage` from `useSettingsForm`: Battery, Solar, Water, EV, Parameters currently don't destructure it — they'll need to add it.

## Risks / Trade-offs

- **Risk**: `generateProfileEntityFields` is also used by `useSettingsForm`'s internal field computation, which intentionally adds ALL profile entities regardless of category (for form state initialization). → **Mitigation**: The category parameter is optional; when omitted, all entities are returned (preserving useSettingsForm's behavior).
- **Risk**: Adding the category filter could cause entity fields to disappear from the System tab for users who had them configured there. → **Mitigation**: The config values are stored by key path, not by tab. Moving display from System to Battery doesn't lose data — the saved values remain and are picked up by whichever tab renders the matching field.
