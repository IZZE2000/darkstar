## Why

`inputs.py` is a 1493-line monolith at the project root containing four unrelated responsibilities: config/secrets loading, Home Assistant client, Nordpool price fetching, and forecast orchestration. Its root-level placement breaks project conventions (all other Python modules live under `backend/`, `ml/`, `executor/`, `planner/`) and confuses AI tooling and developers who expect it under `backend/`. 27 files across the codebase import from it. Splitting and relocating it into `backend/core/` improves discoverability, enforces separation of concerns, and aligns with the existing module structure.

## What Changes

- **Split** `inputs.py` (1493 LOC) into 4 focused modules under `backend/core/`:
  - `backend/core/secrets.py` — YAML config/secrets loading (`load_yaml`, `load_home_assistant_config`, `load_notifications_config`)
  - `backend/core/ha_client.py` — Home Assistant HTTP sensor access (`get_ha_entity_state`, `get_ha_sensor_float`, `get_ha_sensor_kw_normalized`, `get_ha_bool`, `make_ha_headers`, `get_load_profile_from_ha`, `get_initial_state`, `get_dummy_load_profile`)
  - `backend/core/prices.py` — Nordpool electricity price fetching (`get_nordpool_data`, `calculate_import_export_prices`, `get_current_slot_prices`)
  - `backend/core/forecasts.py` — PV/load forecast orchestration (`get_forecast_data`, `get_all_input_data`, `build_db_forecast_for_slots`, `get_db_forecast_slots`)
- **Replace** `inputs.py` at project root with a thin **backwards-compatibility re-export shim** that imports all public symbols from the 4 new modules and re-exports them. This ensures zero breakage during transition.
- **Update** all 27 importing files to use the new `backend.core.*` import paths.
- **Remove** the re-export shim once all imports are migrated.
- **Update** `tests/conftest.py` which patches `inputs.load_yaml` to patch the new canonical location.

## Capabilities

### New Capabilities

- `input-module-structure`: Defines the module split layout, public API surface of each new module, and the re-export shim contract for backwards compatibility.

### Modified Capabilities

_(No existing spec-level behavior changes — this is a pure refactoring. All public function signatures remain identical.)_

## Impact

- **27 files** across `backend/`, `executor/`, `ml/`, `bin/`, `scripts/`, `tests/` need import path updates
- **`tests/conftest.py`** patches `inputs.load_yaml` — needs to patch `backend.core.secrets.load_yaml` instead
- **Test files** that use `from inputs import ...` inside test functions need updating
- **No API changes** — all HTTP endpoints, WebSocket behavior, and function signatures remain identical
- **No dependency changes** — no new packages required
- **Risk**: High regression potential due to breadth of import changes. Mitigated by re-export shim and comprehensive test verification.
