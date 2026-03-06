## Context

The sensor-spike-protection change (2025-03-04) implemented spike filtering for backend analytical paths using a config-derived threshold (`grid.max_power_kw × 0.25h × 2.0`). However, the ML training and evaluation code paths were not included in the hardened paths list, creating a gap where corrupted data flows into model training.

The spike filtering pattern is already established:
1. `backend/validation.py` provides `get_max_energy_per_slot(config)` for threshold calculation
2. Analytical read paths add `WHERE energy_col <= max_kwh` to SQL queries
3. The threshold is derived from grid connection capacity (physical bottleneck)

The gap: ML code directly queries `slot_observations` without applying this filter, causing models to learn from impossible values.

## Goals / Non-Goals

**Goals:**
- Apply the same spike filtering pattern to ML training, correction, and evaluation code
- Maintain consistency with the existing backend analytical path implementation
- Ensure no code duplication - reuse `backend/validation.py` utility

**Non-Goals:**
- Changing the spike detection logic or threshold calculation
- Database migration or data cleanup (spike rows remain in DB, filtered at read time)
- Retrospective retraining of existing models (users will retrain naturally)

## Decisions

### D1: Reuse existing validation utility

**Decision**: Import `get_max_energy_per_slot()` from `backend.validation` in all three ML files.

**Rationale**: Single source of truth for threshold calculation. Avoids duplication. The utility already handles config validation and safety factor application.

**Alternatives considered**:
- Duplicate the calculation logic: Violates DRY, creates maintenance burden
- Hardcode a default threshold: Loses config-derived accuracy, inconsistent with backend

### D2: Filter at query time (WHERE clause)

**Decision**: Add `AND pv_kwh <= ? AND load_kwh <= ?` to SQL queries in all three ML functions.

**Rationale**: Consistent with backend approach. Efficient (database filters before returning rows). Clean - doesn't require post-processing DataFrames.

**Alternatives considered**:
- Load all data, filter in Python: Less efficient, more code, inconsistent pattern
- Create a shared ML query helper: Over-engineering for three simple queries

### D3: Apply to both pv_kwh and load_kwh

**Decision**: Filter both energy columns in all queries.

**Rationale**: Both can have spike values from sensor glitches. Consistency. The validation utility already handles both fields.

**Alternatives considered**:
- Filter only pv_kwh: Load spikes also corrupt training, seen in the wild
- Filter per-function: Inconsistent, error-prone

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Reduced training data if threshold is too aggressive | 2.0x safety factor provides headroom; threshold is conservative (grid.max_power_kw × 0.25 × 2.0) |
| Existing trained models remain corrupted | Users will retrain naturally over time; new models will be clean |
| Config missing grid.max_power_kw | `get_max_energy_per_slot()` raises ValueError with clear message; callers propagate error |
