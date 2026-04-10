## 1. Config Structure & Migration

- [x] 1.1 Add per-device fields to `config.default.yaml`: `departure_time`, `switch_entity`, `replan_on_plugin`, `replan_on_unplug` in each `ev_chargers[]` entry. Remove global `ev_departure_time` and `executor.ev_charger` section from the template.
- [x] 1.2 Add migration step in `backend/config_migration.py`: copy `ev_departure_time` → first enabled charger's `departure_time`, copy `executor.ev_charger.switch_entity` → first enabled charger's `switch_entity`, copy replan settings. Only copy when target field is absent/empty.
- [x] 1.3 Add `ev_departure_time` and `executor.ev_charger.*` entries to deprecated keys registry.
- [x] 1.4 Update `backend/api/routers/config.py` validation to validate per-device EV fields (`departure_time` format, `switch_entity` format).
- [x] 1.5 Write tests for config migration: verify values migrate to first enabled charger, idempotency, no-op when already migrated, edge case with no enabled chargers.

## 2. Solver Types & Adapter

- [x] 2.1 Create `EVChargerInput` dataclass in `planner/solver/types.py` with fields: `id`, `max_power_kw`, `battery_capacity_kwh`, `current_soc_percent`, `plugged_in`, `deadline`, `incentive_buckets`.
- [x] 2.2 Replace scalar EV fields in `KeplerConfig` with `ev_chargers: list[EVChargerInput]`. Remove `ev_max_power_kw`, `ev_battery_capacity_kwh`, `ev_current_soc_percent`, `ev_plugged_in`, `ev_deadline`, `ev_incentive_buckets`.
- [x] 2.3 Add per-device EV output to `KeplerResultSlot`: replace `ev_charge_kw: float` with `ev_charger_results: dict[str, float]` (charger_id → kW) plus aggregate `ev_charge_kw` for compat.
- [x] 2.4 Replace `_aggregate_ev_chargers()` in `planner/solver/adapter.py` with per-device config builder that creates `EVChargerInput` list from `ev_chargers[]` config + HA state.
- [x] 2.5 Update `config_to_kepler_config()` to populate `KeplerConfig.ev_chargers` list instead of scalar fields.
- [x] 2.6 Write tests for adapter: verify per-device configs built correctly, disabled chargers excluded, unplugged chargers included in config but filtered in solver.

## 3. Kepler MILP Solver

- [x] 3.1 Refactor EV variable creation in `kepler.py`: create `ev_charge[d][t]` and `ev_energy[d][t]` indexed by device ID and time slot. Only create for plugged-in chargers.
- [x] 3.2 Add per-device energy coupling constraint: `ev_energy[d][t] == ev_charge[d][t] * charger.max_power_kw * h` for each device.
- [x] 3.3 Add per-device deadline constraint: `ev_energy[d][t] == 0` for slots past each charger's deadline.
- [x] 3.4 Add per-device incentive bucket variables and constraints: `ev_bucket_charged[d][i]` with per-device capacity bounds and total energy linking.
- [x] 3.5 Update energy balance constraint to sum all devices: `sum(ev_energy[d][t] for d in chargers)` replaces single `ev_energy[t]`.
- [x] 3.6 Add `any_ev_charging[t]` auxiliary binary and linking constraints. Update discharge blocking: `discharge[t] <= (1 - any_ev_charging[t]) * M`.
- [x] 3.7 Update grid-only charging constraint per device: `ev_energy[d][t] <= grid_import[t] + pv + epsilon` (shared grid import across devices).
- [x] 3.8 Update objective function: sum incentive bucket values across all devices.
- [x] 3.9 Update result extraction: build `ev_charger_results` dict from per-device `ev_energy[d][t]` values.
- [x] 3.10 Write solver tests: single charger equivalence, two chargers with different deadlines, two chargers exceeding grid limit get staggered, unplugged charger gets no variables, no chargers equals no EV constraints.

## 4. Pipeline & Initial State

- [x] 4.1 Update `ha_client.py` `get_initial_state()` to fetch SoC and plug state for ALL enabled chargers, returning per-device list instead of scalar values.
- [x] 4.2 Update `pipeline.py` to call `calculate_ev_deadline()` per charger using each charger's `departure_time`.
- [x] 4.3 Update `pipeline.py` to build `EVChargerInput` list from per-device config + per-device HA state + per-device deadline.
- [x] 4.4 Update replan trigger to pass charger ID, and `get_initial_state()` to accept per-device plug state override.
- [x] 4.5 Write pipeline tests: per-device deadline calculation, per-device state fetching, plug override for specific charger.

## 5. Schedule Output

- [x] 5.1 Update `planner/output/formatter.py` to include `ev_chargers` dict in each schedule slot alongside aggregate `ev_charging_kw`.
- [x] 5.2 Update `planner/output/schedule.py` (if applicable) to serialize per-device EV data.
- [x] 5.3 Write tests: verify schedule output contains per-device breakdown and correct aggregate.

## 6. Executor

- [x] 6.1 Create `EVChargerDeviceConfig` dataclass in `executor/config.py`. Replace `EVChargerConfig` with `ev_chargers: list[EVChargerDeviceConfig]` in `ExecutorConfig`.
- [x] 6.2 Update `load_executor_config()` to build per-device config list from `ev_chargers[]` entries.
- [x] 6.3 Create `EVChargerState` dataclass in `executor/engine.py`. Replace scalar EV state vars with `_ev_charger_states: dict[str, EVChargerState]`.
- [x] 6.4 Add `ev_charger_plans: dict[str, float]` to `SlotPlan` in `executor/override.py`. Update slot loading to parse per-device EV data from schedule.
- [x] 6.5 Refactor `_control_ev_charger()` into a loop over configured chargers, using per-device plan and per-device state. Each charger gets independent switch control and safety timeout.
- [x] 6.6 Update source isolation logic to check ANY charger (scheduled or actual power detected across all chargers).
- [x] 6.7 Update EV power detection to sum power across all chargers via LoadDisaggregator.
- [x] 6.8 Update execution record to include `ev_charger_plans` dict and aggregate `ev_charging_kw`.
- [x] 6.9 Update `get_status()` to include per-device EV plan in `current_slot_plan`.
- [x] 6.10 Write executor tests: per-device switch control, independent safety timeouts, source isolation across chargers, old-format schedule fallback.

## 7. WebSocket & Replan

- [x] 7.1 Update `ha_socket.py` to maintain plug sensor → charger ID mapping for ALL enabled chargers.
- [x] 7.2 Update `_trigger_ev_replan()` to look up charger ID from plug sensor, check that charger's replan settings.
- [x] 7.3 Pass triggering charger ID through replan trigger chain so `get_initial_state()` can override that specific charger's plug state.
- [x] 7.4 Write tests: per-device plug sensor mapping, charger-specific replan settings, charger ID propagation.

## 8. Energy Recording

- [x] 8.1 Update `backend/recorder.py` to record per-device EV energy (fetch history per charger, store as JSON field).
- [x] 8.2 Maintain aggregate `ev_charging_kwh` as sum across chargers for backward compatibility.
- [x] 8.3 Write tests: per-device recording, aggregate still correct, fallback to snapshot per device.

## 9. Frontend Settings

- [x] 9.1 Add `departure_time`, `switch_entity`, `replan_on_plugin`, `replan_on_unplug` fields to the EV charger entity card in `EntityArrayEditor`.
- [x] 9.2 Remove the orphan "Departure Time" and "Control" sections from `EVTab.tsx` / `types.ts`.
- [x] 9.3 Verify settings save/load round-trip with the new per-device fields.
- [x] 9.4 Remove `nominal_power_kw` field from the EV Charger entity card in `EntityArrayEditor` to avoid UX confusion with `max_power_kw`.
- [x] 9.5 Polish EV Settings UI: Remove redundant power sensor hint text, update replan toggles to use the `Switch` component, and improve grid layout alignment.

## 10. Integration & Validation

- [x] 10.1 Run full test suite and fix any regressions from KeplerConfig changes, SlotPlan changes, or executor config changes.
- [x] 10.3 Update health checks in `backend/health.py` to detect deprecated `executor.ev_charger` and suggest migration.
