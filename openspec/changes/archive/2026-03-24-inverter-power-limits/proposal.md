## Why

The planner has no awareness of inverter hardware limits. It only knows the grid fuse (`system.grid.max_power_kw`) and uses that as both the import and export ceiling. In reality, hybrid inverters have two additional physical limits: max AC output power and max DC input from PV strings. This causes over-optimistic export schedules — the planner may schedule 14kW export when the inverter can only produce 10kW AC. The inverter silently clips the excess, wasting battery cycles and producing incorrect cost calculations.

## What Changes

- Add `system.inverter.max_ac_power_kw` config key — maximum AC power the inverter can produce (PV + battery discharge combined)
- Add `system.inverter.max_dc_input_kw` config key — maximum DC power from PV strings (used to clip PV forecast)
- **BREAKING**: Remove unused `system.inverter.max_power_kw` config key (was never wired to anything)
- **BREAKING**: Remove unused `executor.controller.inverter_ac_limit_kw` config key (parsed but never used)
- Add planner constraint: PV AC contribution + battery discharge ≤ `max_ac_power_kw` per slot
- Pre-clip PV forecast by `max_dc_input_kw` before it enters the solver
- Expose both new keys in Settings UI System tab with tooltip help text
- Add config validation warnings when keys are missing

## Capabilities

### New Capabilities
- `inverter-power-limits`: Inverter AC output and DC input power limit modeling in the planner, including config, validation, solver constraints, and UI exposure

### Modified Capabilities
- `grid-power-limits`: Update spec to clarify that `system.grid.max_power_kw` is the grid fuse limit only (not inverter limit), and that export is also capped by inverter AC output
- `planner`: Add requirement for inverter AC constraint and PV DC clipping in the solver

## Impact

- **Config**: `config.default.yaml` — replace `system.inverter.max_power_kw` with two new keys, remove `executor.controller.inverter_ac_limit_kw`
- **Planner adapter**: `planner/solver/adapter.py` — read new keys, clip PV, pass AC limit to solver
- **Planner solver**: `planner/solver/kepler.py` — add inverter AC output constraint
- **Solver types**: `planner/solver/types.py` — add `max_inverter_ac_kw` field to `KeplerConfig`
- **Frontend**: `config-help.json`, `settings/types.ts` — add fields and tooltips
- **Backend validation**: `backend/api/routers/config.py` — warn when keys missing
- **Config migration**: `backend/config_migration.py` — migrate old key names
