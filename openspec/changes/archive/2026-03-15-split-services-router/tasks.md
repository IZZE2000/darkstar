## 1. Baseline & Safety Gate

- [x] 1.1 Run the full test suite with `pytest` and record the exact number of passing tests. Save this number — it is the baseline. Every phase must match or exceed it.

- [x] 1.2 Create the route-preservation snapshot test file `tests/api/test_route_snapshot.py`. This test verifies that all 14 current services.py endpoints are registered in the app. Use the same test client pattern as other API tests (import `create_app`, unwrap Socket.IO, use `TestClient`). The test must extract all registered routes from the FastAPI app and assert that each of these exact method+path combinations exists:
  ```
  GET  /api/ha/entity/{entity_id}
  GET  /api/ha/average
  GET  /api/ha/entities
  GET  /api/ha/services
  POST /api/ha/test
  GET  /api/ha/water_today
  GET  /api/water/boost
  POST /api/water/boost
  DELETE /api/water/boost
  GET  /api/energy/today
  GET  /api/energy/range
  GET  /api/performance/data
  GET  /api/ha-socket
  POST /api/simulate
  ```
  To extract routes, iterate over `app.routes`, check for `hasattr(route, 'methods')` and `hasattr(route, 'path')`, and build a set of `f"{method} {route.path}"` strings. Assert each expected route is in the set, with a clear failure message naming the missing route.

- [x] 1.3 Run `pytest tests/api/test_route_snapshot.py -v` and verify the snapshot test passes. Then run the full suite with `pytest` and verify the total pass count is baseline + 1.

## 2. Create `backend/api/routers/ha.py`

- [x] 2.1 Create the file `backend/api/routers/ha.py` with the following structure. Copy the endpoint functions and helper EXACTLY as they appear in `services.py` — do NOT refactor or modify any logic.

  **Imports (top of file):**
  ```python
  import logging
  from datetime import datetime, timedelta
  from typing import Any, cast

  import httpx
  import pytz
  from fastapi import APIRouter

  from backend.core.ha_client import get_ha_entity_state, make_ha_headers
  from backend.core.secrets import load_home_assistant_config, load_yaml
  ```

  **Module-level variables:**
  ```python
  logger = logging.getLogger("darkstar.api.ha")

  router = APIRouter(prefix="/api/ha", tags=["ha"])
  router_misc = APIRouter(prefix="/api", tags=["ha"])
  ```

  **Functions to copy from `services.py` (in this order):**
  1. `_fetch_ha_history_avg(entity_id: str, hours: int) -> float` (services.py lines 25-105) — private helper, no decorator
  2. `get_ha_entity(entity_id: str)` (lines 108-122) — decorator: `@router.get("/entity/{entity_id}", summary="Get HA Entity", description="Returns the state of a specific Home Assistant entity.")`
  3. `get_ha_average(entity_id: str | None = None, hours: int = 24)` (lines 125-189) — decorator: `@router.get("/average", summary="Get Entity Average", description="Calculate average value for an entity over the last N hours.")`
  4. `get_ha_entities()` (lines 192-240) — decorator: `@router.get("/entities", summary="List HA Entities", description="List available Home Assistant entities.")`
  5. `get_water_today()` (lines 279-316) — decorator: `@router.get("/water_today", summary="[DEPRECATED] Get Water Heating Energy", description="DEPRECATED: Use /api/services/energy/today instead. Returns water_heating_kwh field.")` — This is temporary; it will be removed in Phase 4.
  6. `get_ha_services()` (lines 645-674) — decorator: `@router.get("/services", summary="List HA Services", description="List available Home Assistant services.")`
  7. `test_ha_connection()` (lines 677-700) — decorator: `@router.post("/test", summary="Test HA Connection", description="Test connection to Home Assistant API.")`
  8. `get_ha_socket_status()` (lines 703-717) — decorator: `@router_misc.get("/ha-socket", summary="Get HA Socket Status", description="Return status of the HA WebSocket connection.")` — NOTE: This uses `router_misc`, not `router`.

  **Critical details:**
  - Replace all `@router_ha.` decorators with `@router.`
  - Replace the `@router_services.get("/ha-socket"` decorator with `@router_misc.get("/ha-socket"`
  - The `get_ha_average` function has deferred imports inside the function body (`from backend.core.cache import cache`, `from backend.core.ha_client import get_load_profile_from_ha`, `from backend.core.secrets import load_yaml`). Keep these deferred imports exactly as they are — do NOT move them to the top of the file.
  - The `get_ha_socket_status` function has a deferred import (`from backend.ha_socket import get_ha_socket_status as _get_status`). Keep this exactly as-is.

## 3. Create `backend/api/routers/energy.py`

- [x] 3.1 Create the file `backend/api/routers/energy.py` with the following structure. Copy functions EXACTLY from `services.py`.

  **Imports (top of file):**
  ```python
  import logging
  from datetime import date, datetime, timedelta
  from typing import Any, cast

  from fastapi import APIRouter, Depends

  from backend.api.deps import get_learning_store
  from backend.core.secrets import load_yaml
  from backend.learning.store import LearningStore
  ```

  **Module-level variables:**
  ```python
  logger = logging.getLogger("darkstar.api.energy")

  router = APIRouter(prefix="/api", tags=["energy"])
  ```

  **Functions to copy from `services.py` (in this order):**
  1. `get_performance_data(days: int = 7)` (services.py lines 243-276) — decorator: `@router.get("/performance/data", summary="Get Performance Data", description="Get performance metrics for the Aurora card.")`
  2. `get_energy_today(store: LearningStore = Depends(get_learning_store))` (lines 411-463) — decorator: `@router.get("/energy/today", summary="Get Today's Energy", description="Get today's energy summary from database (SlotObservation table).")`
  3. `get_energy_range(period: str = "today", start_date: str | None = None, end_date: str | None = None, store: LearningStore = Depends(get_learning_store))` (lines 466-639) — decorator: `@router.get("/energy/range", summary="Get Energy Range", description="Get energy range data (today, yesterday, week, month, custom) from database.")`

  **Critical details:**
  - Replace all `@router_services.` decorators with `@router.`
  - `get_energy_today` calls `get_energy_range` directly on line 421: `range_data = await get_energy_range(period="today", store=store)`. Since both functions are in the same file, this works without changes.
  - `get_performance_data` has a deferred import: `from backend.learning import get_learning_engine`. Keep it deferred.
  - `get_energy_range` has deferred imports: `import pytz`, `from sqlalchemy import func, select`, `from backend.learning.models import SlotObservation`. Keep them deferred.
  - Do NOT import `pytz` at the top level of this file — `get_energy_range` imports it inside the function body.

## 4. Create `backend/api/routers/water.py`

- [x] 4.1 Create the file `backend/api/routers/water.py` with the following structure. Copy functions EXACTLY from `services.py`.

  **Imports (top of file):**
  ```python
  import logging
  import traceback

  from fastapi import APIRouter, HTTPException
  from pydantic import BaseModel
  ```

  **Module-level variables:**
  ```python
  logger = logging.getLogger("darkstar.api.water")

  router = APIRouter(prefix="/api/water", tags=["water"])
  ```

  **Model and functions to copy from `services.py` (in this order):**
  1. `WaterBoostRequest(BaseModel)` class (services.py lines 343-344) — Pydantic model with `duration_minutes: int = 60`
  2. `get_water_boost()` (lines 323-340) — decorator: `@router.get("/boost", summary="Get Water Boost Status", description="Get current water boost status from executor.")`
  3. `set_water_boost(req: WaterBoostRequest)` (lines 347-386) — decorator: `@router.post("/boost", summary="Set Water Boost", description="Activate water heater boost via executor quick action.")`
  4. `cancel_water_boost()` (lines 389-408) — decorator: `@router.delete("/boost", summary="Cancel Water Boost", description="Cancel active water boost.")`

  **Critical details:**
  - The route paths change from `"/water/boost"` to `"/boost"` because the router prefix is `/api/water`. The full URL `/api/water/boost` remains identical.
  - All three boost functions have deferred imports: `from backend.api.routers.executor import get_executor_instance`. Keep them deferred exactly as-is.
  - Put the `WaterBoostRequest` class BEFORE `get_water_boost` (it's used by `set_water_boost` but define it early for readability, matching the original order where the class was between get and set).

  Actually, re-checking services.py order: `get_water_boost` (323-340), then `WaterBoostRequest` (343-344), then `set_water_boost` (347-386). Keep this exact order: `get_water_boost` first, then `WaterBoostRequest`, then `set_water_boost`, then `cancel_water_boost`.

## 5. Add `simulate` endpoint to `schedule.py`

- [x] 5.1 Add the `simulate` endpoint to `backend/api/routers/schedule.py`. Insert it AFTER the `save_schedule` function (after line 521) and BEFORE the `_clean_nans` helper function (line 524). The endpoint uses the existing `router` object already defined in schedule.py.

  **Code to add (copy exactly from services.py lines 720-741):**
  ```python
  @router.post(
      "/api/simulate",
      summary="Run Simulation",
      description="Run a simulation of the current schedule.",
  )
  async def run_simulation() -> dict[str, Any]:
      """Run schedule simulation."""
      try:
          from planner.simulation import simulate_schedule  # pyright: ignore [reportMissingImports]

          with Path("data/schedule.json").open() as f:
              schedule = json.load(f)

          config = load_yaml("config.yaml")
          initial_state: dict[str, Any] = {}  # Simplified simulation

          result = simulate_schedule(schedule, config, initial_state)
          return {"status": "success", "result": cast("dict[str, Any]", result)}
      except ImportError:
          return {"status": "error", "message": "Simulation module not available"}
      except Exception as e:
          return {"status": "error", "message": str(e)}
  ```

  **Verify these imports already exist at the top of schedule.py** (they do — no new imports needed):
  - `json` — yes (line 1)
  - `Path` from `pathlib` — yes (line 5)
  - `Any, cast` from `typing` — yes (line 6)
  - `load_yaml` from `backend.core.secrets` — yes (line 15)

## 6. Update `backend/main.py` — Router Imports

- [x] 6.1 In `backend/main.py`, update the router import block (lines 20-32). Change:
  ```python
  from backend.api.routers import (
      config,
      dashboard,
      executor,
      forecast,
      learning,
      legacy,
      loads,
      schedule,
      services,
      system,
      theme,
  )
  ```
  To:
  ```python
  from backend.api.routers import (
      config,
      dashboard,
      energy,
      executor,
      forecast,
      ha,
      learning,
      legacy,
      loads,
      schedule,
      system,
      theme,
      water,
  )
  ```
  Note: `services` is removed; `energy`, `ha`, and `water` are added (alphabetical order).

- [x] 6.2 In `backend/main.py`, update the router registration (lines 258-260). Change:
  ```python
      app.include_router(config.router)
      app.include_router(services.router_ha)
      app.include_router(services.router_services)
  ```
  To:
  ```python
      app.include_router(config.router)
      app.include_router(ha.router)
      app.include_router(ha.router_misc)
      app.include_router(energy.router)
      app.include_router(water.router)
  ```
  The `services.router_ha` and `services.router_services` lines are replaced with four new lines. Keep the position (after `config.router`, before `legacy.router`).

## 7. Update `backend/api/routers/dashboard.py` — Cross-Module Call

- [x] 7.1 In `backend/api/routers/dashboard.py`, update the import on line 7. Change:
  ```python
  from backend.api.routers import config, executor, schedule, services, system
  ```
  To:
  ```python
  from backend.api.routers import config, executor, schedule, system, water
  ```
  Note: `services` is replaced with `water` (alphabetical order).

- [x] 7.2 In `backend/api/routers/dashboard.py`, update the function call on line 33. Change:
  ```python
          services.get_water_boost(),
  ```
  To:
  ```python
          water.get_water_boost(),
  ```

## 8. Delete `services.py` and Verify

- [x] 8.1 Delete the file `backend/api/routers/services.py`.

- [x] 8.2 Run `pytest tests/api/test_route_snapshot.py -v` and verify the route-preservation snapshot test still passes (all 14 routes present).

- [x] 8.3 Run the full test suite with `pytest` and verify the pass count matches baseline + 1 (the snapshot test added in Phase 1). If any tests fail, investigate and fix before proceeding.

## 9. Remove Deprecated `/api/ha/water_today` Endpoint

- [x] 9.1 In `backend/api/routers/ha.py`, delete the entire `get_water_today` function and its decorator (the block that was copied from services.py lines 279-316). This is the function decorated with `@router.get("/water_today", ...)`.

- [x] 9.2 In `tests/api/test_route_snapshot.py`, remove `"GET /api/ha/water_today"` from the expected routes set. The expected count drops from 14 to 13.

- [x] 9.3 In `frontend/src/lib/api.ts`, remove the `WaterTodayResponse` type definition (lines 140-144):
  ```typescript
  export type WaterTodayResponse = {
      source?: 'home_assistant' | 'sqlite'
      water_kwh_today?: number
      [key: string]: unknown
  }
  ```

- [x] 9.4 In `frontend/src/lib/api.ts`, remove the `haWaterToday` API method (line 561):
  ```typescript
      haWaterToday: () => getJSON<WaterTodayResponse>('/api/ha/water_today'),
  ```

- [x] 9.5 In `scripts/bench_dashboard.py`, remove the water_today entry from the `DASHBOARD_ENDPOINTS` dict (line 52):
  ```python
      "/api/ha/water_today": {"threshold_warn": 300, "threshold_error": 1000, "critical": False},
  ```

- [x] 9.6 In `scripts/verify_slow.py`, remove the water_today entry from the endpoints list (line 55):
  ```python
      ("GET", "/api/ha/water_today"),
  ```

- [x] 9.7 In `scripts/verify_arc1_routes.py`, remove the water_today entry from the routes list (line 74):
  ```python
      ("GET", "/api/ha/water_today"),
  ```

- [x] 9.8 In `tests/performance/test_dashboard_performance.py`, remove the water_today entry from the `DASHBOARD_ENDPOINTS` dict (line 38):
  ```python
      "/api/ha/water_today": {"threshold_warn": 300, "threshold_error": 1000, "critical": False},
  ```

- [x] 9.9 Run `pytest` and verify the pass count matches baseline + 1. The snapshot test should pass with 13 expected routes.

## 10. Add Endpoint Smoke Tests

- [x] 10.1 Create `tests/api/test_endpoint_smoke.py` with smoke tests for all 13 endpoints. Each test calls the endpoint with mocked dependencies and verifies the response status code is not 500 (i.e., the endpoint is reachable and doesn't crash).

  **Test file structure:**
  ```python
  """Smoke tests for all API endpoints relocated from services.py.

  Each test verifies the endpoint is reachable and returns a non-500 response
  with dependencies mocked. These are NOT functional tests — they verify
  the wiring (route registration, imports, basic error handling) is correct.
  """

  from unittest.mock import AsyncMock, MagicMock, patch

  import pytest
  from fastapi.testclient import TestClient
  ```

  **Fixture:** Use the same app-creation pattern as other API tests:
  ```python
  @pytest.fixture
  def client():
      from backend.main import create_app
      app = create_app()
      fastapi_app = app.other_asgi_app if hasattr(app, "other_asgi_app") else app
      with patch("backend.main.LearningStore", return_value=MagicMock(close=AsyncMock())):
          with TestClient(fastapi_app) as c:
              yield c
  ```

  **Tests to create (one per endpoint):**

  1. `test_smoke_ha_entity` — `GET /api/ha/entity/sensor.test` with `backend.core.ha_client.get_ha_entity_state` patched to return `{"entity_id": "sensor.test", "state": "1.0"}`. Assert status != 500.

  2. `test_smoke_ha_average` — `GET /api/ha/average?entity_id=sensor.test&hours=1` with `backend.api.routers.ha._fetch_ha_history_avg` patched to return `42.0` AND `backend.core.cache.cache` patched (its `get` returns `None` async, its `set` is a no-op async). Assert status != 500.

  3. `test_smoke_ha_entities` — `GET /api/ha/entities` with `backend.core.secrets.load_home_assistant_config` patched to return `{"url": "http://test:8123", "token": "test"}` AND `httpx.AsyncClient` patched so the GET returns a 200 response with JSON `[{"entity_id": "sensor.test", "attributes": {"friendly_name": "Test"}}]`. Assert status != 500.

  4. `test_smoke_ha_services` — `GET /api/ha/services` with same HA config mock and `httpx.AsyncClient` patched to return 200 with JSON `[{"domain": "light", "services": {"turn_on": {}}}]`. Assert status != 500.

  5. `test_smoke_ha_test` — `POST /api/ha/test` with same HA config mock and `httpx.AsyncClient` patched to return 200. Assert status != 500.

  6. `test_smoke_water_boost_get` — `GET /api/water/boost` with `backend.api.routers.executor.get_executor_instance` patched to return `None`. Assert status != 500.

  7. `test_smoke_water_boost_set` — `POST /api/water/boost` with JSON body `{"duration_minutes": 30}` and `backend.api.routers.executor.get_executor_instance` patched to return `None`. Assert status code is 503 (executor unavailable) which is the expected behavior, NOT 500.

  8. `test_smoke_water_boost_delete` — `DELETE /api/water/boost` with `backend.api.routers.executor.get_executor_instance` patched to return `None`. Assert status != 500.

  9. `test_smoke_energy_today` — `GET /api/energy/today`. The conftest autouse fixture already mocks the learning engine. The `get_learning_store` dependency returns a mock store whose `AsyncSession()` context manager yields a mock session. The mock session's `execute` returns a mock result whose `fetchone()` returns `None`. The endpoint's exception handler catches this and returns a fallback dict. Assert status == 200.

  10. `test_smoke_energy_range` — `GET /api/energy/range?period=today`. Same as above — conftest handles mocking. Assert status == 200.

  11. `test_smoke_performance_data` — `GET /api/performance/data`. The conftest mocks `get_learning_engine`. Assert status == 200.

  12. `test_smoke_ha_socket` — `GET /api/ha-socket` with `backend.ha_socket.get_ha_socket_status` patched to return `{"status": "connected"}`. Assert status != 500.

  13. `test_smoke_simulate` — `POST /api/simulate` with `planner.simulation.simulate_schedule` patched to raise `ImportError`. Assert status == 200 and response body contains `{"status": "error", "message": "Simulation module not available"}`.

  **Critical details:**
  - The conftest.py autouse fixture `prevent_real_learning_engine` handles most mocking for energy/performance endpoints. Tests 9-11 should work without additional patches.
  - For HA endpoints (tests 1-5), you need to mock the external HTTP calls. The simplest approach is to mock `httpx.AsyncClient` as a context manager or patch the specific functions.
  - For test 2 (ha_average), patching `backend.api.routers.ha._fetch_ha_history_avg` directly is simpler than mocking all the httpx internals.
  - Each test should be independent and not depend on other tests.

- [x] 10.2 Run `pytest tests/api/test_endpoint_smoke.py -v` and verify all 13 smoke tests pass.

- [x] 10.3 Run the full test suite with `pytest` and verify the total pass count is baseline + 1 (snapshot) + 13 (smoke) = baseline + 14.

## 11. Final Verification

- [x] 11.1 Run `./scripts/lint.sh` and fix any linting errors.

- [x] 11.2 Verify no imports of `backend.api.routers.services` remain anywhere in the codebase. Run: `grep -r "backend.api.routers.services\|backend\.api\.routers import.*services\|from backend.api.routers import.*services" --include="*.py" .` — should return zero results.

- [x] 11.3 Verify `backend/api/routers/services.py` does not exist.

- [x] 11.4 Run the full test suite one final time with `pytest -v` and confirm all tests pass with the expected count (baseline + 14).
