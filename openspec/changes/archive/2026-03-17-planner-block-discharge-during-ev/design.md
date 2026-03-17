## Context

The Kepler MILP solver (`planner/solver/kepler.py`) has an energy balance constraint and a "grid-only" constraint for EV charging:

```python
# Energy balance (line 224-231)
load + water_load + ev_energy + charge + grid_export + curtailment
  == pv + discharge + grid_import + load_shedding

# Grid-only constraint (line 239-241)
ev_energy[t] <= grid_import[t] + s.pv_kwh + 1e-6
```

The grid-only constraint prevents EV energy from *exceeding* grid+solar, but the solver can still schedule `discharge > 0` alongside `ev_energy > 0` in the same slot (battery serves house load, grid serves EV). The executor then zeros discharge via source isolation, making the plan inaccurate.

EV charging uses a binary variable `ev_charge[t]` (0 or 1) with `ev_energy[t] = ev_charge[t] * max_power * hours`. This binary is ideal for a Big-M mutual exclusion constraint.

## Goals / Non-Goals

**Goals:**
- Make the planner's EV/discharge constraint match the executor's source isolation behavior
- Ensure the solver never plans discharge and EV charging in the same slot
- Improve plan accuracy (planned cost matches actual cost)

**Non-Goals:**
- Changing executor source isolation logic
- Allowing partial discharge during EV charging (physically impossible on shared AC bus)
- Changing any other planner constraints or objective function terms

## Decisions

### Decision 1: Big-M constraint on discharge when EV is charging

**Choice:** Add `discharge[t] <= (1 - ev_charge[t]) * M` where `M = max_discharge_kw * slot_hours`

**Rationale:** `ev_charge[t]` is already a binary variable in the model. When `ev_charge[t] = 1`, discharge is forced to 0. When `ev_charge[t] = 0`, the constraint is non-binding (discharge bounded by its own upper bound). This is a standard Big-M formulation, minimal solver impact.

**Alternatives considered:**
- *Indicator constraints*: PuLP doesn't natively support indicator constraints, would need CBC-specific extensions
- *Two separate models (EV on/off)*: Combinatorial explosion with multi-slot horizons, impractical
- *SOS constraints*: Overkill for a simple binary mutual exclusion

### Decision 2: Place constraint inside existing `if ev_enabled` block

**Choice:** Add the new constraint right after the existing grid-only constraint (line 241), inside the same `if ev_enabled` guard.

**Rationale:** Keeps all EV-related constraints together. No constraint added when EV is not enabled (no solver overhead for non-EV users).

## Risks / Trade-offs

- **[Solver feasibility]** In rare edge cases where the house load is high and the only way to avoid load shedding is battery discharge, but EV is also scheduled → the solver must choose between EV charging and battery discharge. The solver will naturally prefer the lower-cost option since load shedding has a 10,000 SEK/kWh penalty. → *Acceptable: this matches physical reality.*
- **[Big-M tightness]** Using `max_discharge_kw * h` as M is tight (equals the actual upper bound on discharge), which is optimal for LP relaxation quality. → *No risk, this is the standard approach.*
