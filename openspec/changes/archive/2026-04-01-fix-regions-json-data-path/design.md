## Context

`regions.json` maps Nordpool price areas to weather coordinates. It was created as a static application file but mistakenly placed in `data/`, which is the user-data mount point (`/share/darkstar` via symlink). When the Dockerfile's `COPY data/regions.json ./data/regions.json` was made to work (via a `.dockerignore` exception), it pre-created `/app/data/` as a real directory. This broke `run.sh`'s `ln -sf /share/darkstar /app/data` — `ln` places the symlink inside the existing directory rather than replacing it, causing the app to connect to an ephemeral empty database.

## Goals / Non-Goals

**Goals:**
- Move `regions.json` to `ml/` where the sole consumer (`ml/weather.py`) lives
- Restore the correct `/app/data → /share/darkstar` symlink behavior
- Update all references consistently (code, tests, Dockerfiles, spec)

**Non-Goals:**
- Changing how `regions.json` is structured or consumed
- Modifying `run.sh` or the symlink mechanism itself
- Any other data directory changes

## Decisions

**Decision: Move to `ml/` rather than repo root or a new `config/` directory.**

`ml/weather.py` is the only consumer. Placing the file next to its consumer is the simplest, most navigable structure. No new directories needed. The root would be cluttered; a new `config/` directory would be over-engineering for a single file used by one module.

**Decision: Update default parameter values in `ml/weather.py`, not environment variables or config.**

The path is an internal implementation detail with a sensible default. There is no user-facing config for this path and no need to introduce one. The two function signatures in `weather.py` already accept a path override, which is sufficient for testing.

**Decision: Update tests to pass `ml/regions.json` explicitly rather than mocking.**

The tests in `test_regions_loader.py` already pass the path as an explicit argument. Updating those strings is the minimal correct change — no structural test changes needed.

## Risks / Trade-offs

- [Any code that hardcodes `"data/regions.json"` as a string outside the identified files] → Mitigated by grep confirming only `ml/weather.py` and the test file reference this path in code.
- [Developer confusion if they look for the file in `data/`] → The spec update makes the canonical location clear.

## Migration Plan

No database changes, no API changes, no user action required. The fix takes effect on the next container build and restart. The user's persistent database at `/share/darkstar/planner_learning.db` is unaffected — the symlink will be correctly restored on next start.
