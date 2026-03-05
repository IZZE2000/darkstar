## Context

ChartCard component displays energy data (charge, discharge, PV, load, water, EV, export, SOC) across a 48-hour window. The current implementation incorrectly shows actual values in both the main chart elements and overlay lines for historical slots, making planned vs actual comparison impossible.

**Current Behavior** (`ChartCard.tsx:1382-1392`):
```javascript
charge.push(
    isExec && slot.actual_charge_kw != null
        ? slot.actual_charge_kw  // Shows ACTUAL for historical
        : (slot.battery_charge_kw ?? slot.charge_kw ?? null),
)
actualCharge.push(slot.actual_charge_kw ?? null)  // Also ACTUAL
```

**Data Sources**:
- `battery_charge_kw` = planned/forecasted value (from `slot_plans` table via `planned_map`)
- `actual_charge_kw` = actual observed value (from `slot_observations` table via `exec_map`)

The backend (`schedule.py:389-406`) correctly provides both values in the API response for all slots.

## Goals / Non-Goals

**Goals:**
- Main chart bars/lines display planned/forecasted values for ALL slots (historical + future)
- Dotted overlay lines display actual values for historical slots only
- Apply consistent pattern to all metrics: charge, discharge, PV, load, water, EV, export, SOC
- Enable visual comparison of planned vs actual performance

**Non-Goals:**
- No backend changes
- No API changes
- No database changes
- No new chart features (just fix existing display logic)

## Decisions

### D1: Separate Planned and Actual Data Arrays

**Decision**: Maintain separate arrays for planned values (main display) and actual values (overlay), rather than conditionally switching values.

**Rationale**:
- Clearer separation of concerns
- Planned values flow through existing `charge`, `discharge`, `pv`, `load` arrays
- Actual values already flow through `actualCharge`, `actualDischarge`, `actualPv`, `actualLoad` arrays
- No new arrays needed - just fix the conditional logic

### D2: Always Use Planned Values for Main Arrays

**Decision**: Main display arrays (`charge`, `discharge`, `pv`, `load`, `water`, `evCharging`, `exp`) should use planned/forecasted values unconditionally.

**Pattern**:
```javascript
// BEFORE (wrong)
charge.push(
    isExec && slot.actual_charge_kw != null
        ? slot.actual_charge_kw
        : (slot.battery_charge_kw ?? slot.charge_kw ?? null),
)

// AFTER (correct)
charge.push(slot.battery_charge_kw ?? slot.charge_kw ?? null)
```

**Rationale**:
- Solid lines/bars represent the PLAN/FORECAST
- Dotted overlay lines represent ACTUAL
- This matches user mental model: "What did I plan?" vs "What actually happened?"

### D3: Keep Actual Arrays Unchanged

**Decision**: The `actual*` arrays (`actualCharge`, `actualDischarge`, `actualPv`, etc.) remain unchanged - they already correctly show actual values.

**Rationale**: These are already correct and used for overlay lines.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Historical slots may have no planned value if planner never ran | Graceful null handling - chart shows nothing for that slot |
| Users accustomed to seeing actual in main bars | User expectation is that SOLID = plan, DOTTED = actual (confirmed by user) |
| PV/Load forecasts may differ significantly from actual | This is the point - to show the forecast error visually |

## Migration Plan

1. Update `ChartCard.tsx` data population logic
2. Verify chart displays correctly with existing data
3. No data migration needed - data is already correct in backend

**Rollback**: Revert the conditional logic changes in `ChartCard.tsx`
