## Context

`backend/api/routers/services.py` is a 741-line monolithic router containing 14 endpoints across 5 unrelated domains. The project already follows a pattern of focused router files (e.g., `config.py`, `executor.py`, `forecast.py`, `loads.py`), and the recent `split-move-inputs` refactoring established a proven pattern for splitting large files.

**Current services.py structure:**
- Two router objects: `router_ha` (prefix `/api/ha`) and `router_services` (prefix `/api`)
- 14 endpoints, 1 private helper (`_fetch_ha_history_avg`), 1 Pydantic model (`WaterBoostRequest`)
- Cross-module call: `dashboard.py` imports and calls `services.get_water_boost()` directly

**Cross-references that must be updated:**
- `main.py` lines 29, 259-260: imports and registers both routers
- `dashboard.py` line 7, 33: imports services module, calls `services.get_water_boost()`
- `frontend/src/lib/api.ts` line 561: references deprecated `/api/ha/water_today`
- 3 scripts + 1 test: reference `/api/ha/water_today`

## Goals / Non-Goals

**Goals:**
- Split services.py into focused, single-domain router files following project conventions
- Preserve all URL paths exactly (zero frontend breakage)
- Remove the deprecated `/api/ha/water_today` stub endpoint and all its references
- Move `simulate` endpoint to its semantic home (`schedule.py`)
- Add route-preservation snapshot test as a permanent safety gate
- Add endpoint smoke tests for permanent coverage of all relocated endpoints
- Delete services.py completely (no shims, no re-exports)

**Non-Goals:**
- Changing any URL paths or API contracts
- Refactoring endpoint internals (logic stays identical, just moves between files)
- Adding full functional/integration tests (smoke tests only)
- Changing OpenAPI tags (tags will naturally update to match new file domains, this is cosmetic)
- Splitting schedule.py or any other existing router

## Decisions

### Decision 1: Three new files + one existing file

**Choice:** Split into `ha.py`, `energy.py`, `water.py` (new) + add `simulate` to `schedule.py` (existing).

**Alternatives considered:**
- *Two files (ha.py + energy.py with water mixed in):* Simpler but loses semantic clarity. Water boost is a distinct feature with its own Pydantic model and executor dependency.
- *Four new files (including simulate.py):* Overkill — a 22-line endpoint doesn't warrant its own file. `schedule.py` already reads `data/schedule.json` and works with schedule data.

**Rationale:** Three new files gives clean domain boundaries. Each file has a clear single responsibility and a reasonable size (120-280 lines). Simulate fits naturally in schedule.py.

### Decision 2: ha.py exports two routers

**Choice:** `ha.py` exports `router` (prefix `/api/ha`) and `router_misc` (prefix `/api`) for the ha-socket endpoint.

**Rationale:** The `/api/ha-socket` endpoint's URL path is `/api/ha-socket` (on the `/api` prefix router). Moving it to the `/api/ha` prefix would change its URL to `/api/ha/ha-socket`, which breaks the frontend. Two routers per file is an established pattern — `forecast.py` already exports `router` and `forecast_router`.

**Alternative considered:** Leave ha-socket in energy.py. Rejected because ha-socket is semantically HA-domain (it checks the HA WebSocket connection).

### Decision 3: Delete services.py with no backwards-compatibility shims

**Choice:** Clean delete. No `__init__.py` re-exports, no `services.py` stub importing from new modules.

**Rationale:** Follows the `split-move-inputs` precedent which deleted `inputs.py` entirely. All consumers are updated with explicit imports. Re-exports create confusion and hide actual dependencies.

### Decision 4: Remove deprecated water_today endpoint

**Choice:** Delete the endpoint, its frontend API definition, and all script/test references.

**Rationale:** The endpoint is a stub returning `{deprecated: true, water_kwh_today: 0.0}`. It provides zero value. The replacement (`/api/energy/today` with `water_heating_kwh` field) has been available. Cleaning this up during the split avoids carrying dead code into the new file structure.

### Decision 5: Route-preservation test + smoke tests

**Choice:** Create a route-snapshot test BEFORE the split (verifying all 13 post-removal URLs exist), then add per-endpoint smoke tests that verify each endpoint returns a non-500 response with mocked dependencies.

**Rationale:** The snapshot test is the primary safety gate — it catches any URL path regression immediately. Smoke tests provide permanent coverage for the 11 previously untested endpoints and serve as an ongoing regression safety net.

**Test file structure:** Single file `tests/api/test_services_split.py` containing both the route snapshot and all smoke tests. This keeps the refactoring-related tests together and avoids scattering test updates across multiple files.

### Decision 6: Endpoint grouping

| File | Router(s) | Endpoints | Key Dependencies |
|------|-----------|-----------|-----------------|
| `ha.py` | `router` (prefix `/api/ha`), `router_misc` (prefix `/api`) | entity, average, entities, services, test + ha-socket | `ha_client`, `secrets`, `httpx`, `cache` |
| `energy.py` | `router` (prefix `/api`) | energy/today, energy/range, performance/data | `LearningStore`, `secrets`, `sqlalchemy` |
| `water.py` | `router` (prefix `/api/water`) | boost GET/POST/DELETE | `executor` |
| `schedule.py` | existing `router` | simulate (added) | `planner.simulation`, `secrets` |

### Decision 7: Logger naming convention

Each new file gets its own logger following the established pattern:
- `ha.py`: `darkstar.api.ha`
- `energy.py`: `darkstar.api.energy`
- `water.py`: `darkstar.api.water`
- `schedule.py`: keeps existing `darkstar.api.schedule`

## Risks / Trade-offs

**[Risk] URL path accidentally changes during split** → Mitigation: Route-snapshot test created BEFORE the split catches this immediately. Test must pass before and after.

**[Risk] dashboard.py cross-module call breaks** → Mitigation: Explicit task to update `dashboard.py` import from `services` to `water`. The function signature doesn't change, only the import path.

**[Risk] Implementer misses a consumer of services.py** → Mitigation: The grep `from backend.api.routers.services|from backend.api.routers import.*services` found only 2 Python consumers (main.py, dashboard.py). Tasks enumerate every file explicitly.

**[Risk] OpenAPI tag changes confuse frontend** → Low risk. Tags are for Swagger UI grouping only; the frontend uses URL paths, not tags. Tag changes from `["services"]` to `["energy"]`/`["water"]`/`["ha"]` are cosmetic.

**[Risk] Test patches targeting old module path break** → Low risk. Investigation found no test patches directly targeting `backend.api.routers.services.*`. All patches target the underlying modules (`backend.core.ha_client`, `backend.core.secrets`, etc.).

**[Trade-off] schedule.py grows by ~22 lines** → Acceptable. The file goes from 535 to ~557 lines, and the simulate endpoint is a natural semantic fit.

**[Trade-off] ha.py has two routers** → Acceptable. This is an established project pattern (forecast.py does the same). The alternative (changing the URL) is worse.
