## Context

The Kepler MILP solver currently has no concept of an "export SoC floor." It will happily schedule grid exports that drive projected SoC well below the user's comfort level, relying on the executor's `LOW_SOC_EXPORT_PREVENTION` override (priority 8.5) to catch this at runtime. This creates schedule desync: the downstream slots are optimized assuming the export happened, but the override blocks it.

The planner replans every 30 minutes (configurable via `planner.schedule.every_minutes`). At this cadence, SoC drift between projected and actual is typically <1-2%, making a planner-internal constraint reliable enough to replace the reactive override entirely.

Current constraint landscape in Kepler:
- `min_soc_kwh`: soft lower bound with 1000 SEK/kWh penalty (safety floor)
- `max_soc_kwh`: soft upper bound with 1000 SEK/kWh penalty
- `enable_export`: hard binary toggle (export on/off globally)
- `max_export_power_kw`: hard grid fuse limit
- No SoC-gated export constraint exists

## Goals / Non-Goals

**Goals:**
- Prevent Kepler from scheduling exports that would drop projected SoC below a configurable floor
- Make this a soft constraint (high penalty) so the solver can still export in extreme cases (e.g., massive price spike) rather than going infeasible
- Remove the executor `LOW_SOC_EXPORT_PREVENTION` override entirely — the planner handles this
- Keep `enable_export` toggle unchanged (global on/off for exports)

**Non-Goals:**
- This does NOT constrain battery discharge for self-consumption — only grid export
- This does NOT change `min_soc` behavior or the executor's other overrides (excess PV heating, slot failure fallback, manual override)
- This does NOT add new config surface for penalty weight — the penalty is hardcoded at the same level as `MIN_SOC_PENALTY`

## Decisions

### Decision 1: Big-M formulation with binary `is_exporting[t]`

The constraint requires: "if `grid_export[t] > 0`, then `soc[t] >= export_floor_kwh`." This is naturally modeled with a binary indicator variable per slot.

**Formulation:**
```
Variables:
  is_exporting[t] ∈ {0, 1}    for t in 0..T-1
  export_floor_violation[t] ≥ 0

Constraints:
  grid_export[t] ≤ M * is_exporting[t]          (M = max_export or max_discharge)
  soc[t] ≥ export_floor_kwh * is_exporting[t]
           + min_soc_kwh * (1 - is_exporting[t])
           - export_floor_violation[t]

Objective penalty:
  EXPORT_FLOOR_PENALTY * Σ export_floor_violation[t]
```

When `is_exporting[t] = 0`: export is forced to 0, SoC floor is `min_soc_kwh` (unchanged).
When `is_exporting[t] = 1`: export is allowed, SoC floor is `export_floor_kwh` (tighter).

**Alternative considered:** Conditional constraint without binary (using `grid_export[t] / M` as a continuous proxy). Rejected because it introduces nonlinearity. The binary approach is standard MILP and adds only T binaries (~96-192), trivial for GLPK/CBC at 30-second timeout.

### Decision 2: Soft constraint with high penalty

Using a slack variable `export_floor_violation[t]` penalized at `EXPORT_FLOOR_PENALTY` (1000 SEK/kWh, same as `MIN_SOC_PENALTY`). This means:
- Kepler will strongly avoid exporting below the floor
- If the math still favors it (e.g., price is 10 SEK/kWh and export gains more than the penalty), the solver can violate
- The problem never goes infeasible due to this constraint

**Alternative considered:** Hard constraint (no violation allowed). Rejected because it could make the LP infeasible in edge cases where the energy balance forces export.

### Decision 3: Only active when `enable_export` is True and `export_floor_soc_percent` is set

The constraint is gated on both:
- `config.enable_export == True` (if exports are disabled, there's nothing to gate)
- `config.export_floor_soc_percent is not None` (if not configured, skip entirely)

### Decision 4: Config relocation

`low_soc_export_floor` moves from `executor.override` to `export.export_floor_soc_percent`. The executor config section no longer needs an override subsection for this. Config migration handles the move transparently.

## Risks / Trade-offs

**[Binary variable overhead]** → T additional binary variables per solve. At T=192 (48h * 4 slots/h), GLPK handles this in <1 second. Negligible.

**[Config migration]** → Users with existing `executor.override.low_soc_export_floor` need the value moved. Mitigation: config migration script reads the old key and writes to the new location.

**[Forecast drift]** → The constraint uses projected SoC, not real-time. With 30-min replanning, drift is <1-2%. This is acceptable — the user confirmed this is a preference, not a safety constraint.
