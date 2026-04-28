## 1. Configuration

- [x] 1.1 Add `executor.excess_pv` section to `config.default.yaml` with sink selector and custom entity fields
- [x] 1.2 Add `ExcessPVConfig` dataclass to `executor/config.py` with sink type enum (`water_heater_boost` | `custom_entity` | `disabled`) and custom entity fields
- [x] 1.3 Load excess PV config in `load_executor_config()` and pass to engine
- [x] 1.4 Add `boost_reward_sek_per_kwh` to config, solver, and settings UI
- [x] 1.5 Add `soc_threshold_percent` (default 95) to `config.default.yaml`, `ExcessPVConfig`, `KeplerConfig`, adapter, and settings UI
- [x] 1.6 Add `power_kw` (default 1.0) to `ExcessPVCustomEntityConfig`, `KeplerConfig`, adapter, and settings UI

## 2. Remove EXCESS_PV_HEATING Override

- [x] 2.1 Remove `EXCESS_PV_HEATING` from `OverrideType` enum in `executor/override.py`
- [x] 2.2 Remove `EXCESS_PV_HEATING` evaluation block from `OverrideEvaluator.evaluate()` (priority 5 block)
- [x] 2.3 Remove `excess_pv_threshold_kw` parameter from `OverrideEvaluator.__init__()` and `evaluate_overrides()`
- [x] 2.4 Remove `excess_pv_threshold_kw` from `executor.excute.override` config defaults in `engine.py`
- [x] 2.5 Add `override.excess_pv_threshold_kw` to `config_migration.py` removal list to strip it from existing user configs

## 3. Kepler Planner: Excess PV Detection (Coarse Filter)

- [x] 3.1 Pre-calculate per-slot excess PV flags from raw forecasts before MILP solve: `excess[t] = max(0, pv_forecast[t] - load_forecast[t] - min_water_heat_forecast[t] - min_ev_forecast[t]) > 0`
- [x] 3.2 Pass excess slot flags into Kepler MILP as fixed binary parameters (not derived from solve output)

## 4. Kepler Planner: SoC Threshold Gate (Battery-First Priority)

- [x] 4.1 Add `soc_above_threshold[t]` binary variables in kepler.py when any sink is active (boost or custom entity)
- [x] 4.2 Add big-M constraint linking SoC to threshold: `soc[t] >= threshold_kWh - M * (1 - soc_above_threshold[t])` where threshold = `soc_threshold_percent`% of capacity (configurable, default 95)
- [x] 4.3 Constrain water heater boost variables to `soc_above_threshold[t]` (in addition to existing excess PV flag constraint)
- [x] 4.4 Constrain custom entity variables to `soc_above_threshold[t]` (in addition to excess PV flag constraint)

## 5. Kepler Planner: Water Heater Boost

- [x] 5.1 Create per-device boost binary decision variables for all water heaters when sink is `water_heater_boost`
- [x] 5.2 Constrain boost variables to pre-calculated excess PV slot flags (coarse filter)
- [x] 5.3 Add boost reward (`BOOST_REWARD_SEK * boost_var * heater_kw * h`) to objective function — negative cost incentivizes boost over export
- [x] 5.4 Add `water_heating_boost` field to schedule output format (per-device boolean in each slot)
- [x] 5.5 Update schedule output formatter to include boost flags

## 6. Kepler Planner: Custom Entity Solver Variable

- [x] 6.1 Create `custom_entity_active[t]` binary solver variable when sink is `custom_entity`
- [x] 6.2 Constrain custom entity to pre-calculated excess PV flags (coarse filter)
- [x] 6.3 Add reward to objective for custom entity: `BOOST_REWARD_SEK * custom_entity_active[t] * power_kw * h`
- [x] 6.4 Use solver variable value (not pre-calculated flag) in schedule output for `custom_entity_active`
- [x] 6.5 Add custom entity power consumption to energy balance (demand side)

## 7. Executor: Water Heater Boost Temperature

- [x] 7.1 Update `_determine_water_temps()` in controller to return `temp_boost` when schedule has `water_heating_boost` for a device
- [x] 7.2 Ensure boost temperature takes precedence over normal temperature when both apply

## 8. Executor: Custom Entity Control

- [x] 8.1 Add `set_custom_entity()` method to ActionDispatcher that toggles a HA entity to a specified value
- [x] 8.2 In engine `_tick()`, when excess PV sink is `custom_entity`, read schedule flags and toggle entity on/off per slot
- [x] 8.3 Skip custom entity control when sink is `disabled`
- [x] 8.4 In `SLOT_FAILURE_FALLBACK` handler, set custom entity to `off_value` when sink is `custom_entity`

## 9. Settings UI: Excess PV Sink Configuration

- [x] 9.1 Add sink selector (Water Heater Boost / Custom Entity / Disabled) to Advanced tab, Excess PV Dispatch section
- [x] 9.2 Show entity ID, on-value, off-value fields when "Custom Entity" selected
- [x] 9.3 Hide water heater boost option when `has_water_heater=false`
- [x] 9.4 Add config field bindings to save/load from `config.yaml`
- [x] 9.5 Add `boost_reward_sek_per_kwh` field to settings when sink is `water_heater_boost` or `custom_entity`
- [x] 9.6 Add SEK/kWh unit label to the boost reward field
- [x] 9.7 Add `soc_threshold_percent` field (%) to settings when sink is active (same row as reward)
- [x] 9.8 Add `power_kw` field (kW) to custom entity settings when sink is `custom_entity`

## 10. Chart: Boost Bar Visualization

- [x] 10.1 Add separate bar dataset for water heating boost (teal `#00E6B4`, `rgba(0, 230, 180, 0.40)`) — separate dataset required because glow plugin reads borderColor as static string
- [x] 10.2 Apply sharp glow to boost dataset (`glowBlur: 20`, `glowOpacity: 1.0`) and custom entity dataset
- [x] 10.3 Disable glow on all other bar datasets (`glow: false`)
- [x] 10.4 Move PV forecast overlay behind all bars (`order: 20`)
- [x] 10.5 Both boost and normal water heating datasets toggle together via "Water Heating" overlay (ds[6] and ds[7])
- [x] 10.6 Update dataset overlay index mapping after adding boost dataset (indices shifted by 1)

## 11. Tests & Cleanup

- [x] 11.1 Add tests for spec requirements (planner dispatch, executor boost temp, custom entity)
- [x] 11.2 Update existing override tests to verify EXCESS_PV_HEATING is removed
- [x] 11.3 Add tests for SoC threshold constraint (sink does not activate below threshold, activates above, configurable)
- [x] 11.4 Add tests for custom entity solver variable (reward applies, not pre-calculated flag, power_kw sizes reward)
- [x] 11.5 Run full lint and verify all checks pass
