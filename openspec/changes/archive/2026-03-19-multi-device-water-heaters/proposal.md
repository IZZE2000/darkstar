## Why

The water heater system supports configuring multiple heaters via the `water_heaters[]` array (ARC15 config v2), but the planner aggregates them into a single blob (`_aggregate_water_heaters()` sums power, takes first heater's timing settings), the executor controls only one `target_entity`, and the solver creates a single `water_heat[t]` decision variable. Users with multiple water heaters get a combined plan that controls only the first heater. Global settings (temperature setpoints, scheduling parameters) live outside the array in `water_heating:` and `executor.water_heater:` sections. This mirrors the exact same flaw fixed for EV chargers in the `multi-device-ev-chargers` change — following the same per-device indexed MILP variable pattern.

## What Changes

- Kepler MILP solver gains per-device decision variables: `water_heat[device, t]` (binary) and `water_start[device, t]` (binary) with per-device constraints (daily min kWh, block duration, spacing) sharing the grid import budget
- Adapter replaces `_aggregate_water_heaters()` with per-device config passthrough via `WaterHeaterInput` dataclass
- `KeplerConfig` replaces scalar water fields with `water_heaters: list[WaterHeaterInput]`
- Schedule output gains per-device water heater fields alongside aggregate `water_heating_kw`
- `SlotPlan` gains `water_heater_plans: dict[str, float]` for per-device planned kW
- Executor controls each heater's `target_entity` independently with per-device temperature decisions
- `WaterHeaterConfig` becomes a list of per-device configs, each with `target_entity` from its array entry
- Per-device water energy recording in slot observations
- **Temperature setpoints and global scheduling parameters stay in `water_heating:` / `executor.water_heater:` sections** — these are house-level preferences, not per-device settings
- Frontend settings: no structural changes needed (water heater array already has per-device fields, global scheduling/temp sections are correct as-is)

## Capabilities

### New Capabilities
- `per-device-water-scheduling`: Per-device water heater optimization in the MILP solver with indexed binary decision variables, per-device schedule output, per-device executor control, and per-device energy recording.

### Modified Capabilities
- `planner`: Adapter passes per-device water heater configs to solver instead of aggregating. Solver creates indexed decision variables per heater with per-device daily min, block duration, and spacing constraints. Shared energy balance ensures grid budget is respected.
- `executor`: Per-device water heater control loop with independent target entities and temperature control per heater.
- `water-heater-execution`: Per-device temperature control replaces single-device control. Each heater gets independent heating/off decisions.
- `energy-recording`: Per-device water energy recording replaces aggregated `water_kwh` with per-heater tracking, maintaining aggregate for backward compatibility.

## Impact

- **Kepler solver** (`planner/solver/kepler.py`): New indexed decision variables `water_heat[d][t]`, `water_start[d][t]`. Per-device daily min, block duration, spacing constraints. Variable count scales linearly with heater count.
- **Solver types** (`planner/solver/types.py`): Scalar water fields replaced with `water_heaters: list[WaterHeaterInput]`. `KeplerResultSlot` gains per-device water output.
- **Adapter** (`planner/solver/adapter.py`): `_aggregate_water_heaters()` replaced with per-device config builder.
- **Pipeline** (`planner/pipeline.py`): Per-device mid-block locking via `force_water_on_slots` per heater.
- **Schedule format** (`planner/output/`): Per-device water heater fields in schedule alongside aggregate `water_heating_kw`.
- **Executor config** (`executor/config.py`): `WaterHeaterConfig` becomes list of per-device configs with `target_entity` per heater. Temp setpoints stay global.
- **Executor engine** (`executor/engine.py`): Per-device water heater control loop replaces single call.
- **Executor actions** (`executor/actions.py`): `set_water_temp()` accepts device-specific target entity.
- **Controller** (`executor/controller.py`): Per-device water temperature decisions in `ControllerDecision`.
- **SlotPlan** (`executor/override.py`): `water_kw` becomes per-device dict plus aggregate.
- **Recorder** (`backend/recorder.py`): Per-device water energy recording.
- **Config defaults** (`config.default.yaml`): No changes needed — per-device fields already in array, global sections stay.
- **Frontend settings** (`frontend/src/pages/settings/types.ts`): Minimal changes — entity array already has per-device fields, scheduling and temperature sections correctly reference global paths.
