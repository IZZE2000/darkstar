## 1. SystemState Updates

- [x] 1.1 Add `has_water_heater: bool = True` field to `SystemState` dataclass in `executor/override.py`
- [x] 1.2 Pass `has_water_heater` from engine to SystemState in `_gather_system_state()` method

## 2. Override Logic Updates

- [x] 2.1 Add `state.has_water_heater` condition to EXCESS_PV_HEATING override check
- [x] 2.2 Conditionally include `water_temp` in SLOT_FAILURE_FALLBACK actions based on `has_water_heater`

## 3. Tests

- [x] 3.1 Add test: EXCESS_PV_HEATING skipped when `has_water_heater=False`
- [x] 3.2 Add test: EXCESS_PV_HEATING triggers when `has_water_heater=True`
- [x] 3.3 Add test: SLOT_FAILURE_FALLBACK excludes `water_temp` when `has_water_heater=False`
- [x] 3.4 Add test: SLOT_FAILURE_FALLBACK includes `water_temp` when `has_water_heater=True`

## 4. Verification

- [x] 4.1 Run `./scripts/lint.sh` and fix any issues
- [x] 4.2 Run override tests: `uv run python -m pytest tests/executor/test_executor_override.py -v`
