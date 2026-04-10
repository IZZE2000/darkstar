## Why

`backend/api/routers/services.py` (741 lines, 14 endpoints) is a monolithic router file mixing five unrelated domains: Home Assistant integration, energy data, water heating controls, WebSocket status, and schedule simulation. This makes the file hard to navigate, increases merge conflict risk, and violates the project's established pattern of focused, single-domain router files. The recent `split-move-inputs` refactoring (inputs.py → 4 backend/core modules) established a clean precedent. This change continues that cleanup effort by splitting services.py into focused router modules.

## What Changes

- **Split `backend/api/routers/services.py` into 3 new router files:**
  - `ha.py` — Home Assistant integration (entity, average, entities, services, test, ha-socket)
  - `energy.py` — Energy data and performance metrics (energy/today, energy/range, performance/data)
  - `water.py` — Water heating controls (boost GET/POST/DELETE)
- **Move `simulate` endpoint into existing `schedule.py`** — semantically correct home (reads schedule.json, runs schedule simulation)
- **Remove deprecated `/api/ha/water_today` endpoint** — stub returning only `{deprecated: true}`, no longer needed. **BREAKING** for any client still calling this endpoint.
- **Clean up all references to the removed endpoint** — frontend API definition, benchmark scripts, verification scripts, performance tests
- **Delete `services.py`** after all endpoints are relocated
- **Update `main.py` router registration** — replace 2 services routers with 4 new router imports
- **Update `dashboard.py` cross-module call** — `services.get_water_boost()` → `water.get_water_boost()`
- **Add route-preservation snapshot test** — safety gate verifying all URLs remain registered
- **Add endpoint smoke tests** — permanent test coverage for all relocated endpoints

## Capabilities

### New Capabilities
- `router-structure`: Defines the project's conventions for organizing API router files, router naming, import patterns, and registration in main.py. Captures the split layout and the rules that prevent future monolithic routers.

### Modified Capabilities
- `energy-totals-api`: The endpoints `/api/energy/today` and `/api/energy/range` move from services.py to energy.py. No requirement changes — only the source file location changes.

## Impact

- **Backend files changed:** `main.py`, `dashboard.py`, `schedule.py` (modified); `ha.py`, `energy.py`, `water.py` (created); `services.py` (deleted)
- **Frontend files changed:** `frontend/src/lib/api.ts` (remove `haWaterToday` definition)
- **Scripts changed:** `scripts/bench_dashboard.py`, `scripts/verify_slow.py`, `scripts/verify_arc1_routes.py` (remove water_today references)
- **Tests changed:** `tests/performance/test_dashboard_performance.py` (remove water_today threshold); new test files added for route snapshot + smoke tests
- **API surface:** All existing URLs preserved exactly. Only removal: `GET /api/ha/water_today` (deprecated stub).
- **No dependency changes** — no new packages required
