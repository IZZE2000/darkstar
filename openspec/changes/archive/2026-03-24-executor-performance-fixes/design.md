## Context

The executor's main loop calls `reload_config()` on every tick (~every 60s), which re-reads `config.yaml` from disk and re-parses the inverter profile YAML. On resource-constrained hardware (HA Yellow, ARM Cortex-A53), this adds 100-500ms per tick.

The Nordpool price fetch in the executor uses `asyncio.run()` inside an already-running async event loop. The code detects this and skips the fetch every time, falling back to a hardcoded 0.5 SEK/kWh. This affects all users, not just slow hardware.

The recorder and executor fetch water heater sensors regardless of `has_water_heater`, causing 404s and log spam when water heating is disabled.

## Goals / Non-Goals

**Goals:**
- Eliminate unnecessary per-tick YAML I/O by caching config and profile with file-mtime detection
- Fix the Nordpool price fetch so the executor uses real spot prices for battery cost tracking
- Gate water heater sensor reads behind the `has_water_heater` flag
- Clean the default config template to not ship phantom sensor references

**Non-Goals:**
- Optimizing the planner/Kepler solver performance (separate concern)
- Adding Docker memory limits (too risky for diverse hardware)
- Lazy-loading ML models (negligible memory savings — models are ~3MB total)
- Changing the executor tick interval or threading architecture

## Decisions

### Decision 1: File mtime-based config caching

Cache the parsed config and profile in memory. Before each tick, check `os.path.getmtime()` on `config.yaml` and the profile YAML file. Only re-parse if the mtime has changed.

**Alternative considered**: File watcher (inotify/watchdog) — rejected because it adds a dependency and complexity for a simple problem. Stat-ing a file is essentially free compared to parsing YAML.

**Alternative considered**: Timer-based reload (e.g., every 5 minutes) — rejected because mtime check is just as cheap and gives instant response to config changes.

### Decision 2: Replace asyncio.run() with await for Nordpool fetch

The `get_nordpool_data()` function is already async. Since `_tick()` runs inside an async event loop, we simply `await` it directly. Remove the entire `asyncio.get_running_loop()` detection block.

**Alternative considered**: Run Nordpool fetch in a separate thread with `asyncio.to_thread()` — rejected because the function is already async and works correctly with `await` everywhere else in the codebase (recorder.py:628, forecast.py:540, schedule.py:94).

### Decision 3: Guard water heater reads with system flag check

Add a check for `system.has_water_heater` before iterating `water_heaters[]` in both `recorder.py` and the executor's state gathering. Same pattern for EV chargers with `has_ev_charger`.

The default config template (`config.default.yaml`) will have the water heater sensor field set to empty string (`sensor: ''`) instead of `sensor: sensor.vvb_power`, matching the pattern already used for other optional fields.

## Risks / Trade-offs

- **[Config cache staleness]** → Mitigated by checking mtime on every tick. The OS filesystem cache makes stat() nearly free. Worst case: if a file is modified within the same second as the last read, the change is picked up on the next tick (1 minute later).
- **[Nordpool fetch adds latency to tick]** → The fetch is an HTTP call to HA's Nordpool integration. If HA is slow, this could add to tick duration. Mitigated by using a short timeout (5s) and falling back to the existing 0.5 SEK/kWh default on failure, same as today.
- **[Water heater guard hides config mistakes]** → If a user has `has_water_heater: false` but actually has a water heater configured, sensors won't be read. This is correct behavior — the flag is the source of truth for feature enablement.
