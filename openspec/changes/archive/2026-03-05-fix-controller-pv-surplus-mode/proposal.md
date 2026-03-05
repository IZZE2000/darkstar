## Why

The controller incorrectly selects "export" mode (battery discharge to grid) when the planner outputs PV surplus scenarios (`charge_kw > 0`, `export_kw > 0`, `discharge_kw = 0`). This causes the battery to discharge instead of charge during high PV production, directly opposing the planner's intent. A Fronius beta tester reported their battery was discharging while the schedule showed it should charge to 100% SoC.

This is a critical bug affecting all inverter profiles (Fronius, Deye, Sungrow, Generic) and breaks the core contract between planner and executor.

Additionally, Deye inverters can now support simultaneous battery charging and PV export by limiting `max_charge_current` in "Zero Export to CT" mode with "Solar Sell" enabled.

## What Changes

### Controller Bug Fix (All Profiles)
- Fix mode selection logic in `executor/controller.py:_follow_plan()` (lines 182-186)
- The controller now checks `discharge_kw` before selecting "export" mode
- PV surplus scenarios now correctly use "self_consumption" mode instead of "export"

### Deye Profile Enhancement
- Add `max_charge_current` action to `self_consumption` mode in `profiles/deye.yaml`
- This enables Deye inverters to export excess PV while charging battery
- Requires "Solar Sell" toggle ON (default) on the inverter
- No breaking changes - existing behavior preserved for users without Solar Sell

## Capabilities

### New Capabilities

- `deye-pv-surplus-export`: Deye inverters can export excess PV while charging battery by limiting charge current in self_consumption mode

### Modified Capabilities

None - this fixes implementation to match existing requirements and adds new optional capability.

## Impact

**Affected Code:**
- `executor/controller.py` - `_follow_plan()` method (mode selection logic, ~10 lines)
- `profiles/deye.yaml` - `self_consumption` mode actions (+1 entity)
- Unit tests in `tests/executor/`

**Affected Inverter Profiles:**
- Fronius: "Auto" mode now correctly selected for PV surplus ✅
- Deye: "Zero Export to CT" mode now correctly selected + charge limit enables export ✅
- Sungrow: "Self-consumption mode" now correctly selected for PV surplus ✅
- Generic: Correct mode selected based on profile configuration ✅

**User Impact:**
- Fixes battery discharging when it should be charging (critical bug)
- Deye users can now export PV surplus while charging (new capability)
- No configuration changes required (Solar Sell is ON by default)
