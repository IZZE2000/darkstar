## Context

The current excess PV handling lives entirely in the executor as a reactive override (`EXCESS_PV_HEATING`). When real-time PV exceeds load by 2kW and battery is ≥95%, it sets water heater to 85°C. This has three problems:

1. **Bug**: The override only populates the scalar `water_temp` field, not the per-device `water_temps` dict used by the multi-device water heater control loop — so the engine silently drops the action
2. **Architecture**: A 30-minute-ahead planner with PV forecasts should proactively schedule excess PV utilization, not react to it
3. **Limited**: Only water heater users benefit; users without water heaters have no sink for excess PV

Kepler already models water heating as a deferrable load, PV forecasts, battery charging, and grid export. Adding excess PV dispatch fits naturally.

## Goals / Non-Goals

**Goals:**
- Remove `EXCESS_PV_HEATING` override from the executor
- Kepler schedules water heater boost (85°C) into forecast excess PV slots
- Users can toggle between "Water Heater Boost", "Custom HA Entity", or "Disabled" as their excess PV sink
- Custom HA entity toggles on/off during excess PV slots
- Chart shows boost water bars as distinct teal color with sharp glow; custom entity bars with amber color and sharp glow; all other bars have no glow
- PV forecast overlay renders behind all bars
- Settings UI in Hardware Features section

**Non-Goals:**
- kWh tracking or energy metering for custom entity (solver uses estimated power_kw for reward sizing only)
- Notification changes (no longer needed — planned, not reactive)
- Removing other override types (low SoC, slot failure, manual, force actions stay intact)

## Decisions

### Decision 1: Single MILP with pre-calculated excess PV slots as coarse filter + SoC threshold as real gate

Excess PV slots are pre-calculated from raw forecasts before the solver runs: `excess[t] = max(0, pv_forecast[t] - load_forecast[t] - min_water_heat_forecast[t] - min_ev_forecast[t]) > 0`. These become fixed binary flags used as a **coarse upper bound** — they exclude slots where PV can't possibly exceed demand (e.g., nighttime).

The **real gate** is a solver-internal SoC threshold constraint: boost and custom entity variables can only activate when the solver's projected battery SoC >= 95%. This ensures the priority order: **battery charges first → EV charges → when battery is near full → sink activates**.

**Alternative considered**: Running a second MILP pass using the Phase 1 solution to calculate excess. Rejected because excess is determined by forecasts — the same inputs already available before the solve. Using Phase 1 output adds solver complexity and runtime with no accuracy benefit.

**Alternative considered**: Pre-calculated flags alone without SoC constraint. Rejected because flags don't account for battery state — they'd mark a slot as "excess" even at 20% SoC when the battery should be charging.

**Rationale**: KISS. Pre-calculated flags are a fast coarse filter. The SoC big-M constraint is the real gate. Together they produce correct priority ordering without a second solver invocation.

### Decision 2: Boost is per-slot binary, no daily energy budget, gated by SoC >= 95%

When the excess PV sink is `water_heater_boost`, the solver creates a binary boost variable for each water heater in each slot. Boost is constrained by **two conditions**: (1) pre-calculated excess PV flag is true (coarse filter), AND (2) projected SoC >= 95% (real gate). There is no daily kWh cap — the SoC constraint and solver's energy balance handle the economics naturally. The executor's physical thermostat prevents overheating.

**Alternative considered**: Per-device `boost_kwh_per_day` parameter. Rejected because it adds unnecessary configuration — the SoC constraint bounds when boost can happen, the solver decides whether it's economically worthwhile vs exporting, and the physical thermostat handles the rest. Three natural constraints make a config knob redundant.

### Decision 3: Sink reward incentivizes the solver (same for both sink types)

Boost adds energy to the demand side of the solver's energy balance, competing with grid export. Without an incentive, the solver always prefers exporting (which earns money) over boosting the water heater. A configurable `boost_reward_sek_per_kwh` (default 0.5) is subtracted from the objective function for each kWh of boost in excess PV slots. When the reward exceeds the export price, the solver prefers boost. When export price is higher, it exports.

The same reward applies to both sink types: water heater boost and custom entity. The concept is the same — "how much is it worth to direct excess PV to this sink vs exporting." For water heater boost, the reward is `reward * boost_var * heater_kw * h`. For custom entity, the reward is `reward * custom_entity_active_var * power_kw * h` where `power_kw` is configurable (default 1.0 kW).

The reward is exposed in Settings under Advanced → Excess PV Dispatch.

### Decision 4: Custom entity is a solver variable with reward and configurable power

The custom entity sink is a binary solver variable `custom_entity_active[t]`, constrained the same way as water heater boost: (1) pre-calculated excess PV flag must be true, AND (2) projected SoC >= configurable threshold (default 95%). The same reward applies. The reward is sized by a configurable `power_kw` (default 1.0 kW): `reward * custom_entity_active_var * power_kw * h`. The entity's power consumption is added to the energy balance demand side (`custom_entity_active[t] * power_kw * h`), ensuring the solver makes genuine economic tradeoffs between exporting and directing energy to the entity. This ensures the solver correctly weighs the economic value — a 3 kW pool pump should earn 3x the reward of a 1 kW device.

**Rationale**: The custom entity must be a proper MILP variable (not a pre-calculated flag) so the solver can decide whether to activate it based on the full optimization context (battery state, export prices, reward). Using pre-calculated flags directly would bypass the solver entirely, ignoring battery priority. The `power_kw` field ensures the reward is proportional to actual energy use, preventing misleading solver economics. Adding the entity's consumption to the energy balance prevents the solver from activating the entity "for free" without accounting for the energy cost.

### Decision 5: Excess PV sink is a single exclusive choice in settings

The user picks ONE sink: "Water Heater Boost", "Custom Entity", or "Disabled". Not multiple concurrent sinks. If `has_water_heater=false`, the water heater option is hidden, leaving "Custom Entity" or "Disabled".

**Rationale**: Simplicity. Priority ordering (battery → EV → sink) is already determined by the optimizer. Supporting multiple configurable sinks adds UI and executor complexity with minimal benefit at this stage.

### Decision 6: Excess PV detection in Kepler uses forecast values only

Excess PV slots are identified purely from forecasts: `excess[t] = max(0, pv_forecast[t] - load_forecast[t] - ...)`. No real-time sensor data involved. The planner runs every 30 minutes, so forecasts are fresh.

**Rationale**: The whole point is proactive planning. Real-time deviations are handled by the inverter's built-in self-consumption logic (exports any surplus automatically).

### Decision 7: Chart visualization

Boost water heating gets its **own separate bar dataset** (not a scriptable color on the normal dataset). This is required because:
- The glow plugin reads `borderColor` as a string — scriptable `borderColor` breaks the glow plugin
- A separate dataset allows static `borderColor`, `glowBlur`, and `glowOpacity` specific to boost bars

Normal water heating: `rgba(78, 168, 222, 0.25)` fill / `#4EA8DE` border, no glow (`glow: false`)
Boost water heating: `rgba(0, 255, 200, 0.91)` fill / `#00ffc8ff` border (bright teal), sharp glow (`glowBlur: 20`, `glowOpacity: 1.0`)
Custom entity: `rgba(255, 182, 64, 0.81)` fill / `#FF9F40` border (amber), sharp glow (`glowBlur: 20`, `glowOpacity: 1.0`)

All other bar datasets have `glow: false`. Only boost and custom entity have glow enabled.

The PV forecast line dataset has `order: 20` (higher than bars at `order: 0`) so it renders behind all bars.

Both boost and normal water heating datasets toggle together via the "Water Heating" overlay pill. Dataset indices in overlay toggle code:
- 6: water (normal), 7: water (boost), 8: EV, 9: excess PV sink (custom entity)
- Both ds[6] and ds[7] are toggled by `overlays.water`

### Decision 9: Configurable SoC threshold (default 95%) ensures battery-first priority

Excess PV must always charge the battery first. The sink (water heater boost or custom entity) can only activate when the solver's projected SoC >= a configurable threshold (default 95%). This is implemented via a big-M binary formulation:

```
soc_binary[t] ∈ {0, 1}
soc[t] >= threshold_kWh - M * (1 - soc_binary[t])   // if binary=1, SoC must be >= threshold
boost[t] <= soc_binary[t]                             // boost requires binary=1
custom_entity_active[t] <= soc_binary[t]              // custom entity requires binary=1
```

Where `M = capacity_kWh` (big enough to make the constraint inert when binary=0).

The threshold is configurable via `executor.excess_pv.soc_threshold_percent` (default 95%). 95% provides a small buffer — the battery is effectively full but not absolutely maxed out, leaving room for forecast error and PV variability. Users with slower charging curves near the top may want to lower it (e.g., 90%). EV charging is handled by the existing solver constraints (plugs in, has deadlines) and is naturally prioritized by the solver's objective.

**Alternative considered**: Fixed 90% threshold. Rejected — too opinionated. Users know their batteries best. Hardcoded 100% is too strict (SoC may fluctuate near max due to forecast imprecision).

### Decision 10: Configuration structure

```yaml
executor:
  excess_pv:
    sink: water_heater_boost  # water_heater_boost | custom_entity | disabled
    boost_reward_sek_per_kwh: 0.5  # Reward for using excess PV at sink vs exporting
    soc_threshold_percent: 95  # Battery must be above this SoC% for sink to activate
    custom_entity:
      entity: ""
      on_value: "1"
      off_value: "0"
      power_kw: 1.0  # Estimated power consumption (kW) — sizes solver reward
```

No per-device boost config needed — boost is driven by the SoC threshold constraint, pre-calculated excess PV flags (coarse filter), solver energy balance, and the boost reward.

## Risks / Trade-offs

- **PV forecast error**: If PV forecast underestimates, excess goes to grid export (inverter handles this naturally). If it overestimates, the water heater boost may draw from battery briefly — but boost is only scheduled when battery SoC >= 95%, so the draw is minimal. Mitigation: The inverter's self-consumption logic handles surplus naturally.
- **Boost accuracy**: No daily kWh budget means the solver may schedule boost in more slots than physically needed. Mitigation: The executor's thermostat prevents overheating — boost commands to an already-hot tank are no-ops.
- **Boost vs export tradeoff**: The boost reward determines when boost beats export. Too high = wastes export revenue. Too low = never boosts. Default of 0.5 SEK/kWh means boost only activates when export price is below 0.5.
- **Override removal**: If Kepler fails to produce a schedule, there's no fallback for excess PV utilization. Mitigation: Inverter auto-exports surplus — no energy is wasted. The SLOT_FAILURE_FALLBACK override handles safe-state and MUST set the custom entity sink to `off_value` to avoid it being left on indefinitely.
- **SoC threshold rigidity**: Default 95% may not suit all batteries. Users with slower charging curves near the top might rarely hit 95%. Mitigation: The threshold is configurable — users can lower it (e.g., 90%) to match their battery behavior.

## Open Questions

- ~~Boost kWh default: derive from tank volume config, or let user set directly?~~ Resolved: no daily kWh budget needed.
- ~~Boost reward default~~: Resolved: 0.5 SEK/kWh.
