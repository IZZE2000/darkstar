## 1. Implementation

- [x] 1.1 Add type conversion block in `ml/corrector.py` after `get_forecast_slots()` call
- [x] 1.2 Convert each record's `slot_start` from string to `pd.Timestamp` with `tz_convert(tz)`
- [x] 1.3 Ensure conversion happens before the `if not base_records` guard clause

## 2. Verification

- [x] 2.1 Run `./scripts/lint.sh` and fix any failures
- [x] 2.2 Verify no `AttributeError: 'str' object has no attribute 'astimezone'` in code paths at lines 357, 377, 432
- [x] 2.3 Verify no merge type mismatch errors with weather_df or vacation_mode_flag DataFrames

## 3. Documentation

- [x] 3.1 Add inline comment explaining the conversion (e.g., "Convert slot_start strings → timezone-aware Timestamps (api.py returns ISO strings)")
