## Context

The Forecast Horizon card on the Aurora page was implemented in commit b9d297e but contains critical bugs that prevent any useful data from being displayed:

1. **History Series Location Bug**: The backend returns `history_series` at the root of the JSON response, but the TypeScript contract expects it nested inside the `horizon` object
2. **Timestamp Format Bug**: In `ml/api.py`, Open-Meteo data is keyed by timestamps using `str(ts_idx)` which produces `"2026-03-03 00:00:00+01:00"` (space separator), but slot lookups use `.isoformat()` which produces `"2026-03-03T00:00:00+01:00"` (T separator). These never match.
3. **Per-Array Data Bug**: A consequence of Bug #2 - since the Open-Meteo lookup always fails, per-array PV forecasts never get attached to slots

## Goals / Non-Goals

**Goals:**
- Fix the API response structure so actual/historical data displays correctly
- Fix timestamp serialization to enable Open-Meteo forecast data
- Ensure per-array breakdowns render when multiple arrays are configured
- **Expand window from 48h to 72h** (yesterday + today + tomorrow) for better context
- **Always use forecast API** with `past_days=1` and `forecast_days=2` for complete Open-Meteo coverage
- Maintain zero regression risk (only fixes broken code paths)

**Non-Goals:**
- Refactoring unrelated code
- Changing the visualization beyond the expanded window

## Decisions

### D1: Nest history_series Inside horizon Object
**Decision**: Move `history_series` from root level into the `stats` (horizon) object in the backend API response.

**Rationale**:
- The TypeScript contract in `types.ts` already expects this structure
- Better encapsulation - history belongs to the horizon view context
- Minimal change - single line move in `forecast.py`

**Alternative Considered**: Fix frontend to read from root level. Rejected because it leaks implementation detail and the TypeScript types already define the correct structure.

### D2: Use isoformat() for Timestamp Serialization
**Decision**: Change `ts_str = str(ts_idx)` to `ts_str = ts_idx.isoformat()` in `ml/api.py`.

**Rationale**:
- `isoformat()` is the standard, portable way to serialize timestamps
- Ensures consistent format between dictionary keys and lookup values
- Zero risk - only affects currently broken code path

### D3: Expand to 72h Window (3 Days)
**Decision**: Change horizon from 48h (today+tomorrow) to 72h (yesterday+today+tomorrow).

**Rationale**:
- Provides better context for trend analysis
- Yesterday's actual data helps validate forecast accuracy
- Consistent with expanded Open-Meteo coverage
- Backend changes: `horizon_start = start_of_yesterday`, `forecast_days=2`, `past_days=1`

### D4: Always Use Forecast API for Open-Meteo
**Decision**: Replace conditional archive/forecast API logic with always using forecast API.

**Rationale**:
- Forecast API with `past_days=1` provides hindcasts for yesterday
- Forecast API with `forecast_days=2` provides forecasts for today+tomorrow
- Eliminates the gap where today's data was missing
- Simpler code path, no conditional logic needed

## Risks / Trade-offs

**Risk**: Database or cache contains timestamps in old format → **Mitigation**: Not applicable - this is runtime data enrichment, not persistent storage

**Risk**: Frontend depends on broken behavior elsewhere → **Mitigation**: None found in code review - the broken paths return empty arrays which no code depends on

**Trade-off**: Minimal fix vs comprehensive refactor → **Decision**: Minimal fix to reduce risk and time to resolution
