## Why

The current excess PV system uses a reactive executor override that sets the water heater to max temperature when real-time PV surplus is detected. This is fundamentally flawed: the override is buggy (does not work with multi-device water heater configs), only supports water heaters, and sends notification spam on each cloud-pass. More importantly, a 30-minute-ahead planner should proactively schedule excess PV utilization rather than react to it.

## What Changes

- **Remove** `EXCESS_PV_HEATING` override from the executor — excess PV is now handled by the planner
- Kepler scheduler models water heater **boost** (85°C) as additional per-slot binary demand, dispatched only into slots with forecast excess PV. No daily energy budget — the solver's energy balance handles economics via a configurable boost reward, and the executor's thermostat handles physics.
- A configurable `boost_reward_sek_per_kwh` incentivizes the solver to prefer boost over export when the reward exceeds the export price
- Users can configure a **custom HA entity** as an excess PV sink (e.g., pool pump, dehumidifier), toggled on/off during excess PV slots
- Water heater execution supports boost temperature from the schedule, not just normal/off
- Chart shows boost water bars as teal with sharp glow (separate dataset); custom entity bars in amber with sharp glow; all other bars have no glow; PV overlay renders behind bars
- Settings UI in Hardware Features section: toggle between "Water Heater Boost", "Custom Entity", or "Disabled" as the excess PV sink
  - If `has_water_heater=false`, only custom entity or disabled is available

## Capabilities

### New Capabilities

- `excess-pv-planner-dispatch`: Kepler models forecast excess PV and dispatches it to water heater boost and/or custom HA entity sinks in the schedule
- `excess-pv-settings`: Settings UI for configuring the excess PV sink (water heater boost, custom HA entity, or disabled)

### Modified Capabilities

- `water-heater-override-condition`: Remove `EXCESS_PV_HEATING` override — excess PV is no longer a reactive executor concern
- `water-heater-execution`: Support boost temperature value from schedule alongside normal/off temperatures
- `chart-planned-actual-display`: Water heating boost bars use separate teal dataset with sharp glow; custom entity sink bars use amber with sharp glow; all other bars have no glow; PV overlay renders behind bars

## Impact

- `executor/override.py` — Remove `EXCESS_PV_HEATING` override type and evaluation logic
- `executor/engine.py` — Remove excess PV override handling path; water temp dispatch supports boost
- `executor/controller.py` — `_apply_override` no longer handles `EXCESS_PV_HEATING`; `_determine_water_temps` supports boost
- `planner/solver/kepler.py` — Add per-slot boost binary variables for all water heaters when sink is `water_heater_boost`, constrained to excess PV slots with boost reward in objective
- `planner/pipeline.py` — Feed boost demand into Kepler; detect excess PV slots
- `planner/output/formatter.py` — Include water heater boost flag in schedule output
- `frontend/src/components/ChartCard.tsx` — Separate boost dataset (teal + sharp glow); custom entity dataset (amber + sharp glow); no glow on other bars; PV at order:20 behind bars
- `frontend/src/pages/settings/` — Excess PV sink configuration in Hardware Features section; boost reward config (TODO)
- `config.default.yaml` — New `excess_pv` section with sink, boost_reward, and custom entity configuration
