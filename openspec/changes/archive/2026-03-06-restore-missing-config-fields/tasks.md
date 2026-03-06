## 1. UI Field Restoration (Critical)

- [x] 1.1 Add `system.grid.max_power_kw` field to `systemSections` in `frontend/src/pages/settings/types.ts`
  - Place after `system.grid_meter_type` in System Profile section
  - Label: "Grid Max Power (kW)"
  - Helper: "HARD limit from your grid fuse. The planner will never exceed this."
  - Type: number
  - NOT marked as isAdvanced

## 2. Fix PV Dump Threshold Visibility Bug

- [x] 2.1 Update `WaterTab.tsx` to destructure `config` from `useSettingsForm`
  - Add `config` to destructured values (line 16)
- [x] 2.2 Update `shouldRenderField` call in `WaterTab.tsx` to pass `config`
  - Change `shouldRenderField(field, form)` to `shouldRenderField(field, form, config as Record<string, unknown>)`
  - Location: line 80

## 3. Config Documentation

- [x] 3.1 Add clarifying comment to `system.inverter.max_power_kw` in `config.default.yaml`
  - Note that it's not implemented yet
  - Reference BACKLOG entry
- [x] 3.2 Add clarifying comment to `grid.import_limit_kw` in `config.default.yaml`
  - Note that soft limit feature exists but not wired
- [x] 3.3 Add clarifying comment to `battery.roundtrip_efficiency_percent` in `config.default.yaml`
  - Note that it's used only in simulation.py
  - Explain relationship to charge_efficiency

## 4. Backlog Update

- [x] 4.1 Add entry to `docs/BACKLOG.md` for implementing `system.inverter.max_power_kw`
  - Category: 🔧 Technical Debt
  - Note: Currently defined in config but not used by planner
  - Relates to "Inverter Clipping Support" draft

## 5. Verification

- [x] 5.1 Verify grid max power field appears in Settings > System tab
- [x] 5.2 Verify grid max power field saves to config.yaml correctly
- [x] 5.3 Verify PV Dump Threshold is visible in Water tab when has_solar && has_water_heater
- [x] 5.4 Run `./scripts/lint.sh` to verify no errors
