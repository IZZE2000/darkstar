## Context

The Darkstar energy manager supports configuring multiple EV chargers via the `ev_chargers[]` array (ARC15 config v2), but the entire downstream stack — planner adapter, MILP solver, schedule output, executor, and WebSocket monitoring — treats all chargers as one aggregated device. The adapter sums power across chargers, takes the largest battery, merges penalty buckets, reads only the first charger's SoC/plug sensors, and passes a single set of EV parameters to the Kepler solver. The executor controls one switch entity and tracks one state machine.

Global settings that should be per-device (`ev_departure_time`, `executor.ev_charger.switch_entity`, `executor.ev_charger.replan_on_plugin/unplug`) live outside the array.

The Kepler solver uses PuLP (MILP) with binary `ev_charge[t]` and continuous `ev_energy[t]` variables indexed by time slot. The energy balance constraint sums all loads against grid import — a natural place to add per-device variables that share the grid budget.

This change establishes the per-device pattern that will later be applied to water heaters and future deferrable loads.

## Goals / Non-Goals

**Goals:**
- Per-device EV decision variables in the MILP solver with per-device constraints
- Per-device schedule output with individual charging plans per charger
- Per-device executor control with independent switch entities and state tracking
- Per-device config: departure time, switch entity, replan settings in each charger entry
- Config migration for existing users (zero manual steps)
- Shared grid import constraint ensures combined EV + house load respects fuse limit
- Pattern that can be replicated for water heaters and future load types

**Non-Goals:**
- Water heater multi-device support (Change 2, same pattern)
- Per-device load forecasting / ML training (backlog item)
- Variable-rate EV charging (current binary on/off model stays)
- Per-device frontend chart traces (nice-to-have, not required)
- Changes to the learning system or Aurora models

## Decisions

### Decision 1: Per-device indexed MILP variables

**Choice**: Add a device index `d` to EV decision variables: `ev_charge[d][t]` (binary), `ev_energy[d][t]` (continuous), `ev_bucket_charged[d][i]` (continuous per incentive bucket per device).

**Alternatives considered**:
- *Run solver once per device*: Simpler but devices can't share the grid budget. Two EVs could both plan to charge at full power in the same slot, exceeding the fuse. Would require post-processing capacity allocation.
- *Sequential solver runs with capacity reservation*: First EV "reserves" grid capacity, second EV sees reduced budget. Order-dependent and suboptimal.

**Rationale**: PuLP handles indexed variables natively via `LpVariable.dicts`. Per-device variables within one MILP let the solver globally optimize which charger charges when, naturally respecting the shared grid import constraint. Variable count increases by ~2T per additional charger (T=96 for 24h), which is trivial for GLPK/CBC.

### Decision 2: Per-device KeplerConfig structure

**Choice**: Replace scalar EV fields in `KeplerConfig` with a list of `EVChargerInput` dataclasses:

```
@dataclass
class EVChargerInput:
    id: str
    max_power_kw: float
    battery_capacity_kwh: float
    current_soc_percent: float
    plugged_in: bool
    deadline: datetime | None
    incentive_buckets: list[IncentiveBucket]
```

`KeplerConfig.ev_chargers: list[EVChargerInput]` replaces the flat `ev_max_power_kw`, `ev_battery_capacity_kwh`, `ev_current_soc_percent`, `ev_plugged_in`, `ev_deadline`, `ev_incentive_buckets` fields.

**Rationale**: Clean separation. Each charger carries its own complete state. The adapter builds this list from config + HA sensor data. Old scalar fields are removed (breaking change to solver interface, but internal only).

### Decision 3: Per-device schedule output

**Choice**: Add `ev_chargers` dict to each schedule slot:

```json
{
  "ev_charging_kw": 18.4,
  "ev_chargers": {
    "ev_charger_1": {"charging_kw": 11.0},
    "ev_charger_2": {"charging_kw": 7.4}
  }
}
```

Keep aggregate `ev_charging_kw` as the sum for backward compatibility (chart, recorder, status API).

**Alternatives considered**:
- *Only per-device, no aggregate*: Breaks too many consumers at once.
- *Array instead of dict*: Dict keyed by ID is easier to look up in executor.

**Rationale**: Additive change to schedule format. Existing consumers read `ev_charging_kw` as before. New per-device consumers read `ev_chargers` dict. Executor uses the dict to control each switch.

### Decision 4: Per-device SlotPlan in executor

**Choice**: Add `ev_charger_plans: dict[str, float]` to `SlotPlan`, mapping charger ID to planned kW. Keep `ev_charging_kw` as aggregate for backward compat in controller logic.

**Rationale**: The executor's `_control_ev_charger()` method becomes a loop over `ev_charger_plans.items()`, looking up each charger's config (switch entity, state) by ID.

### Decision 5: Per-device executor state tracking

**Choice**: Replace scalar state variables (`_ev_charging_active`, `_ev_charging_started_at`, `_ev_charging_slot_end`, etc.) with a dict keyed by charger ID: `_ev_charger_states: dict[str, EVChargerState]`.

```
@dataclass
class EVChargerState:
    charging_active: bool = False
    started_at: datetime | None = None
    slot_end: datetime | None = None
    detected_last_tick: bool = False
    power_fetch_failed: bool = False
    zero_power_ticks: int = 0
    failure_notified: bool = False
```

**Rationale**: Each charger has independent safety timeouts and state transitions. Avoids tangled state when one charger starts/stops while another continues.

### Decision 6: Per-device executor config

**Choice**: Replace single `EVChargerConfig` with `ev_chargers: list[EVChargerDeviceConfig]` in `ExecutorConfig`:

```
@dataclass
class EVChargerDeviceConfig:
    id: str
    name: str
    switch_entity: str | None = None
    max_power_kw: float = 7.4
    battery_capacity_kwh: float | None = None
    replan_on_plugin: bool = True
    replan_on_unplug: bool = False
```

**Rationale**: Directly mirrors the config array. Loaded from `ev_chargers[]` entries. No more reading from `executor.ev_charger`.

### Decision 7: Config migration strategy

**Choice**: In `config_migration.py`, add a migration step that:
1. If `ev_departure_time` exists at root level AND first enabled `ev_chargers[]` entry has no `departure_time`, copy the value into the first enabled charger entry.
2. If `executor.ev_charger.switch_entity` exists AND first enabled `ev_chargers[]` entry has no `switch_entity`, copy it.
3. Same for `replan_on_plugin` and `replan_on_unplug`.
4. Add `ev_departure_time`, `executor.ev_charger.switch_entity`, `executor.ev_charger.replan_on_plugin`, `executor.ev_charger.replan_on_unplug` to the deprecated keys registry.
5. Bump `config_version` to 3 (or handle via presence detection without version bump).

**Rationale**: Zero manual steps for existing users. Migration is idempotent (only copies if target field missing). Backup is created before write (existing migration infrastructure).

### Decision 8: Per-device plug sensor monitoring

**Choice**: In `ha_socket.py`, register plug sensors for ALL enabled chargers (not just first). Each charger's plug event checks that specific charger's `replan_on_plugin`/`replan_on_unplug` setting.

**Rationale**: Already partially implemented — WebSocket maps per-device sensors. Just needs to track which charger ID each plug sensor belongs to, and read that charger's replan setting.

### Decision 9: Per-device HA state fetching

**Choice**: In `ha_client.py`'s `get_initial_state()`, fetch SoC and plug state for ALL enabled chargers (not just first). Return a list of `{id, soc_percent, plugged_in}` dicts instead of scalar values.

**Rationale**: The pipeline needs per-device SoC and plug state to build per-device `EVChargerInput` objects for the solver.

### Decision 10: Solver skip logic for unplugged/disabled chargers

**Choice**: The solver skips creating decision variables for chargers that are not plugged in (no point optimizing charging for an absent car). Only plugged-in chargers get variables and constraints.

**Rationale**: Reduces solver complexity. An unplugged charger has zero decision space. The adapter filters before passing to solver.

## Risks / Trade-offs

**[Risk] Solver time increases with many chargers** → Each charger adds ~2T binary + 2T continuous variables. For 2-3 chargers this is negligible (GLPK handles 1000+ variables easily). For extreme cases (5+ chargers), the 30s timeout is the safety net. Mitigation: monitor solve time in production logs.

**[Risk] Schedule format change breaks external consumers** → The aggregate `ev_charging_kw` field is preserved for backward compatibility. Per-device data is additive. Mitigation: document the new format in release notes.

**[Risk] Config migration edge cases** → User has multiple enabled chargers but global settings were meant for charger #2. Mitigation: always migrate to first enabled charger (deterministic, documented). User can reassign in settings UI after upgrade.

**[Risk] Executor complexity increases** → Per-device state tracking loop instead of simple scalar. Mitigation: `EVChargerState` dataclass keeps state clean. Each iteration is independent (no cross-device coupling in control logic).

**[Risk] WebSocket replan storm** → Multiple chargers plugging in simultaneously could trigger multiple rapid replans. Mitigation: existing `trigger_now()` debouncing in scheduler service prevents concurrent runs. No change needed.

**[Trade-off] Binary charging model stays** → Each charger is still on/off at max power per slot. True variable-rate charging (adjusting amperage) would require continuous power variables and charger communication protocols (OCPP). Out of scope — the binary model works for the vast majority of home charger setups.

## Migration Plan

1. **Config migration runs at startup** (existing infrastructure). New migration step copies global EV settings into first charger entry. Old paths added to deprecated keys registry.
2. **Frontend settings page** updated in same release. Orphan sections removed, fields appear in charger cards.
3. **Rollback**: If issues found, revert code. Config backup (created by migration) can be restored. The deprecated fields are only removed from the config file after successful migration, and the migration is idempotent.

## Open Questions

None — all design decisions are resolved based on the investigation. The pattern is straightforward and matches PuLP's native indexed variable support.
