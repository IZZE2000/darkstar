## Why

A recent UI refactor (commit `4de76a9`, "UI20 device-centric settings tabs") accidentally removed the `system.grid.max_power_kw` field from the Settings UI. This is a **safety-critical parameter** that defines the HARD grid fuse limit - the maximum power that can be imported from the grid. Without UI access, users cannot configure this value, leading to potential planning errors where the solver schedules impossible power levels.

Additionally, the `executor.override.excess_pv_threshold_kw` field exists in the Water tab but is hidden due to a bug: `WaterTab.tsx` doesn't pass the `config` object to `shouldRenderField()`, so the `showIfAll: ['system.has_solar', 'system.has_water_heater']` condition fails.

Finally, several configuration parameters are orphaned (defined but unused) and need documentation.

## What Changes

### Critical Fix
- **Restore `system.grid.max_power_kw` to System tab** - Hard grid fuse limit used by planner solver (`adapter.py:386-392`) and validation (`validation.py:34`)

### Bug Fix
- **Fix `excess_pv_threshold_kw` visibility in Water tab** - `WaterTab.tsx` must destructure `config` from `useSettingsForm` and pass it to `shouldRenderField()`

### Documentation
- **Add comment to `system.inverter.max_power_kw`** - Currently unused, mark as future feature
- **Add to BACKLOG.md** - Track implementation of inverter max power constraint
- **Add comment to `grid.import_limit_kw`** - Soft limit feature exists in code but not wired to config
- **Add comment to `battery.roundtrip_efficiency_percent`** - Used only in simulation, separate from `charge_efficiency`

## Capabilities

### New Capabilities

- `grid-power-limits`: UI configuration for grid fuse hard limit (`system.grid.max_power_kw`)

### Modified Capabilities

- (None - this is a UI regression fix, no spec-level requirement changes)

## Impact

### Files Modified
- `frontend/src/pages/settings/types.ts` - Add `system.grid.max_power_kw` to systemSections
- `frontend/src/pages/settings/WaterTab.tsx` - Fix `shouldRenderField` call to pass `config`
- `config.default.yaml` - Add clarifying comments to orphan/unwired config keys
- `docs/BACKLOG.md` - Add entry for inverter max power implementation

### Backend (No changes required)
- `planner/solver/adapter.py` - Already uses `system.grid.max_power_kw`
- `backend/validation.py` - Already validates `system.grid.max_power_kw`

### User Impact
- Users can now configure their grid fuse limit through the UI
- PV Dump Threshold field is now visible in Water tab when both solar and water heater are enabled
