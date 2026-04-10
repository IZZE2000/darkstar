## Context

The Darkstar energy manager supports configuring multiple water heaters via the `water_heaters[]` array (ARC15 config v2), but the entire downstream stack treats all heaters as one aggregated device. The adapter (`_aggregate_water_heaters()`) sums power across heaters, sums `min_kwh_per_day`, but uses only the first heater's timing settings (`max_hours_between_heating`, `water_min_spacing_hours`). The Kepler solver creates a single `water_heat[t]` binary and `water_start[t]` binary indexed only by time slot. The executor reads only the first enabled heater's `target_entity` and controls it with a single temperature decision.

Global settings live outside the array: `water_heating:` (scheduling parameters, comfort level, vacation mode) and `executor.water_heater:` (temperature setpoints). These are house-level preferences that apply to all heaters — they should stay global, unlike EV settings which were per-device.

The Kepler solver uses PuLP (MILP) with binary `water_heat[t]` and `water_start[t]` variables. Per-device constraints include: daily minimum kWh (soft, per calendar day with deferral), max block duration (sliding window), min spacing between block starts (hard constraint), and mid-block locking (force ON slots). The energy balance constraint sums all loads against grid import — the natural place to add per-device variables.

This change follows the exact per-device indexed MILP variable pattern established by `multi-device-ev-chargers`.

## Goals / Non-Goals

**Goals:**
- Per-device water heater decision variables in the MILP solver with per-device constraints
- Per-device schedule output with individual heating plans per heater
- Per-device executor control with independent target entities per heater
- Per-device energy recording in slot observations
- Global scheduling parameters (comfort, deferral, penalties) and temperature setpoints stay global
- Pattern consistent with multi-device-ev-chargers change

**Non-Goals:**
- Per-device temperature setpoints (these are house-level preferences)
- Per-device comfort levels or deferral settings (global scheduling policy)
- Moving `water_heating:` or `executor.water_heater:` sections into the array
- Config migration (no settings need to move — `target_entity` is already in the array)
- Per-device load forecasting / ML training (backlog item)
- Vacation mode changes (stays global)
- Water heater replan triggers (water heaters have no plug sensor equivalent)

## Decisions

### Decision 1: Per-device indexed MILP variables

**Choice**: Add a device index `d` to water heater decision variables: `water_heat[d][t]` (binary on/off), `water_start[d][t]` (binary block start detection).

**Alternatives considered**:
- *Keep aggregated model*: Can't handle heaters with different power ratings or timing needs. Two 3kW heaters get a combined 6kW plan that only one heater executes.
- *Run solver once per heater*: Heaters can't share the grid budget. Both could plan to heat in the same cheap slot, exceeding fuse limit.

**Rationale**: PuLP handles indexed variables natively via `LpVariable.dicts`. Per-device variables within one MILP let the solver globally optimize which heater heats when, naturally respecting the shared grid import constraint. Binary variables increase by ~2T per additional heater (T=96 for 24h), trivial for GLPK/CBC.

### Decision 2: Per-device WaterHeaterInput dataclass

**Choice**: Replace scalar water fields in `KeplerConfig` with a list of `WaterHeaterInput` dataclasses:

```
@dataclass
class WaterHeaterInput:
    id: str
    power_kw: float
    min_kwh_per_day: float
    max_hours_between_heating: float
    min_spacing_hours: float
    force_on_slots: list[int] | None = None
```

`KeplerConfig.water_heaters: list[WaterHeaterInput]` replaces `water_heating_power_kw`, `water_heating_min_kwh`, `water_min_spacing_hours`, and `force_water_on_slots`. Global settings (comfort penalties, block penalties, reliability penalty, deferral, max block hours) stay as scalar fields on `KeplerConfig` since they apply to all heaters.

**Rationale**: Clean separation between per-device physical properties and global scheduling policy. Each heater carries its own power, daily requirement, and timing constraints. The adapter builds this list from the `water_heaters[]` config array.

### Decision 3: Per-device schedule output

**Choice**: Add `water_heaters` dict to each schedule slot:

```json
{
  "water_heating_kw": 6.0,
  "water_heaters": {
    "main_tank": {"heating_kw": 3.0},
    "upstairs_tank": {"heating_kw": 3.0}
  }
}
```

Keep aggregate `water_heating_kw` as the sum for backward compatibility (chart, recorder, status API, SoC target calculation).

**Rationale**: Additive change. Existing consumers read `water_heating_kw` as before. Executor uses the dict to control each heater independently.

### Decision 4: Per-device SlotPlan in executor

**Choice**: Add `water_heater_plans: dict[str, float]` to `SlotPlan`, mapping heater ID to planned kW. Keep `water_kw` as aggregate for backward compat in controller logic.

**Rationale**: The executor's water heater control becomes a loop over `water_heater_plans.items()`, looking up each heater's config (`target_entity`) by ID.

### Decision 5: Per-device executor config

**Choice**: Replace single `WaterHeaterConfig` with `water_heaters: list[WaterHeaterDeviceConfig]` in `ExecutorConfig`:

```
@dataclass
class WaterHeaterDeviceConfig:
    id: str
    name: str
    target_entity: str | None = None
    power_kw: float = 3.0
```

Temperature setpoints (`temp_normal`, `temp_off`, `temp_boost`, `temp_max`) stay on a global `WaterHeaterGlobalConfig` (renamed from `WaterHeaterConfig`), since temperature preferences are house-level.

**Rationale**: Directly mirrors the config array for per-device fields. Global temp settings stay in `executor.water_heater:` where they belong.

### Decision 6: Per-device controller decisions

**Choice**: Replace scalar `water_temp: int` in `ControllerDecision` with `water_temps: dict[str, int]` mapping heater ID to temperature target. Keep `water_temp` as fallback for single-heater setups.

**Rationale**: Each heater can be independently turned on/off based on its per-device plan. All heaters use the same temperature setpoints (global), but some may be heating while others are off in the same slot.

### Decision 7: Global settings stay global

**Choice**: `water_heating:` section (comfort_level, defer_up_to_hours, block_start_penalty_sek, reliability_penalty_sek, block_penalty_sek, enable_top_ups, vacation_mode) and `executor.water_heater:` temperature setpoints remain in their current locations. No config migration needed.

**Alternatives considered**:
- *Move temp setpoints per-device*: Different water heaters rarely need different temperatures. Adds config complexity for no practical benefit.
- *Move comfort/penalty settings per-device*: These are scheduling policy preferences, not device properties.

**Rationale**: Unlike EV chargers (which have per-device departure times and switch entities that were incorrectly global), water heater global settings are genuinely global — house-level comfort and temperature policy. The only per-device properties are physical: power rating, daily energy need, timing constraints, and control entity — all already in the array.

### Decision 8: Per-device mid-block locking

**Choice**: `force_water_on_slots` becomes per-device: `WaterHeaterInput.force_on_slots: list[int] | None`. The pipeline detects mid-block state per heater (is this specific heater currently in a heating block?) and locks only that heater's slots.

**Rationale**: With per-device scheduling, one heater might be mid-block while another is idle. Locking must be per-device to avoid forcing an idle heater ON.

### Decision 9: Per-device daily tracking

**Choice**: `water_heated_today_kwh` becomes per-device via a new field on `WaterHeaterInput`. The pipeline tracks how much each heater has already heated today (from recorder data or sensor state) and passes it per-device.

**Rationale**: Each heater has an independent daily minimum. Today's progress must be tracked per-device for the soft constraint to work correctly.

### Decision 10: No config migration needed

**Choice**: Unlike the EV change, no config migration step is required. All per-device fields (`target_entity`, `power_kw`, `min_kwh_per_day`, timing settings) are already in the `water_heaters[]` array. Global settings stay where they are.

**Rationale**: The ARC15 migration already placed per-device fields correctly. The problem was only in the downstream code (adapter aggregation, solver, executor) — not in the config structure.

## Risks / Trade-offs

**[Risk] Solver time increases with many heaters** → Each heater adds ~2T binary variables. For 2-3 heaters this is negligible. For extreme cases, the 30s timeout is the safety net.

**[Risk] Per-device daily min constraints may conflict** → Two heaters each needing 6 kWh/day on cheap slots could compete. The solver handles this naturally — it optimizes globally across all heaters and slots.

**[Risk] Mid-block detection complexity** → Per-device mid-block detection requires knowing each heater's current state independently. The LoadDisaggregator already tracks per-device power, so detecting "is this heater currently ON?" is feasible.

**[Risk] Executor temperature control complexity** → Each heater needs independent ON/OFF decisions but uses global temp setpoints. The loop is straightforward: for each heater, set `temp_normal` if planned kW > 0, else `temp_off`.

**[Trade-off] Global temp setpoints for all heaters** → A user with fundamentally different heater types (e.g., tank vs. heat pump) might want different temperatures. We accept this limitation — it can be added later without architectural changes by moving temp setpoints into the array.

## Open Questions

None — the pattern is established by the EV change and water heaters are simpler (no SoC, no plug sensors, no deadlines, no replan triggers).
