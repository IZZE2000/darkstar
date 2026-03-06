## Context

The override system in `executor/override.py` evaluates real-time conditions and determines when to override the scheduled plan. Two overrides currently reference water heater control without checking if a water heater exists:

1. **EXCESS_PV_HEATING (Priority 5)**: Triggers when excess PV is available and battery is healthy, sets `water_temp` to max to dump solar energy
2. **SLOT_FAILURE_FALLBACK (Priority 8)**: Triggers when no valid slot exists, sets `water_temp` to off as part of safe fallback

The `SystemState` dataclass lacks a `has_water_heater` field, so the evaluator cannot condition its behavior on water heater presence.

## Goals / Non-Goals

**Goals:**
- Prevent override logic from triggering water heater actions when `has_water_heater=false`
- Maintain clean separation: override evaluator should have all context it needs via `SystemState`

**Non-Goals:**
- Changing how water heater actions are executed downstream (already handled gracefully in `actions.py`)
- Removing or changing other override logic

## Decisions

### 1. Add `has_water_heater` to `SystemState` dataclass

**Rationale**: The `SystemState` is the contract between the engine and override evaluator. Adding the field here keeps the evaluator stateless and testable.

**Alternative considered**: Pass config directly to evaluator — rejected because it couples evaluator to config structure.

### 2. Condition EXCESS_PV_HEATING with early return guard

**Rationale**: If no water heater exists, the entire override is irrelevant. Early guard at the start of the condition block is clearest.

### 3. Conditionally include `water_temp` in SLOT_FAILURE_FALLBACK actions

**Rationale**: The slot failure fallback is still valid for battery protection even without water heater. Only the `water_temp` action should be excluded.

**Alternative considered**: Skip entire override — rejected because battery protection (`soc_target`, `grid_charging`) is still valuable.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Test coverage gap | Add explicit test cases for `has_water_heater=False` |
| Future overrides forget the check | Document in code comment that water-related actions need this check |
