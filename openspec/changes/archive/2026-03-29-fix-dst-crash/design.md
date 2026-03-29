## Context

Darkstar generates 15-minute time slot series for energy planning using `pd.date_range()` and `tz_localize()` with local timezones throughout the codebase. During DST transitions, these calls crash because:
- **Spring forward** (March): times like 02:00–02:45 don't exist → `NonExistentTimeError`
- **Fall back** (October): times like 02:00–02:45 occur twice → `AmbiguousTimeError`

Currently only `planner/inputs/data_prep.py` handles DST via try/except. All other call sites (~10 locations across 8 files) are unprotected.

## Goals / Non-Goals

**Goals:**
- Eliminate all DST-related crashes in the planner and supporting modules
- Provide a central, reusable DST-safe time utility that all code uses
- Prevent future regressions with automated detection of unsafe calls
- Handle both spring-forward and fall-back transitions correctly

**Non-Goals:**
- Migrating the entire codebase to UTC-only internals (too large a refactor)
- Changing how prices, forecasts, or schedules are displayed to users
- Modifying the scheduler/executor timing logic (already uses UTC internally)

## Decisions

### 1. Central utility module at `utils/time_utils.py`

Two functions:

**`dst_safe_date_range(start, end, freq, tz, **kwargs)`**
- Converts start/end to UTC
- Generates the date range in UTC (which never has DST gaps)
- Converts result to the target timezone via `tz_convert`
- Returns a DatetimeIndex with correct local times (gap skipped in spring, both occurrences in fall)

**`dst_safe_localize(timestamps, tz)`**
- For Series/Index: uses `tz_localize` with `nonexistent='shift_forward'` and `ambiguous='infer'`
- For single timestamps: try/except with `is_dst=True` fallback (matches existing `data_prep.py` pattern)

**Why UTC-generate-then-convert over `nonexistent=` parameter:**
- `pd.date_range` in UTC can never produce nonexistent times — the problem is structurally eliminated
- `nonexistent='shift_forward'` can produce duplicate timestamps (two slots mapped to 03:00), which would break downstream logic
- The UTC approach produces the physically correct number of slots (23h day in spring, 25h in fall)

### 2. Replace all bare calls, preserve existing `data_prep.py` pattern

Replace bare `pd.date_range(..., tz=local_tz)` and `.tz_localize(local_tz)` in production code with the utility functions. The existing DST handling in `data_prep.py` already works and uses `normalize_timestamp()` — leave it as-is since it handles individual timestamps from external data (different use case from range generation).

### 3. Regression guard via grep-based test

A test that greps production code (excluding `utils/time_utils.py` and tests) for bare `pd.date_range` calls with a `tz=` parameter that isn't `"UTC"`, and bare `.tz_localize()` calls on non-UTC targets. This catches new unsafe calls at CI time.

**Why a test over a linter plugin:** simpler to implement, runs in existing test infrastructure, no new tooling dependencies.

## Risks / Trade-offs

- **[Risk] Slot count changes on DST days** → This is correct behavior (a 23-hour day has fewer slots). The planner and executor already handle variable-length planning horizons. Verified: no code assumes exactly 96 slots per day.
- **[Risk] Fall-back produces overlapping local times** → `tz_convert` from UTC correctly assigns different UTC offsets to each occurrence. Pandas handles this natively — downstream code that compares timestamps will work because the UTC offset disambiguates.
- **[Risk] Missing a call site** → The regression guard test will catch any remaining bare calls. Manual audit of grep results during implementation provides additional safety.
