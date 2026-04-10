## Why

`regions.json` is a static application file (SE1-SE4 weather coordinates) that was placed in the `data/` directory, which is the user-data mount point. This causes a critical runtime regression: the Dockerfile's `COPY data/regions.json ./data/regions.json` pre-creates `/app/data/` as a real directory, which prevents `run.sh`'s `ln -sf /share/darkstar /app/data` symlink from working. The app then silently connects to a fresh empty database instead of the persistent user database, causing "no such table" errors on every executor tick.

## What Changes

- Move `data/regions.json` → `ml/regions.json` (static app file belongs with the ML code that uses it, not in user-data storage)
- Update all three Dockerfiles to copy from/to the new path
- Remove the `.dockerignore` exception `!data/regions.json` (no longer needed)
- Update the two default path parameters in `ml/weather.py`
- Update test path references in `tests/ml/test_regions_loader.py`
- Update the `regional-weather-coordinates` spec to reflect the correct file location

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `regional-weather-coordinates`: The required file path changes from `data/regions.json` to `ml/regions.json`. The spec currently mandates the old path.

## Impact

- **Dockerfiles** (`Dockerfile`, `darkstar/Dockerfile`, `darkstar-dev/Dockerfile`): COPY path updated
- **`.dockerignore`**: Exception line removed
- **`ml/weather.py`**: Two default parameter strings updated
- **`tests/ml/test_regions_loader.py`**: Four test path strings updated
- **`openspec/specs/regional-weather-coordinates/spec.md`**: Path references updated
- No API changes, no database changes, no user-facing behavior changes
- Fixes the broken `/app/data` symlink regression introduced in `24391b9`/`2520cb4`
