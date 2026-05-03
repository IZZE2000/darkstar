## 1. Controller fix

- [x] 1.1 In `executor/controller.py` `_follow_plan()`: after line 250 where `max_charge` is computed, add an override so that when `mode_intent == "self_consumption"` and `charge_value <= 0`, set `charge_value = max_charge` and `write_charge = True`. Do NOT place this before line 250 — `unit` and `max_charge` are not in scope until then.

## 2. Tests

- [x] 2.1 Add test in `tests/executor/test_executor_controller.py`: verify default self_consumption fallback sets `charge_value` to `max_charge_a` (not 0) when nothing is planned and SoC is above target
- [x] 2.2 Add test: verify PV surplus path (charge_kw > 0) still uses the planned charge_value and is NOT overridden to max

## 3. Verification

- [x] 3.1 Run `./scripts/lint.sh` and fix any failures
- [x] 3.2 Run existing controller tests with `uv run python -m pytest tests/executor/test_executor_controller.py -v` and verify all pass
