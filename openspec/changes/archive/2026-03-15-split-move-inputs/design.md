## Context

`inputs.py` is a 1493-line file at the project root that has grown organically to contain four unrelated responsibilities. It is the most-imported module in the project (27 files depend on it) and its root-level placement conflicts with the existing package structure where all Python modules live under `backend/`, `ml/`, `executor/`, or `planner/`.

The file already imports from `backend.core.cache` and `backend.exceptions`, creating a circular dependency pattern (root imports from backend, backend imports from root). The `backend/core/` package already exists with `cache.py`, `logging.py`, and `websockets.py`.

Current function groups in `inputs.py`:

| Group | Functions | LOC (approx) | Dependencies |
|-------|-----------|------|------|
| Secrets/Config | `load_yaml`, `load_home_assistant_config`, `load_notifications_config` | ~60 | `yaml`, `pathlib` |
| HA Client | `make_ha_headers`, `get_ha_entity_state`, `get_ha_sensor_float`, `get_ha_sensor_kw_normalized`, `_normalize_energy_to_kwh`, `get_ha_bool`, `get_load_profile_from_ha`, `get_initial_state`, `get_dummy_load_profile` | ~500 | `httpx`, secrets group |
| Prices | `get_nordpool_data`, `calculate_import_export_prices`, `_process_nordpool_data`, `get_current_slot_prices` | ~180 | `nordpool`, `backend.core.cache`, secrets group |
| Forecasts | `_interpolate_small_gaps`, `_get_forecast_data_aurora`, `_get_forecast_data_async`, `get_forecast_data`, `get_all_input_data`, `get_db_forecast_slots`, `build_db_forecast_for_slots` | ~750 | `open_meteo_solar_forecast`, `ml.api`, `ml.weather`, HA client group, prices group, secrets group |

**Critical cross-references within inputs.py:**
- HA Client → Secrets (calls `load_home_assistant_config`, `make_ha_headers`)
- HA Client → uses `load_yaml` for config access
- Prices → Secrets (calls `load_yaml` for config)
- Forecasts → HA Client (calls `get_ha_entity_state`, `get_ha_sensor_float`, `load_home_assistant_config`, `make_ha_headers`)
- Forecasts → Prices (calls `get_nordpool_data`)
- Forecasts → Secrets (calls `load_yaml`)
- `get_all_input_data` is the "main" orchestrator that calls across all groups

**Test infrastructure constraint:** `tests/conftest.py` does `import inputs` and patches `inputs.load_yaml` with `patch.object(inputs, "load_yaml", mock_load_yaml)`. This is a session-scoped fixture that affects all tests.

## Goals / Non-Goals

**Goals:**
- Split `inputs.py` into 4 focused modules under `backend/core/`
- Maintain identical public API (same function names, same signatures, same behavior)
- Update all 27 importing files to use new import paths
- Ensure zero test regressions
- Provide a safe, verifiable migration path

**Non-Goals:**
- Renaming any functions or changing any signatures
- Changing any business logic or behavior
- Adding new functionality
- Changing the `backend/core/` package structure beyond adding 4 new files
- Splitting further into sub-packages (this split is sufficient)

## Decisions

### Decision 1: Module layout — 4 files in `backend/core/`

**Choice:** Create `secrets.py`, `ha_client.py`, `prices.py`, `forecasts.py` in `backend/core/`.

**Alternatives considered:**
- *Single file move* (`inputs.py` → `backend/core/inputs.py`): Moves the problem, doesn't solve it. Still a 1500-line god file.
- *Deeper package structure* (`backend/core/inputs/secrets.py` etc.): Over-engineering for 4 files.
- *Separate packages* (`backend/ha/`, `backend/prices/`): Creates unnecessary package proliferation.

**Rationale:** `backend/core/` already exists with utility modules. Four new files keeps it flat and discoverable. Each file has a clear single responsibility.

### Decision 2: No backwards-compatibility shim — direct migration

**Choice:** Update all 27 files directly to use new import paths. Do NOT leave a re-export shim at `inputs.py`.

**Alternatives considered:**
- *Re-export shim*: Keep `inputs.py` as a thin re-export file during transition. Adds a step, and since we control all consumers and have tests, it's unnecessary complexity.

**Rationale:** All 27 importing files are in this repo. We can update them all atomically in one commit. The re-export shim would just be tech debt to clean up later. The test suite validates everything works.

### Decision 3: Import dependency order between new modules

```
backend/core/secrets.py        (standalone — no intra-core imports)
       ↑
backend/core/ha_client.py      (imports from secrets)
       ↑
backend/core/prices.py         (imports from secrets, uses backend.core.cache)
       ↑
backend/core/forecasts.py      (imports from secrets, ha_client, prices)
```

Each module imports from the ones above it. No circular dependencies.

### Decision 4: `conftest.py` patching strategy

**Choice:** Update `conftest.py` to import and patch `backend.core.secrets` instead of `inputs`. Since the session-scoped fixture patches `load_yaml`, the patch target must be `backend.core.secrets.load_yaml` — the canonical location where the function is defined.

**Critical detail:** Test files that do `from inputs import get_nordpool_data` inside test functions (lazy imports) must be updated to `from backend.core.prices import get_nordpool_data`. The mock for `load_yaml` must target `backend.core.secrets` because that's where the function is defined, but consumers that call `load_yaml()` in other modules import it — so the patch must also cover the import sites OR use `backend.core.secrets.load_yaml` as the single source of truth that all modules call.

**Approach:** All new modules will call `from backend.core.secrets import load_yaml` and use it directly. The conftest patch must patch `backend.core.secrets.load_yaml` AND also ensure each new module sees the mock. The simplest approach: patch `backend.core.secrets.load_yaml` with `patch.object()` — since all other modules import the function object by reference at call time (not at import time via `from ... import`), we need to verify this. If modules use `from backend.core.secrets import load_yaml` (binding at import time), the patch must target each consumer module's binding. The safest approach is to have modules call `secrets.load_yaml()` (module-level reference) rather than importing the function directly.

**Final decision:** New modules will use `from backend.core import secrets` and call `secrets.load_yaml()` (attribute access on the module). This way, patching `backend.core.secrets.load_yaml` with `patch.object` propagates to all callers automatically.

### Decision 5: Verification strategy

**Choice:** Three-layer verification:

1. **Pre-refactor baseline**: Run full test suite, record pass count and results
2. **Post-refactor validation**: Run full test suite, compare against baseline — must be identical
3. **Import verification script**: A one-off script that verifies no remaining `from inputs import` lines exist anywhere in the codebase (except the script itself)

This is a pure refactoring — if all tests pass before and after, the change is correct.

## Risks / Trade-offs

**[Risk: Stale import caching in `__pycache__`]** → Mitigation: Task includes clearing `__pycache__` directories before running verification tests.

**[Risk: Lazy imports inside functions]** → Several files use lazy imports (`from inputs import ...` inside function bodies, e.g., `executor/engine.py:1678`, `backend/api/routers/executor.py:614`). These are easy to miss. → Mitigation: Task includes explicit grep verification that no `from inputs import` or `import inputs` remains.

**[Risk: Patch target mismatch in tests]** → If `conftest.py` patches the wrong module after refactor, all tests could silently use real config. → Mitigation: Specific task to update conftest.py and verify the mock is effective by checking test behavior.

**[Risk: `__init__.py` re-exports needed]** → `backend/core/__init__.py` doesn't exist yet. → Mitigation: Not needed — all imports will use full paths (`from backend.core.secrets import ...`). No `__init__.py` changes required since `backend/core/` already has `cache.py` etc. working without one. Actually, need to verify if `__init__.py` exists.

**[Risk: Module-level side effects]** → `inputs.py` has module-level code: `logger = logging.getLogger("darkstar.inputs")`. Each new module should have its own logger namespace. → Mitigation: Each file gets its own logger (`darkstar.core.secrets`, `darkstar.core.ha_client`, etc.).

**[Trade-off: Larger diff]** → Touching 27+ files in one change is a big diff. Accepted because: (a) changes are mechanical (import path updates), (b) full test suite validates, (c) atomic commit means no intermediate broken state.
