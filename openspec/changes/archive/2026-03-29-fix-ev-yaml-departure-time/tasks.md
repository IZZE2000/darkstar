## 1. Executor YAML loader fix

- [x] 1.1 In `executor/config.py`, replace `import yaml` (line 12) with `from ruamel.yaml import YAML`. Remove the `import yaml` line entirely.
- [x] 1.2 In `executor/config.py`, find the function that calls `yaml.safe_load(f)` to load config.yaml. Replace it with: create a `YAML(typ='safe')` instance and call `.load(f)` on it. The return type is the same (plain Python dict).
- [x] 1.3 In `executor/config.py`, add a new helper function `_parse_departure_time(value)` directly below the existing `_str_or_none` function (around line 17). The function takes one argument (`value: Any`) and returns `str | None`. Logic: (a) if `value` is `None` or empty string → return `None`; (b) if `value` is an `int` and between 0–1439 inclusive → return `f"{value // 60:02d}:{value % 60:02d}"`; (c) if `value` is an `int` outside 0–1439 → return `None`; (d) otherwise → return `str(value) or None` (same as `_str_or_none`).
- [x] 1.4 In `executor/config.py`, find the two places where `departure_time` is read. At line 373 (`departure_time=_str_or_none(charger.get("departure_time"))`) replace `_str_or_none` with `_parse_departure_time`. There is no departure_time field on the legacy `EVChargerConfig` (line ~346), so only the per-device `EVChargerDeviceConfig` at line 373 needs changing.

## 2. Planner defensive fallback

- [x] 2.1 In `planner/pipeline.py`, in the `calculate_ev_deadline` function (starts at line 45), add an integer handling block right after the `if not departure_time: return None` check (after line 65). The block: if `isinstance(departure_time, int)` and value is between 0–1439 inclusive, convert to `f"{departure_time // 60:02d}:{departure_time % 60:02d}"` and reassign to `departure_time`. If the int is outside 0–1439, log a warning and return `None`.

## 3. Frontend placeholder fix

- [x] 3.1 In `frontend/src/pages/settings/components/EntityArrayEditor.tsx`, at line 473, change `placeholder="07:00"` to `placeholder="e.g. 07:00"`.

## 4. Tests

- [x] 4.1 Add a test in `tests/ev/test_ev_departure_deadline.py` for the integer fallback in `calculate_ev_deadline`: calling `calculate_ev_deadline(960, now, "Europe/Stockholm")` SHALL return the same result as calling `calculate_ev_deadline("16:00", now, "Europe/Stockholm")`. Also test that `calculate_ev_deadline(1020, now, "Europe/Stockholm")` matches `"17:00"`, and `calculate_ev_deadline(9999, now, "Europe/Stockholm")` returns `None`.
- [x] 4.2 Add a test in `tests/config/` (new file `test_departure_time_parsing.py`) for `_parse_departure_time`: test that `_parse_departure_time(960)` returns `"16:00"`, `_parse_departure_time(1020)` returns `"17:00"`, `_parse_departure_time(420)` returns `"07:00"`, `_parse_departure_time(0)` returns `"00:00"`, `_parse_departure_time(1439)` returns `"23:59"`, `_parse_departure_time(1440)` returns `None`, `_parse_departure_time(-1)` returns `None`, `_parse_departure_time(None)` returns `None`, `_parse_departure_time("")` returns `None`, `_parse_departure_time("16:00")` returns `"16:00"`.
- [x] 4.3 Run the full existing EV test suite (`pytest tests/ev/ -v`) and confirm all tests pass.
