## Context

The controller's `_follow_plan` mode selection (lines 191-219) has a five-branch if/elif chain that converges on `self_consumption` as the default fallback when:
- No charge planned (charge_kw = 0)
- No export planned (export_kw = 0)
- No discharge planned (discharge_kw = 0)
- SoC is above the plan target
- No EV charging active

`_calculate_charge_limit` is called AFTER mode selection and returns `(0.0, False)` when `slot.charge_kw <= 0`. The deye profile's `self_consumption` mode uses `{{charge_value}}` for `max_charge_current` — a deliberate design for PV surplus export (limit charging to planned value so excess PV exports). But on the default fallback path, charge_value = 0 blocks ALL PV→battery charging.

## Goals / Non-Goals

**Goals:**
- When self_consumption mode is the default fallback (charge_kw = 0), allow PV→battery charging at the user's configured max charge rate
- Preserve the PV surplus export behavior (planned charge limits) on the intentional self_consumption path (charge_kw > 0)

**Non-Goals:**
- Changing the profile
- Changing the mode selection logic
- Affecting any other mode (charge, export, idle)

## Decisions

### Fix location: Controller, not profile

**Decision**: Fix in `controller.py`'s `_follow_plan`, after `_calculate_charge_limit` returns.

**Rationale**: The profile correctly applies whatever `charge_value` it receives. The bug is that the controller sends 0 on the default fallback path. Fixing the controller keeps the profile simple and applies the fix to ALL profiles that use `{{charge_value}}` in self_consumption mode.

**Alternative considered**: Change the deye profile to use `{{max_charge}}` instead of `{{charge_value}}` in self_consumption. Rejected because it would break PV surplus export — the intentional limited-charge behavior where excess PV exports to grid.

### Value to use when overriding: reuse `max_charge` already computed at line 250

**Decision**: When charge_value is ≤ 0 in self_consumption mode, use:

```
charge_value = max_charge
```

`max_charge` is already computed at line 250 (`self.config.max_charge_w if unit == "W" else self.config.max_charge_a`) and respects `control_unit`. The override must be placed **after line 250** — `unit` and `max_charge` are not in scope before that point. Re-computing them earlier would duplicate logic.

### Only override when charge_value is ≤ 0

**Decision**: The override only fires when `charge_value <= 0`. When `charge_kw > 0` (PV surplus path), `charge_value` already has the correct planned value and we leave it alone.

### Minimal change surface

**Decision**: Insert the override after line 250 where `max_charge` is computed, before the ControllerDecision is constructed. No new methods, no config changes, no profile changes.

### Note on `write_charge_current`

`write_charge_current` is stored on `ControllerDecision` but is never checked in `actions.py` — the profile always writes all action values unconditionally. Setting it to `True` in the override matters only for test assertions, not runtime behavior.

## Risks / Trade-offs

- **Risk**: If a user intentionally configures `max_charge_a = 0` to prevent any charging, this fix would bypass that intent. → **Mitigation**: A max_charge of 0 is an unusual and arguably invalid configuration — the system shouldn't be running if no charging is allowed. Document this edge case.
- **Trade-off**: In the default fallback, the battery may charge faster than the planner anticipated. → The planner doesn't schedule anything in these slots, so there's no planned value to conflict with. PV charging is the desired behavior.
