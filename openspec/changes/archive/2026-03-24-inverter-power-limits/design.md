## Context

The planner's Kepler solver models energy flow with grid import/export limits from the grid fuse (`system.grid.max_power_kw`). Hybrid inverters have two additional physical limits that are not modeled:

1. **AC output limit** — max total AC power the inverter can produce (PV + battery discharge). Typically 8–12kW.
2. **DC input limit** — max DC power from PV strings entering the inverter. When PV array capacity exceeds this, the inverter clips the excess.

Currently three config keys exist for inverter limits — none are wired to the planner:
- `system.inverter.max_power_kw` — orphan, never read by any code
- `executor.controller.inverter_ac_limit_kw` — parsed into config dataclass but never used
- `executor.inverter.grid_max_export_power` — HA entity for runtime export control (different purpose, stays)

## Goals / Non-Goals

**Goals:**
- Model inverter AC output and DC input limits in the Kepler solver
- Clean config: two well-named keys replacing two orphans
- Expose in Settings UI with tooltips
- Warn users when keys are missing (like other essential config)

**Non-Goals:**
- AC-coupled battery systems (separate inverter for battery) — all current users have hybrid inverters
- Variable inverter efficiency curves (fixed efficiency is sufficient)
- Changing the `grid_max_export_power` executor entity (runtime HA control, separate concern)
- Modeling DC-to-DC battery charging from PV (the solver works in kWh energy, efficiency factors handle losses)

## Decisions

### D1: Config key placement — under `system.inverter`

**Decision:** Add `system.inverter.max_ac_power_kw` and `system.inverter.max_dc_input_kw`. Remove `system.inverter.max_power_kw`.

**Rationale:** `system.inverter` already exists in config (orphaned). These are system-level physical parameters, not planner tuning or executor settings. Keeps it next to `system.grid` which holds the grid fuse limit.

**Alternative considered:** Put under `planner.kepler` — rejected because these are physical hardware specs, not solver tuning knobs.

### D2: PV clipping via pre-processing (not solver variable)

**Decision:** Clip `pv_kwh` input to `min(pv_forecast, max_dc_input_kw * slot_hours)` in the adapter before passing to the solver. PV remains a fixed input, not a decision variable.

**Rationale:** The solver never benefits from choosing to use *less* PV than available — you always want all available PV. Making PV a variable adds complexity to the MILP for no optimization benefit. Pre-clipping is simpler and has zero solver performance impact.

**Alternative considered:** Introduce `pv_used[t]` as a solver variable bounded by DC limit — rejected as over-engineering. The solver can't do anything useful with the choice to curtail PV.

### D3: AC output constraint in solver

**Decision:** Add a single constraint: `discharge[t] + pv_clipped[t] <= max_inverter_ac_kw * h` where `pv_clipped[t]` is the pre-clipped PV value from the slot input (a constant per slot, not a variable).

Since PV is already a fixed input in the energy balance, this constraint effectively limits how much battery discharge can stack on top of solar. When PV is high, less room for battery discharge. When PV is zero (nighttime), full AC capacity is available for battery discharge.

**Rationale:** This is the physical reality — the inverter has a single AC output bus shared by PV conversion and battery discharge. The constraint is simple, linear, and doesn't add variables.

### D4: Remove orphan config keys

**Decision:** Remove `system.inverter.max_power_kw` from `config.default.yaml` and `executor.controller.inverter_ac_limit_kw` from both `config.default.yaml` and `executor/config.py`.

**Rationale:** Neither is used. Keeping them creates confusion. Config migration maps old `system.inverter.max_power_kw` → `system.inverter.max_ac_power_kw` for users who had set it.

### D5: No fallback defaults — warn when missing

**Decision:** When `max_ac_power_kw` or `max_dc_input_kw` is not configured, the planner logs a warning and skips the constraint (same behavior as today). Config validation endpoint returns a warning.

**Rationale:** User must set correct values for their hardware. Wrong defaults are worse than no constraint — they'd silently produce wrong schedules.

## Risks / Trade-offs

- **[Risk] Users upgrade without setting new keys** → Mitigation: Planner behavior is unchanged when keys are missing (constraints are skipped). Config validation warns prominently. No breakage.
- **[Risk] Old `max_power_kw` values lost on upgrade** → Mitigation: Config migration maps old key to `max_ac_power_kw`.
- **[Trade-off] Pre-clipping PV loses solver flexibility** → Acceptable: there's no scenario where the solver benefits from using less PV than physically available.
