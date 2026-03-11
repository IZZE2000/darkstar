## Context

The UI20 refactor (commit `4de76a9`) reorganized settings tabs but accidentally removed `system.grid.max_power_kw` from the UI. This field is critical for planner safety - it defines the HARD grid fuse limit that cannot be exceeded.

### Current State
- `system.grid.max_power_kw` exists in `config.default.yaml` (line 25)
- Backend code uses it in `planner/solver/adapter.py:386-392` and `backend/validation.py:34`
- UI has no way to configure this value

### Bug: PV Dump Threshold Hidden
- `executor.override.excess_pv_threshold_kw` exists in `waterSections` (types.ts:1276-1283)
- Has `showIfAll: ['system.has_solar', 'system.has_water_heater']`
- `WaterTab.tsx` calls `shouldRenderField(field, form)` WITHOUT passing `config`
- Since `system.has_solar` isn't in `waterFieldList`, it's not in `form`
- Without `config` fallback, the condition fails → field hidden

### Orphan/Unwired Keys Identified
- `system.inverter.max_power_kw` - Defined but never used in code
- `grid.import_limit_kw` - Field exists in `KeplerConfig` but never populated from config
- `battery.roundtrip_efficiency_percent` - Only used in `simulation.py`, separate from `charge_efficiency`

## Goals / Non-Goals

**Goals:**
- Restore `system.grid.max_power_kw` to UI with proper placement and helper text
- Fix `excess_pv_threshold_kw` visibility bug in WaterTab
- Document orphan/unwired config keys with clarifying comments
- Add backlog entry for future inverter power limit feature

**Non-Goals:**
- Implement `system.inverter.max_power_kw` usage (future feature)
- Wire up `grid.import_limit_kw` (soft limit feature not currently used)
- Remove any existing config keys
- Move any existing fields to different tabs

## Decisions

### 1. Field Placement for `system.grid.max_power_kw`

**Decision:** Add to `systemSections` in System tab, after `system.grid_meter_type`

**Rationale:**
- Groups with other grid-related settings
- `grid_meter_type` already exists in System Profile section
- User expects grid limits near grid configuration

**Alternative considered:** Battery tab - rejected because this is a grid limit, not battery parameter

### 2. Field Definition

```typescript
{
    key: 'system.grid.max_power_kw',
    label: 'Grid Max Power (kW)',
    helper: 'HARD limit from your grid fuse. The planner will never exceed this.',
    path: ['system', 'grid', 'max_power_kw'],
    type: 'number',
}
```

**Rationale:**
- Clear label distinguishing from soft limits
- Helper text emphasizes safety nature
- Not marked `isAdvanced` - users MUST configure this

### 3. Fix for WaterTab.tsx

**Problem:** `shouldRenderField(field, form)` doesn't receive `config`
**Root cause:** `WaterTab` destructures `useSettingsForm` without `config`

**Fix:**
```typescript
// Before (line 16)
const { form, fieldErrors, loading, saving, handleChange, save, isDirty, haEntities, haLoading } = useSettingsForm(...)

// After
const { config, form, fieldErrors, loading, saving, handleChange, save, isDirty, haEntities, haLoading } = useSettingsForm(...)

// Then pass config to shouldRenderField (line 80)
shouldRenderField(field, form, config as Record<string, unknown>)
```

**Rationale:** The `showIfAll` check needs access to `system.has_solar` which lives in config, not in the water tab's form.

### 4. Config Documentation Strategy

**Decision:** Add inline YAML comments, not separate documentation file

**Changes:**
```yaml
# system.inverter.max_power_kw
# NOTE: Currently not implemented. Planned for future inverter clipping feature.
# See docs/BACKLOG.md "Inverter Clipping Support" for details.

# grid.import_limit_kw
# NOTE: Soft limit feature exists in KeplerConfig but not wired to config.
# Planned for effekttariff feature. Currently unused.

# battery.roundtrip_efficiency_percent
# NOTE: Used only in planner/simulation.py. Separate from charge_efficiency
# which is used by the MILP solver. Derives one-way efficiency as sqrt(roundtrip).
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Users may have edited config.yaml directly with grid max power value | No migration needed - field already exists in config |
| WaterTab change affects all showIfAll fields | Fix is minimal and follows SystemTab pattern |
| `system.inverter.max_power_kw` remains unused | Clear comment + backlog entry prevents confusion |

## Migration Plan

1. **No data migration needed** - config keys already exist
2. **UI-only changes** - users with existing config values will see them in UI
3. **No backend changes** - code already uses the values correctly

### Rollback

If issues arise, revert the `types.ts` and `WaterTab.tsx` changes. Config values remain valid.
