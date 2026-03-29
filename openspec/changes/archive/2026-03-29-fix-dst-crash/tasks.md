## 1. Create DST-safe utility module

- [x] 1.1 Create directory `utils/` at project root and add an empty `utils/__init__.py` file
- [x] 1.2 Create `utils/time_utils.py` with function `dst_safe_date_range(start, end, freq, tz, **kwargs)`. This function MUST: (a) convert `start` and `end` to UTC using `.astimezone(pytz.UTC)` (handle naive datetimes by localizing to `tz` first), (b) call `pd.date_range(start=start_utc, end=end_utc, freq=freq, tz="UTC", **kwargs)`, (c) convert the result to the target timezone with `.tz_convert(tz)`, (d) return the resulting `pd.DatetimeIndex`
- [x] 1.3 In the same `utils/time_utils.py`, add function `dst_safe_localize(timestamps, tz)`. This function MUST handle two input types: (a) for `pd.Series` or `pd.DatetimeIndex`: call `.dt.tz_localize(tz, nonexistent='shift_forward', ambiguous='infer')` (or `.tz_localize(...)` for DatetimeIndex), (b) for single `datetime` objects: use `try: tz.localize(dt)` with `except (AmbiguousTimeError, NonExistentTimeError): tz.localize(dt, is_dst=True)`. Import `AmbiguousTimeError` and `NonExistentTimeError` from `pytz.exceptions`

## 2. Replace unsafe calls in ML modules

- [x] 2.1 In `ml/forward.py` around line 140: replace `pd.date_range(start=slot_start, end=horizon_end, freq="15min", tz=tz, inclusive="left")` with `dst_safe_date_range(start=slot_start, end=horizon_end, freq="15min", tz=tz, inclusive="left")`. Add import: `from utils.time_utils import dst_safe_date_range`
- [x] 2.2 In `ml/context_features.py` around line 97: replace `pd.date_range(start=start_local, end=end_local, freq="15min", tz=tz)` with `dst_safe_date_range(start=start_local, end=end_local, freq="15min", tz=tz)`. Add import: `from utils.time_utils import dst_safe_date_range`
- [x] 2.3 In `ml/context_features.py` around line 180: replace the second `pd.date_range(start=start_local, end=end_local, freq="15min", tz=tz)` with `dst_safe_date_range(start=start_local, end=end_local, freq="15min", tz=tz)` (same import already added in 2.2)
- [x] 2.4 In `ml/weather.py` around line 364: replace `dt_index.tz_localize(tz)` with `dst_safe_localize(dt_index, tz)`. Keep the existing `if dt_index.tz is None` guard and the `else dt_index.tz_convert(tz)` branch. Add import: `from utils.time_utils import dst_safe_localize`
- [x] 2.5 In `ml/evaluate.py` around line 86: replace `df["slot_start"].dt.tz_localize(engine.timezone)` with `dst_safe_localize(df["slot_start"], engine.timezone)`. Keep the existing `if/else` structure. Add import: `from utils.time_utils import dst_safe_localize`

## 3. Replace unsafe calls in planner modules

- [x] 3.1 In `planner/output/formatter.py` around line 66: replace `start_series.dt.tz_localize(tz)` with `dst_safe_localize(start_series, tz)`. Add import: `from utils.time_utils import dst_safe_localize`
- [x] 3.2 In `planner/output/formatter.py` around line 80: replace `end_series.dt.tz_localize(tz)` with `dst_safe_localize(end_series, tz)` (same import already added in 3.1)
- [x] 3.3 In `planner/strategy/s_index.py` around line 74: replace `df.index.tz_localize(tz)` with `dst_safe_localize(df.index, tz)`. Add import: `from utils.time_utils import dst_safe_localize`
- [x] 3.4 In `planner/strategy/s_index.py` around line 220: replace `df.index.tz_localize(tz)` with `dst_safe_localize(df.index, tz)` (same import already added in 3.3)
- [x] 3.5 In `planner/strategy/s_index.py` around line 374: replace `df.index.tz_localize(tz)` with `dst_safe_localize(df.index, tz)` (same import already added in 3.3)

## 4. Replace unsafe calls in backend modules

- [x] 4.1 In `backend/learning/engine.py` around line 166: replace `df["timestamp"].dt.tz_localize(self.timezone)` with `dst_safe_localize(df["timestamp"], self.timezone)`. Add import: `from utils.time_utils import dst_safe_date_range, dst_safe_localize`
- [x] 4.2 In `backend/learning/engine.py` around line 195: replace `pd.date_range(start=start_time, end=end_time, freq=f"{resolution_minutes}min", tz=self.timezone)` with `dst_safe_date_range(start=start_time, end=end_time, freq=f"{resolution_minutes}min", tz=self.timezone)` (same import already added in 4.1)
- [x] 4.3 In `backend/learning/engine.py` around line 294: replace `df["timestamp"].dt.tz_localize(self.timezone)` with `dst_safe_localize(df["timestamp"], self.timezone)` (same import already added in 4.1)
- [x] 4.4 In `backend/learning/engine.py` around line 323: replace `pd.date_range(start=start_time, end=end_time, freq=f"{resolution_minutes}min", tz=self.timezone, inclusive="both")` with `dst_safe_date_range(start=start_time, end=end_time, freq=f"{resolution_minutes}min", tz=self.timezone, inclusive="both")` (same import already added in 4.1)

## 5. Tests

- [x] 5.1 Create `tests/utils/test_time_utils.py`. Test `dst_safe_date_range` with three scenarios: (a) spring-forward 2026-03-29 in Europe/Stockholm — verify no timestamps exist between 02:00 and 03:00, verify 20 slots for a 00:00→06:00 range, (b) fall-back 2026-10-25 in Europe/Stockholm — verify 28 slots for a 00:00→06:00 range covering both occurrences of the ambiguous hour, (c) normal day — verify result matches standard `pd.date_range`
- [x] 5.2 In the same test file, test `dst_safe_localize` with two scenarios: (a) Series containing `2026-03-29 02:30:00` in Europe/Stockholm — verify it shifts forward to 03:00 without error, (b) Series containing `2026-10-25 02:30:00` in Europe/Stockholm — verify it localizes without error
- [x] 5.3 Create `tests/utils/test_no_bare_tz_calls.py`. Write a regression guard test that: (a) globs all `.py` files under `ml/`, `planner/`, `backend/`, `executor/` (excluding `tests/` and `utils/time_utils.py`), (b) reads each file and checks for `pd.date_range(` calls containing `tz=` where the tz value is NOT `"UTC"` or `UTC`, (c) checks for `.tz_localize(` calls where the argument is NOT `"UTC"` or `UTC`, (d) fails with a clear message listing the offending files and lines if any are found

## 6. Verify

- [x] 6.1 Run `python -m pytest tests/utils/test_time_utils.py -v` and confirm all tests pass
- [x] 6.2 Run `python -m pytest tests/utils/test_no_bare_tz_calls.py -v` and confirm the regression guard passes (no bare unsafe calls remain in production code)
- [x] 6.3 Run `python -m pytest tests/ -x --timeout=60` to confirm no existing tests are broken by the changes

## Implementation Complete

All 23 tasks have been completed successfully. The DST-safe utility module has been created and all unsafe timezone-aware calls have been replaced throughout the codebase. Two pre-existing test failures (unrelated to DST changes) were identified:
- `tests/ml/test_reflex.py::TestLowSocEventsQuery::test_finds_low_soc_during_peak`
- `tests/planner/test_schedule_history_overlay.py::test_today_with_history_includes_past`

All other 816 tests pass.
