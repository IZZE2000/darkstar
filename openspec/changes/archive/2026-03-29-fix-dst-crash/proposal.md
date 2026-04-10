## Why

Every DST transition (twice per year), the planner crashes with `ValueError: nonexistent time` because `pd.date_range()` and `tz_localize()` calls throughout the codebase generate timestamps for times that don't exist during spring-forward (or are ambiguous during fall-back). This leaves the system completely non-functional — the executor falls into `slot_failure_fallback` and no energy management occurs until a manual restart or the next successful plan after the transition window passes. All users in DST timezones are affected.

## What Changes

- Create central DST-safe utility functions (`dst_safe_date_range`, `dst_safe_localize`) that generate time ranges in UTC and convert to local, avoiding all DST edge cases
- Replace all bare `pd.date_range(..., tz=local_tz)` and `.tz_localize(local_tz)` calls in production code with the safe utilities
- Add tests that specifically exercise DST spring-forward and fall-back transitions
- Add a lint/test guard to catch future introduction of bare DST-unsafe calls

## Capabilities

### New Capabilities
- `dst-safe-time`: Central DST-safe time utility functions and codebase-wide replacement of unsafe calls

### Modified Capabilities

## Impact

- `ml/forward.py` — AURORA forecast slot generation (primary crash site)
- `ml/context_features.py` — vacation mode and alarm state series (2 locations)
- `planner/output/formatter.py` — schedule output timestamp localization
- `planner/strategy/s_index.py` — S-index date calculations (3 locations)
- `backend/learning/engine.py` — learning engine slot generation and localization
- `ml/weather.py` — weather data timestamp localization
- `ml/evaluate.py` — model evaluation timestamp localization
- No API changes, no config changes, no breaking changes
