## 1. Pre-Refactor Baseline

- [x] 1.1 Clear all `__pycache__` directories: run `find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null` from the project root to prevent stale bytecode from masking import errors.

- [x] 1.2 Run the full test suite and record the baseline: run `python -m pytest tests/ -v --tb=short 2>&1 | tee /tmp/darkstar-baseline.txt`. Record the total pass/fail/skip counts from the last line. This baseline will be compared against after migration.

## 2. Create `backend/core/secrets.py`

This is the dependency root — no other `backend.core` module depends on it, but all three other new modules will import from it.

- [x] 2.1 Create the file `backend/core/secrets.py`. Copy the following functions from `inputs.py` **exactly as-is** (no signature or logic changes):
  - `load_yaml` (lines 70–77 of `inputs.py`)
  - `load_home_assistant_config` (lines 22–39)
  - `load_notifications_config` (lines 42–67)

  At the top of the new file, add these imports (copied from `inputs.py`'s existing imports, only the ones these functions need):
  ```python
  import logging
  from pathlib import Path
  from typing import Any, cast

  import yaml

  logger = logging.getLogger("darkstar.core.secrets")
  ```

  **Verify:** The file should contain exactly 3 public functions and no imports from `backend.core`.

## 3. Create `backend/core/ha_client.py`

This module depends on `backend.core.secrets` only.

- [x] 3.1 Create the file `backend/core/ha_client.py`. Copy the following functions from `inputs.py` **exactly as-is**:
  - `make_ha_headers` (lines 62–67)
  - `get_ha_entity_state` (lines 79–101) — this function currently calls `load_home_assistant_config()` and `make_ha_headers()` — these will now be reached via `secrets.load_home_assistant_config()` and the local `make_ha_headers()`.
  - `get_ha_sensor_float` (lines 103–117) — calls `get_ha_entity_state()` (local)
  - `_normalize_energy_to_kwh` (lines 141–167) — private helper
  - `get_ha_sensor_kw_normalized` (lines 119–139) — calls `get_ha_entity_state()` and `_normalize_energy_to_kwh()` (both local)
  - `get_ha_bool` (lines 170–183) — calls `get_ha_entity_state()` (local)
  - `get_load_profile_from_ha` (lines 1147–1303) — calls `secrets.load_home_assistant_config()`, `make_ha_headers()`, and `secrets.load_yaml()`
  - `get_initial_state` (lines 854–957) — calls `get_ha_entity_state()`, `get_ha_sensor_float()` (both local), and `secrets.load_yaml()`
  - `get_dummy_load_profile` (lines 1306–1493) — calls `secrets.load_yaml()` only for config access

  At the top of the new file, add these imports:
  ```python
  import asyncio
  import logging
  from datetime import datetime, timedelta
  from typing import Any

  import httpx
  import pytz

  from backend.core import secrets

  logger = logging.getLogger("darkstar.core.ha_client")
  ```

  **Critical:** Every call to `load_home_assistant_config()`, `load_notifications_config()`, or `load_yaml()` that previously called the local function in `inputs.py` must now call `secrets.load_home_assistant_config()`, `secrets.load_notifications_config()`, or `secrets.load_yaml()` respectively — using **attribute access on the `secrets` module**, NOT a direct import of the function. This is required so that `patch.object` in tests propagates correctly.

  Calls to functions that are local to this same file (e.g., `get_ha_entity_state`, `make_ha_headers`, `_normalize_energy_to_kwh`) stay as direct calls — no module prefix needed.

  **Verify:** The file should contain 7 public functions + 1 private helper. The only `backend.core` import should be `from backend.core import secrets`.

## 4. Create `backend/core/prices.py`

This module depends on `backend.core.secrets` only.

- [x] 4.1 Create the file `backend/core/prices.py`. Copy the following functions from `inputs.py` **exactly as-is**:
  - `get_nordpool_data` (lines 185–278) — calls `secrets.load_yaml()`, `calculate_import_export_prices()` (local), `_process_nordpool_data()` (local), and uses `cache_sync` from `backend.core.cache`
  - `calculate_import_export_prices` (lines 280–306)
  - `_process_nordpool_data` (lines 308–362)
  - `get_current_slot_prices` (lines 364–387) — calls `get_nordpool_data()` (local)

  At the top of the new file, add these imports:
  ```python
  import logging
  from datetime import datetime, timedelta
  from typing import Any

  import pytz
  from nordpool.elspot import Prices

  from backend.core import secrets
  from backend.core.cache import cache_sync

  logger = logging.getLogger("darkstar.core.prices")
  ```

  **Critical:** Every call to `load_yaml()` must become `secrets.load_yaml()`.

  **Verify:** The file should contain 3 public functions + 1 private helper. Imports: `from backend.core import secrets` and `from backend.core.cache import cache_sync`.

## 5. Create `backend/core/forecasts.py`

This module depends on `backend.core.secrets`, `backend.core.ha_client`, and `backend.core.prices`.

- [x] 5.1 Create the file `backend/core/forecasts.py`. Copy the following functions from `inputs.py` **exactly as-is**:
  - `_interpolate_small_gaps` (lines 404–474)
  - `_get_forecast_data_aurora` (lines 476–638) — calls `secrets.load_home_assistant_config()`, `ha_client.make_ha_headers()`, and `secrets.load_yaml()`
  - `_get_forecast_data_async` (lines 640–852) — calls `secrets.load_yaml()`, uses `OpenMeteoSolarForecast`
  - `get_forecast_data` (lines 389–402) — dispatcher that calls `_get_forecast_data_aurora()` or `_get_forecast_data_async()` (both local)
  - `get_all_input_data` (lines 959–1031) — calls `secrets.load_yaml()`, `prices.get_nordpool_data()`, local `get_forecast_data()`, `ha_client.get_load_profile_from_ha()`, `ha_client.get_initial_state()`
  - `get_db_forecast_slots` (lines 1033–1050)
  - `build_db_forecast_for_slots` (lines 1052–1145) — calls `secrets.load_yaml()`, local `get_forecast_data()`

  At the top of the new file, add these imports:
  ```python
  import asyncio
  import logging
  from datetime import datetime, timedelta
  from pathlib import Path
  from typing import Any, cast

  import httpx
  import pytz
  from open_meteo_solar_forecast import OpenMeteoSolarForecast

  from backend.core import ha_client, prices, secrets
  from backend.exceptions import PVForecastError
  from backend.health import set_load_forecast_status
  from ml.api import get_forecast_slots
  from ml.weather import async_get_weather_volatility

  logger = logging.getLogger("darkstar.core.forecasts")
  ```

  **Critical:** Every call to a function from another group must use the module prefix:
  - `load_yaml()` → `secrets.load_yaml()`
  - `load_home_assistant_config()` → `secrets.load_home_assistant_config()`
  - `make_ha_headers()` → `ha_client.make_ha_headers()`
  - `get_nordpool_data()` → `prices.get_nordpool_data()`
  - `get_load_profile_from_ha()` → `ha_client.get_load_profile_from_ha()`
  - `get_initial_state()` → `ha_client.get_initial_state()`

  Calls to functions local to this file (`get_forecast_data`, `_get_forecast_data_aurora`, `_get_forecast_data_async`, `_interpolate_small_gaps`) remain as direct calls.

  **Verify:** The file should contain 4 public functions + 3 private helpers.

## 6. Update Backend Imports (11 files)

Each task below specifies the exact file, line number, old import, and new import. **Do not change anything else in these files.**

- [x] 6.1 **`backend/api/routers/analyst.py` line 12**: Change `from inputs import load_yaml` → `from backend.core.secrets import load_yaml`

- [x] 6.2 **`backend/api/routers/config.py` line 15**: Change `from inputs import load_home_assistant_config, load_notifications_config, load_yaml` → Split into two imports:
  ```python
  from backend.core.secrets import load_home_assistant_config, load_notifications_config, load_yaml
  ```
  (All three come from `secrets`.)

- [x] 6.3 **`backend/api/routers/debug.py` line 18**: Change `from inputs import get_dummy_load_profile, get_load_profile_from_ha, load_yaml` → Split into two imports:
  ```python
  from backend.core.ha_client import get_dummy_load_profile, get_load_profile_from_ha
  from backend.core.secrets import load_yaml
  ```

- [x] 6.4 **`backend/api/routers/executor.py` line 614** (lazy import inside function): Change `from inputs import load_yaml` → `from backend.core.secrets import load_yaml`

- [x] 6.5 **`backend/api/routers/forecast.py` line 18**: Change `from inputs import get_nordpool_data, load_yaml` → Split into two imports:
  ```python
  from backend.core.prices import get_nordpool_data
  from backend.core.secrets import load_yaml
  ```

- [x] 6.6 **`backend/api/routers/schedule.py` line 15**: Change `from inputs import get_nordpool_data, load_yaml` → Split into two imports:
  ```python
  from backend.core.prices import get_nordpool_data
  from backend.core.secrets import load_yaml
  ```

- [x] 6.7 **`backend/api/routers/services.py`** — TWO import sites:
  - **Line 15–20** (top-level multi-line import): Change:
    ```python
    from inputs import (
        get_ha_entity_state,
        load_home_assistant_config,
        load_yaml,
        make_ha_headers,
    )
    ```
    → Split into:
    ```python
    from backend.core.ha_client import get_ha_entity_state, make_ha_headers
    from backend.core.secrets import load_home_assistant_config, load_yaml
    ```
  - **Line 137** (lazy import inside `get_ha_average` function): Change `from inputs import get_load_profile_from_ha, load_yaml` → `from backend.core.ha_client import get_load_profile_from_ha` and `from backend.core.secrets import load_yaml` (two separate lazy imports, OR combine if preferred: keep on two lines for clarity).

- [x] 6.8 **`backend/api/routers/system.py` lines 19–24** (multi-line import): Change:
  ```python
  from inputs import (
      get_ha_bool,
      get_ha_sensor_float,
      get_ha_sensor_kw_normalized,
      load_yaml,
  )
  ```
  → Split into:
  ```python
  from backend.core.ha_client import get_ha_bool, get_ha_sensor_float, get_ha_sensor_kw_normalized
  from backend.core.secrets import load_yaml
  ```

- [x] 6.9 **`backend/ha_socket.py` line 10**: Change `from inputs import load_home_assistant_config, load_yaml` → `from backend.core.secrets import load_home_assistant_config, load_yaml` (both come from secrets)

- [x] 6.10 **`backend/loads/service.py` line 6**: Change `from inputs import get_ha_sensor_kw_normalized` → `from backend.core.ha_client import get_ha_sensor_kw_normalized`

- [x] 6.11 **`backend/main.py` line 44**: Change `from inputs import load_yaml` → `from backend.core.secrets import load_yaml`

- [x] 6.12 **`backend/recorder.py`** — TWO import sites:
  - **Lines 19–25** (top-level multi-line import): Change:
    ```python
    from inputs import (
        _normalize_energy_to_kwh,  # pyright: ignore[reportPrivateUsage]
        get_current_slot_prices,
        get_ha_entity_state,
        get_ha_sensor_float,
        get_ha_sensor_kw_normalized,
    )
    ```
    → Split into:
    ```python
    from backend.core.ha_client import (
        _normalize_energy_to_kwh,  # pyright: ignore[reportPrivateUsage]
        get_ha_entity_state,
        get_ha_sensor_float,
        get_ha_sensor_kw_normalized,
    )
    from backend.core.prices import get_current_slot_prices
    ```
  - **Line 533** (lazy import inside function): Change `from inputs import get_nordpool_data` → `from backend.core.prices import get_nordpool_data`

## 7. Update Executor & Planner Imports (2 files)

- [x] 7.1 **`executor/engine.py` line 37**: Change `from inputs import load_home_assistant_config` → `from backend.core.secrets import load_home_assistant_config`

- [x] 7.2 **`executor/engine.py` line 1678** (lazy import inside function): Change `from inputs import get_nordpool_data` → `from backend.core.prices import get_nordpool_data`

- [x] 7.3 **`bin/run_planner.py` line 13**: Change `from inputs import get_all_input_data` → `from backend.core.forecasts import get_all_input_data`

## 8. Update ML Imports (2 files)

- [x] 8.1 **`ml/context_features.py` line 16**: Change `from inputs import load_home_assistant_config, make_ha_headers` → Split:
  ```python
  from backend.core.ha_client import make_ha_headers
  from backend.core.secrets import load_home_assistant_config
  ```

- [x] 8.2 **`ml/data_activator.py` line 15**: Change `from inputs import load_home_assistant_config, make_ha_headers` → Split:
  ```python
  from backend.core.ha_client import make_ha_headers
  from backend.core.secrets import load_home_assistant_config
  ```

## 9. Update Script Imports (3 files)

- [x] 9.1 **`scripts/df_inspect.py` line 20**: Change `from inputs import load_yaml` → `from backend.core.secrets import load_yaml`

- [x] 9.2 **`scripts/profile_deep.py`** — THREE lazy imports:
  - **Line 79**: Change `from inputs import get_nordpool_data` → `from backend.core.prices import get_nordpool_data`
  - **Line 87**: Change `from inputs import get_forecast_data` → `from backend.core.forecasts import get_forecast_data`
  - **Line 95**: Change `from inputs import get_initial_state` → `from backend.core.ha_client import get_initial_state`

- [x] 9.3 **`scripts/verify_k15.py` line 12**: Change `from inputs import get_all_input_data` → `from backend.core.forecasts import get_all_input_data`

- [x] 9.4 **`bin/inspect_episodes.py` line 30** (lazy import): Change `from inputs import load_yaml` → `from backend.core.secrets import load_yaml`

## 10. Update Test Imports (5 files)

- [x] 10.1 **`tests/conftest.py`** — This is the most critical test file. Replace the entire file content with:
  ```python
  from pathlib import Path
  from unittest.mock import patch

  import pytest

  from backend.core import secrets


  @pytest.fixture(scope="session", autouse=True)
  def setup_test_env():
      """Set up a clean test environment with mocked config for CI."""
      data_dir = Path("data")
      data_dir.mkdir(exist_ok=True)

      db_path = data_dir / "test_planner.db"

      test_config = {
          "version": "2.5.1-beta",
          "timezone": "Europe/Stockholm",
          "learning": {
              "enable": True,
              "sqlite_path": "data/test_planner.db",
              "horizon_days": 2,
          },
          "forecasting": {
              "active_forecast_version": "aurora",
          },
          "input_sensors": {
              "battery_soc": "sensor.test_soc",
          },
      }

      original_load_yaml = secrets.load_yaml

      def mock_load_yaml(path: str) -> dict:
          if path == "config.yaml":
              return test_config
          return original_load_yaml(path)

      with patch.object(secrets, "load_yaml", mock_load_yaml):
          yield

      try:
          if db_path.exists():
              db_path.unlink()
      except Exception:
          pass
  ```

  **Why this works:** All new modules access `load_yaml` via `secrets.load_yaml()` (attribute access). When `patch.object(secrets, "load_yaml", mock_load_yaml)` is active, all attribute lookups on the `secrets` module will find the mock. This is exactly the same pattern as before, just targeting the new canonical location.

- [x] 10.2 **`tests/test_inputs_ha_client.py`** — FOUR lazy imports inside test functions:
  - **Line 27**: Change `from inputs import get_initial_state` → `from backend.core.ha_client import get_initial_state`
  - **Line 84**: Change `from inputs import get_ha_entity_state` → `from backend.core.ha_client import get_ha_entity_state`
  - **Line 120**: Change `from inputs import get_ha_entity_state` → `from backend.core.ha_client import get_ha_entity_state`
  - **Line 148**: Change `from inputs import get_load_profile_from_ha` → `from backend.core.ha_client import get_load_profile_from_ha`

- [x] 10.3 **`tests/test_nordpool_timeout.py`** — FOUR lazy imports:
  - **Line 42**: Change `from inputs import get_nordpool_data` → `from backend.core.prices import get_nordpool_data`
  - **Line 72**: Change `from inputs import get_nordpool_data` → `from backend.core.prices import get_nordpool_data`
  - **Line 115**: Change `from inputs import get_nordpool_data` → `from backend.core.prices import get_nordpool_data`
  - **Line 160**: Change `from inputs import get_nordpool_data` → `from backend.core.prices import get_nordpool_data`

- [x] 10.4 **`tests/ml/test_forecast_aggregation.py`** — TWO lines:
  - **Line 5**: Change the comment `# We import inputs normally. We will patch OpenMeteoSolarForecast where it is USED.` → `# We import from forecasts module. We will patch OpenMeteoSolarForecast where it is USED.`
  - **Line 6**: Change `from inputs import _get_forecast_data_async` → `from backend.core.forecasts import _get_forecast_data_async`

- [x] 10.5 **`tests/executor/test_normalization.py` line 12**: Change `from inputs import get_ha_sensor_kw_normalized` → `from backend.core.ha_client import get_ha_sensor_kw_normalized`

- [x] 10.6 **`tests/ev/test_ev_charging_replan.py` line 229** (lazy import): Change `from inputs import get_initial_state` → `from backend.core.ha_client import get_initial_state`

- [x] 10.7 **`tests/manual/repro_nordpool_cache.py` line 12**: Change `from inputs import get_nordpool_data` → `from backend.core.prices import get_nordpool_data`

## 11. Update Test Patch Targets

After changing imports, some tests may use `patch("inputs.some_function")` as a string target. These must also be updated.

- [x] 11.1 Search the entire `tests/` directory for any string containing `"inputs.` (with quotes) that is used as a patch target: run `grep -rn '"inputs\.' tests/ --include="*.py"`. For each match, update the patch target string from `"inputs.X"` to the correct new module path (e.g., `"backend.core.ha_client.get_ha_entity_state"`). **Important:** The patch target for a function must match **the module where the function is looked up at call time**. If a test patches `"inputs.get_ha_entity_state"` and the test's code-under-test does `from backend.core.ha_client import get_ha_entity_state`, then the patch target should be the module of the code-under-test (e.g., `"backend.api.routers.services.get_ha_entity_state"`) OR `"backend.core.ha_client.get_ha_entity_state"` if the test imports it directly. Review each case carefully.

- [x] 11.2 Also search for `patch.object(inputs,` patterns: run `grep -rn 'patch.object(inputs' tests/ --include="*.py"`. Update these to `patch.object(secrets_module,` or the appropriate new module. (Note: `conftest.py` was already handled in task 10.1.)

## 12. Delete Root `inputs.py`

- [x] 12.1 Delete the file `inputs.py` from the project root. Run `rm inputs.py`.

## 13. Update Documentation

- [x] 13.1 **`docs/DEVELOPER.md` line 252**: Replace the `inputs.py` line in the project structure tree. Change:
  ```
  ├── inputs.py           # Data ingestion (HA, Nordpool, Aurora)
  ```
  → Remove that line entirely. Instead, ensure the `backend/` tree section (if present) or the `backend/core/` listing reflects the new modules. If the `backend/core/` subtree is not shown, add it near the existing backend section:
  ```
  ├── backend/
  │   ├── core/
  │   │   ├── secrets.py    # Config/secrets loading (YAML, HA config)
  │   │   ├── ha_client.py  # Home Assistant HTTP sensor access
  │   │   ├── prices.py     # Nordpool electricity price fetching
  │   │   ├── forecasts.py  # PV/load forecast orchestration
  │   │   ├── cache.py      # TTL cache (async/sync)
  │   │   ├── logging.py    # Logging utilities
  │   │   └── websockets.py # WebSocket manager
  ```

- [x] 13.2 **`docs/ARCHITECTURE.md` lines 593–608** (Section 9, Backend API Architecture): The `backend/` package structure listing currently shows:
  ```
  backend/
  ├── core/
  │   └── websockets.py
  ```
  Update it to also show the new modules:
  ```
  backend/
  ├── core/
  │   ├── secrets.py        # Config/secrets loading
  │   ├── ha_client.py      # Home Assistant HTTP client
  │   ├── prices.py         # Nordpool price fetching
  │   ├── forecasts.py      # PV/load forecast orchestration
  │   ├── cache.py          # TTL cache
  │   └── websockets.py     # AsyncServer singleton, sync→async bridge
  ```

- [x] 13.3 **`docs/BACKLOG.md`**: Remove or mark as completed the following items:
  - The `[Refactor] Move inputs.py to Proper Module` section (lines ~125–147) — delete it entirely since it's now done.
  - Update the `Inverter Clipping Support` Phase 3 bullet (line 56) that references `inputs.py`: change `Update inputs.py to optionally clip forecasts early` → `Update backend/core/forecasts.py to optionally clip forecasts early`.
  - Update the `Split services.py Router` item (line ~217) that mentions `Config loading helpers → reuse from inputs.py` → `Config loading helpers → reuse from backend.core.secrets`.

## 14. Post-Refactor Verification

- [x] 14.1 Clear all `__pycache__` directories again: `find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null`

- [x] 14.2 Run a comprehensive grep to verify no remaining legacy imports: `grep -rn "from inputs import\|import inputs" --include="*.py" .` — this MUST return zero results. If any results are found, go back and fix them before proceeding.

- [x] 14.3 Run the full test suite: `python -m pytest tests/ -v --tb=short 2>&1 | tee /tmp/darkstar-postrefactor.txt`. Compare the pass/fail/skip counts against the baseline from task 1.2. The counts MUST be identical. If any test fails that passed in the baseline, investigate and fix before proceeding.

- [x] 14.4 Verify each new module is importable independently: run these Python commands and confirm no errors:
  ```bash
  python -c "from backend.core.secrets import load_yaml, load_home_assistant_config, load_notifications_config; print('secrets OK')"
  python -c "from backend.core.ha_client import get_ha_entity_state, get_ha_sensor_float, get_ha_sensor_kw_normalized, get_ha_bool, make_ha_headers, get_load_profile_from_ha, get_initial_state, get_dummy_load_profile; print('ha_client OK')"
  python -c "from backend.core.prices import get_nordpool_data, calculate_import_export_prices, get_current_slot_prices; print('prices OK')"
  python -c "from backend.core.forecasts import get_forecast_data, get_all_input_data, get_db_forecast_slots, build_db_forecast_for_slots; print('forecasts OK')"
  ```

- [x] 14.5 Verify the new module files exist and `inputs.py` is gone:
  ```bash
  test -f backend/core/secrets.py && echo "secrets.py exists" || echo "MISSING: secrets.py"
  test -f backend/core/ha_client.py && echo "ha_client.py exists" || echo "MISSING: ha_client.py"
  test -f backend/core/prices.py && echo "prices.py exists" || echo "MISSING: prices.py"
  test -f backend/core/forecasts.py && echo "forecasts.py exists" || echo "MISSING: forecasts.py"
  test ! -f inputs.py && echo "inputs.py removed" || echo "ERROR: inputs.py still exists"
  ```
