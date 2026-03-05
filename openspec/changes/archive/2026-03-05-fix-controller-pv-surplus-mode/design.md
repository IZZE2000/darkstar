## Context

The executor's controller module (`executor/controller.py`) translates planner decisions into inverter mode selections. The `_follow_plan()` method determines the appropriate mode intent based on a `SlotPlan` object containing `charge_kw`, `discharge_kw`, `export_kw`, and other fields.

**Current Bug**: The method prioritizes `export_kw > 0` over `charge_kw > 0` without checking `discharge_kw`. This causes incorrect mode selection when the planner outputs PV surplus scenarios (charge + export, but no battery discharge).

**Deye Discovery**: Testing revealed that Deye inverters CAN export excess PV while charging the battery if:
1. Work mode is "Zero Export to CT"
2. "Solar Sell" toggle is ON (default)
3. `max_charge_current` is limited to less than available PV surplus

This means `charge_value` (already calculated) can be used to enable simultaneous charge+export on Deye, matching Fronius capability.

## Goals / Non-Goals

**Goals:**
- Fix mode selection logic to correctly distinguish between:
  - Battery export to grid (`export_kw > 0` AND `discharge_kw > 0`)
  - PV surplus export (`export_kw > 0` AND `discharge_kw == 0` AND `charge_kw > 0`)
- Enable Deye inverters to export excess PV while charging by adding `max_charge_current` to `self_consumption` mode
- Maintain backward compatibility with all existing inverter profiles
- Add unit tests to prevent regression

**Non-Goals:**
- Modifying planner logic (planner correctly produces these outputs)
- Adding new mode types (4 existing modes are sufficient)
- Profile-level capability flags (not needed - the profile change handles this)
- Controlling "Solar Sell" entity (user responsibility, ON by default)
- Planner inverter-awareness (not needed after this fix)

## Decisions

### Decision 1: Check `discharge_kw` before selecting export mode

**Rationale**: The key distinction is whether the battery is actively discharging to the grid. If `discharge_kw == 0`, the export is PV surplus, not battery export.

**Alternative Considered**: Add a fifth mode for "PV surplus export". Rejected because:
- All inverter profiles correctly handle PV surplus via `self_consumption` mode
- Adding complexity without benefit

### Decision 2: Add `max_charge_current` to Deye `self_consumption` mode

**Rationale**:
- Deye in "Zero Export to CT" mode with "Solar Sell" ON will export excess PV
- Limiting `max_charge_current` forces excess PV to export instead of curtailment
- `charge_value` is already calculated by controller (`_calculate_charge_limit`)
- Template already supports `{{charge_value}}`

**Implementation**:
```yaml
self_consumption:
  actions:
    - entity: "work_mode"
      value: "Zero Export to CT"
    - entity: "grid_charging_enable"
      value: off
    - entity: "max_charge_current"
      value: "{{charge_value}}"  # Limit charge → excess PV exports
    - entity: "soc_target"
      value: "{{soc_target}}"
    - entity: "max_discharge_current"
      value: "{{max_discharge}}"
```

**Why This Works**:
1. Planner outputs `charge_kw=3.5` for 3.5kW battery charging
2. Controller calculates `charge_value=~73A` (already implemented)
3. Profile writes `max_charge_current=73A` to inverter
4. If PV is 10kW and load is 1kW, then 3.5kW charges battery, 5.5kW exports

**Comment to Add**:
```yaml
- entity: "max_charge_current"
  value: "{{charge_value}}"
  # Limit PV charging current to enable excess export.
  # With Solar Sell ON, excess PV beyond this limit exports to grid.
```

**Alternative Considered**: Create a separate "pv_surplus_export" mode. Rejected because:
- Self consumption IS the correct semantic mode for this scenario
- Just need to add the charge limit action

### Decision 3: Keep grid charging separate from PV charging

**Rationale**: The existing condition `slot.charge_kw > 0 and slot.export_kw == 0` handles grid charging scenarios where there's no PV surplus. This remains unchanged.

## Risks / Trade-offs

**Risk 1**: Deye users without "Solar Sell" toggle ON won't get PV export
- **Mitigation**: "Solar Sell" is ON by default on Deye inverters. Document this requirement in profile comments. Users who disabled it can re-enable in Home Assistant.

**Risk 2**: Deye behavior depends on firmware version
- **Mitigation**: Test with beta testers. Document firmware requirements if needed. The fallback (no export) is safe - just suboptimal.

**Risk 3**: Existing behavior change might affect users who "worked around" the bug
- **Mitigation**: The bug caused incorrect behavior (battery discharging when it should charge). Any "workaround" would have been compensating for wrong behavior. The fix restores intended behavior.

## Migration Plan

1. Deploy fix to staging/testing environment
2. Verify unit tests pass
3. Manual testing with Fronius beta tester (original reporter)
4. Manual testing with Deye beta tester (verify PV surplus export)
5. Deploy to production
6. Monitor execution logs for correct mode selection

**Rollback**: Single-line revert for controller, single-line removal for profile. No data migration needed.

## Future Enhancements (Out of Scope)

- Add "Solar Sell" entity to profile for explicit control (if users request it)
- Add profile capability flag for "supports_simultaneous_charge_export" (not needed now)
- Planner awareness of inverter capabilities (not needed - native logic handles it)
