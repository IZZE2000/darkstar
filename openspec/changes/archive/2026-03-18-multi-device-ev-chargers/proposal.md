## Why

The EV charger system supports configuring multiple chargers via the `ev_chargers[]` array, but the planner aggregates them into a single blob, the executor controls only one switch, and settings like departure time and control entities live outside the array as global singletons. This means users with multiple EVs get incorrect schedules (one combined plan), only one charger is actually controlled, and per-charger departure times are impossible. This change builds true per-device EV optimization into the MILP solver and executor, establishing the foundation pattern for all future deferrable loads (water heaters, washing machines, etc).

## What Changes

- **BREAKING**: `ev_departure_time` (root-level) moves into each `ev_chargers[]` entry as `departure_time`
- **BREAKING**: `executor.ev_charger.switch_entity` moves into each `ev_chargers[]` entry as `switch_entity`
- **BREAKING**: `executor.ev_charger.replan_on_plugin` / `replan_on_unplug` move into each `ev_chargers[]` entry
- Config migration auto-migrates existing settings into the first enabled charger
- Kepler MILP solver gains per-device decision variables: `ev_charge[device, t]` and `ev_energy[device, t]` with per-device constraints (SoC, deadline, incentive buckets) sharing the grid import budget
- Schedule output gains per-device EV fields (replaces single `ev_charging_kw`)
- Executor controls each charger's switch independently with per-device state tracking
- WebSocket monitors per-device plug sensors for independent replan triggers
- Frontend EV settings page removes orphan "Departure Time" and "Control" sections; settings appear inside each charger card
- Per-device EV energy recording in slot observations

## Capabilities

### New Capabilities
- `per-device-ev-scheduling`: Per-device EV charger optimization in the MILP solver, per-device schedule output, per-device executor control, and per-device config structure. Establishes the indexed-variable pattern for future deferrable load types.

### Modified Capabilities
- `planner`: Adapter passes per-device EV configs to solver instead of aggregating. Solver creates indexed decision variables per charger. Per-device deadline, SoC, and incentive bucket constraints. Shared grid import constraint ensures fuse safety.
- `executor`: Per-device EV charger control loop with independent switch entities, state tracking, and safety timeouts per charger.
- `ev-charging-replan`: Per-device plug sensor monitoring. Each charger's plug event triggers replan independently based on its own `replan_on_plugin`/`replan_on_unplug` setting.
- `config-migration`: Migrates `ev_departure_time`, `executor.ev_charger.switch_entity`, `executor.ev_charger.replan_on_plugin`, and `executor.ev_charger.replan_on_unplug` into the first enabled `ev_chargers[]` entry. Deprecates the old paths.
- `energy-recording`: Per-device EV energy recording replaces aggregated `ev_charging_kwh` with per-charger tracking, while maintaining the aggregate for backward compatibility.

## Impact

- **Kepler solver** (`planner/solver/kepler.py`): New indexed decision variables, per-device constraints. Variable count scales linearly with number of chargers (2T per charger). Solve time may increase slightly for multi-EV setups.
- **Solver types** (`planner/solver/types.py`): `KeplerConfig` and `KeplerResultSlot` gain per-device EV structures.
- **Adapter** (`planner/solver/adapter.py`): `_aggregate_ev_chargers()` replaced with per-device config passthrough.
- **Pipeline** (`planner/pipeline.py`): Per-device deadline calculation, per-device SoC/plug state from HA.
- **Schedule format** (`planner/output/`): Per-device EV fields in schedule.json (breaking change for consumers).
- **Executor config** (`executor/config.py`): `EVChargerConfig` becomes a list of per-device configs.
- **Executor engine** (`executor/engine.py`): Per-device control loop replaces single-device EV control.
- **SlotPlan** (`executor/override.py`): `ev_charging_kw` becomes per-device dict.
- **HA Socket** (`backend/ha_socket.py`): Per-device plug sensor monitoring and replan triggers.
- **HA Client** (`backend/core/ha_client.py`): Per-device SoC and plug state fetching.
- **Config migration** (`backend/config_migration.py`): New migration step for EV settings.
- **Config validation** (`backend/api/routers/config.py`): Validate per-device EV fields.
- **Config defaults** (`config.default.yaml`): New fields in ev_chargers[], deprecated global fields removed.
- **Recorder** (`backend/recorder.py`): Per-device EV energy recording.
- **Frontend settings** (`frontend/src/pages/settings/types.ts`, `EVTab.tsx`): Remove orphan sections, add fields to entity card.
- **Frontend chart** (`frontend/src/components/ChartCard.tsx`): Per-device EV traces (nice-to-have).
- **Controller** (`executor/controller.py`): Per-device EV charging awareness in mode decisions.
