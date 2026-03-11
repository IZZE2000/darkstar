## Context

The executor controls multiple devices:
1. **Inverter** (via profile-driven actions) - battery, work mode, SOC target
2. **EV Charger** (separate control) - on/off switch
3. **Water Heater** (separate control) - temperature setpoint

During ARC17 Inverter Profile Redesign, the executor was refactored to use profile-driven actions for inverter control. However, water heater control was incorrectly removed - it was not added as a separate control path like EV charger.

The `set_water_temp()` method exists in `ActionDispatcher` and works correctly. It just needs to be called.

## Goals / Non-Goals

**Goals:**
- Fix water heater temperature execution during normal scheduled operation
- Ensure water temp changes are logged to execution history
- Follow the established EV charger control pattern

**Non-Goals:**
- Changes to override logic (already works correctly)
- Changes to profile system (water heater is not an inverter entity)
- Changes to planner/scheduler

## Decisions

### Decision 1: Execute water temp in _tick() after EV charger control

**Rationale**: Mirrors the EV charger pattern exactly. Both are external HA entities controlled independently from the inverter.

**Alternative considered**: Add water_temp to profile actions.
- **Rejected**: Water heater is not an inverter function. Profiles are for inverter-specific control. Adding it would mix concerns and require all profiles to include water temp actions.

**Implementation**:
```python
# In ExecutorEngine._tick(), after line 1258 (after _control_ev_charger),
# inside the existing `if self.dispatcher:` block (line 1262), before dispatcher.execute():
# Control Water Heater Temperature
if self._has_water_heater and self.config.water_heater.target_entity:
    water_result = await self.dispatcher.set_water_temp(decision.water_temp)
    action_results.append(water_result)
```

> **Placement matters**: This call must be inside the `if self.dispatcher:` guard that already wraps `dispatcher.execute()` at line 1262, and placed **before** that `execute()` call so all results are collected together.

### Decision 2: Append to action_results for history logging

**Rationale**: The `action_results` list is already logged to execution history. By appending the water temp result, it will appear in the UI's Execution History tab.

**Current boost behavior**: `set_water_boost()` calls `dispatcher.set_water_temp()` but doesn't log to history. This is acceptable - boost is a manual user action, not scheduled execution.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Double execution if called elsewhere | `set_water_temp()` is idempotent — skips if already at target. Note: a concurrent water boost `create_task()` mid-tick could attempt a parallel HA write, but the idempotency check in `set_water_temp()` mitigates this in practice |
| Shadow mode not respected | `set_water_temp()` already checks shadow mode internally |
| Entity not configured | `set_water_temp()` returns `skipped=True` if entity not configured |
| `dispatcher` is None | Call must be inside the existing `if self.dispatcher:` guard — not a standalone call |
