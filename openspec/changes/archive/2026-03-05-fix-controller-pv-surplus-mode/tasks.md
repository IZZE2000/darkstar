## 1. Fix Controller Logic

- [x] 1.1 Update `_follow_plan()` mode selection logic in `executor/controller.py` (lines 186-195)
- [x] 1.2 Add inline comments explaining the PV surplus vs battery export distinction
- [x] 1.3 Verify all four mode intents are still reachable (export, charge, idle, self_consumption)
- [x] 1.4 Fix: Add distinction between grid charging (charge mode) and PV surplus (self_consumption mode)

## 2. Enhance Deye Profile

- [x] 2.1 Add `max_charge_current` action to `self_consumption` mode in `profiles/deye.yaml`
- [x] 2.2 Add comment explaining why charge limit enables PV export with Solar Sell
- [x] 2.3 Verify `{{charge_value}}` template variable is available (already implemented in controller)

## 3. Add Unit Tests

- [x] 3.1 Create test file `tests/executor/test_controller_modes.py` (or add to existing test file)
- [x] 3.2 Test: PV surplus scenario (`charge_kw > 0, export_kw > 0, discharge_kw = 0`) → `self_consumption`
- [x] 3.3 Test: Battery export scenario (`discharge_kw > 0, export_kw > 0, charge_kw = 0`) → `export`
- [x] 3.4 Test: Grid charge scenario (`charge_kw > 0, export_kw = 0, discharge_kw = 0`) → `charge`
- [x] 3.5 Test: Idle scenario (`charge_kw = 0, export_kw = 0, discharge_kw = 0, soc_at_target`) → `idle`
- [x] 3.6 Test: Self consumption default (`all values = 0, soc_below_target`) → `self_consumption`
- [x] 3.7 Test: Deye profile renders `max_charge_current` with correct `{{charge_value}}`

## 4. Verification

- [x] 4.1 Run `./scripts/lint.sh` to ensure code quality
- [x] 4.2 Run all existing executor tests to verify no regressions
- [x] 4.3 Manual verification with Fronius beta tester logs (original bug report)
- [x] 4.4 Manual verification with Deye beta tester (verify PV surplus export with limited charge)

## 5. Documentation

- [x] 5.1 Update Deye profile comments to explain Solar Sell requirement
- [x] 5.2 No user-facing documentation changes needed (Solar Sell is ON by default)
