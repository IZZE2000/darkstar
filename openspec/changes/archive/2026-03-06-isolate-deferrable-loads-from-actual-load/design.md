## Context

The recorder captures energy data in 15-minute slots for ML training. It has two calculation paths:

1. **Power snapshot path** (legacy): `energy_kwh = power_kw * 0.25`
2. **Cumulative sensor path** (Mar 2026): `energy_kwh = delta between meter readings`

The LoadDisaggregator correctly isolates controllable loads (EV, water) from base load **for power snapshots only**. When cumulative sensors were added, the energy calculation bypassed this isolation.

**Current flow (buggy):**
```
total_load_kw (power) ──┬──> LoadDisaggregator ──> base_load_kw (for power snapshot fallback)
                        │
total_load_consumption ─┴──> delta calculation ──> load_kwh (STORED - includes EV/water!)
```

**Fixed flow:**
```
total_load_consumption ───> delta calculation ──> total_load_kwh
                                                    │
ev_charging_kwh (snapshot) ───────────────────────┼──> subtract
water_kwh (snapshot) ─────────────────────────────┘
                                                    │
                                                    └──> base_load_kwh (STORED)
```

## Goals / Non-Goals

**Goals:**
- Subtract EV and water energy from total load before storing `load_kwh`
- Clamp result to minimum 0 (handle sensor drift)
- Maintain compatibility with existing cumulative sensor infrastructure

**Non-Goals:**
- Adding cumulative sensors for EV/water (future enhancement)
- Backfilling historical data
- Changes to LoadDisaggregator

## Decisions

### D1: Apply isolation to energy, not just power

**Decision**: Calculate `base_load_kwh = total_load_kwh - ev_charging_kwh - water_kwh`

**Rationale**:
- LoadDisaggregator already does this for power (kW)
- EV/water are typically binary loads with predictable energy per 15-min slot
- Snapshot approximation for EV/water is acceptable (small error relative to total load)

**Alternative considered**: Add cumulative sensors for EV/water
- Rejected: Requires HA configuration changes, more complexity, marginal accuracy gain

### D2: Clamp negative base load to 0

**Decision**: `base_load_kwh = max(0.0, total_load_kwh - ev_charging_kwh - water_kwh)`

**Rationale**:
- Matches existing behavior in `LoadDisaggregator.calculate_base_load()`
- Prevents sensor drift from corrupting data
- Logs warning when clamping occurs (like power path)

### D3: No database migration

**Decision**: No changes to `SlotObservation` model

**Rationale**:
- `load_kwh` will now contain base load (semantic change)
- `ev_charging_kwh` and `water_kwh` already stored separately
- Historical data remains contaminated but will be overwritten naturally
- If debugging needed, `total = load + ev + water` can reconstruct

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Negative base load due to sensor timing mismatch | Clamp to 0, log warning with values |
| Historical data inconsistent with new data | Acceptable - ML will retrain on clean data |
| EV/water snapshot error accumulates | Small relative to total load; future cumulative sensors will improve |
