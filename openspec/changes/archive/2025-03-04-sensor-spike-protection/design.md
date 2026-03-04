## Context

Home Assistant sensors can report spurious values due to communication glitches, sensor malfunctions, or counter resets. Currently, values flow unchecked from HA → Recorder → `slot_observations` DB. The only protection is a 50 kWh threshold in `learning/engine.py` that only applies during backfill, not live recording. Analytical pipelines (Analyst, Reflex) read raw rows with no spike guard.

## Goals / Non-Goals

**Goals:**
- Derive a physically-reasonable max energy threshold from user's grid fuse rating
- Validate all energy values before database storage (recorder)
- Harden all analytical read paths to filter spike rows at query time (no DB migration needed)
- Fix the backfill threshold to use the same derived value across both ETL functions

**Non-Goals:**
- SoC validation (already bounded 0-100% by nature)
- Real-time alerting on bad values (out of scope)
- Predictive anomaly detection (out of scope)
- Database migration / cleaning existing rows (pipelines handle this at read time)

## Decisions

### D1: Threshold derived from grid.max_power_kw

**Decision**: Calculate `max_kwh_per_slot = grid.max_power_kw × 0.25h × 2.0`

**Rationale**: The grid connection is the physical bottleneck. No sensor can report more than what the grid + PV can deliver. PV export also goes through the same grid connection. A 2.0x safety factor accounts for:
- Simultaneous import + PV production
- Short transients
- Measurement noise

**Alternatives considered**:
- Sum of all device max values: Too generous, complex
- House fuse (A) field: Requires new config field
- Per-sensor thresholds: Overly complex for marginal gain

### D2: Spike values set to 0.0 at write time

**Decision**: Values exceeding threshold are set to 0.0 by `recorder.py`, not clipped or interpolated.

**Rationale**: 0.0 signals "unknown/unreliable" data rather than pretending we know what it was. The learning/aggregation pipelines can handle gaps. Existing spiked rows already in the DB are left as-is and filtered at read time (see D3).

**Alternatives considered**:
- Clip to max: Pretends we know the value (misleading)
- Interpolate: Complex, assumes continuity
- Previous value: Same issues as interpolation

### D3: No database migration — pipelines filter at read time

**Decision**: Existing spiked rows in `slot_observations` are not modified. Instead, all analytical read paths apply a `WHERE energy_col <= max_kwh_per_slot` filter before returning data to callers.

**Rationale**: This is safer and simpler than a one-way destructive migration:
- No risk of incorrectly zeroing valid data
- Fully reversible — the raw DB is untouched
- The DB becomes a faithful historical record; analytical pipelines determine what is "valid"
- New writes are already protected by `recorder.py`, so the problem is self-healing going forward

**Paths hardened**:
- `Analyst._fetch_observations` — filters before bias / auto-tune calculation
- `LearningStore.get_forecast_vs_actual` — filters before Reflex accuracy analysis
- `LearningStore.calculate_metrics` — filters before MAE calculations

**Paths not hardened** (justified):
- `LearningStore.get_observations_range` — feeds the 48h dashboard chart only; old spikes are outside the window
- `LearningStore.get_history_range` — used by price backfiller; does not consume energy values for computation

**Alternatives considered**:
- Alembic migration zeroing spikes: One-way, destructive, requires config to be present at migration time — too risky for a first deploy
- Per-query fallback value: More complex than a simple filter

### D4: Utility function in backend/validation.py

**Decision**: Create `backend/validation.py` with `get_max_energy_per_slot(config)` function.

**Rationale**: Single source of truth used by:
- `recorder.py` (live validation at write time)
- `learning/engine.py` — both `etl_cumulative_to_slots` and `etl_power_to_slots` (backfill threshold)
- `learning/analyst.py` and `learning/store.py` (read-time filtering)

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Threshold too low for unusual setups | 2.0x safety factor provides headroom; user can increase `grid.max_power_kw` |
| Legacy spike rows remain in DB indefinitely | Pipelines filter them; new writes are clean; old data self-ages out |
| False positives on legitimate high values | Log warnings at write time; user can investigate via quality_flags |
| `get_max_energy_per_slot` called with missing config key | Function must return a safe default (raise or return a conservative value with a warning) |
