## Why

Beta testing on HA Yellow (ARM Cortex-A53, 4GB RAM) revealed that the executor tick is consistently slow (2-8s, threshold 1.0s), the Nordpool price fetch is permanently broken due to an async/sync mismatch, and unconfigured water heater sensors are polled on every tick. These issues affect all users to varying degrees — the Nordpool bug means every installation gets a hardcoded 0.5 SEK/kWh fallback for battery cost tracking instead of real spot prices.

## What Changes

- **Config/profile caching**: Cache parsed config and inverter profile in memory. Only re-read from disk when the file's modification timestamp changes. Eliminates unnecessary YAML I/O on every tick.
- **Fix Nordpool price fetch**: Replace the broken `asyncio.run()` call with a direct `await` since the executor tick is already running in an async context. The current code detects "event loop already running" and always skips the fetch.
- **Water heater sensor guard**: Skip water heater sensor fetches when `system.has_water_heater` is `false`. Also remove the placeholder `sensor: sensor.vvb_power` from `config.default.yaml` so new installs don't ship with a phantom sensor entity.

## Capabilities

### New Capabilities
- `config-caching`: File-change-aware caching for config and inverter profile YAML, replacing per-tick re-parsing

### Modified Capabilities
- `executor`: Nordpool price fetch fixed to use `await` instead of broken `asyncio.run()` path; water heater sensor reads gated by `has_water_heater` flag
- `sensor-configuration`: Default config cleaned to not include placeholder water heater sensor when water heating is disabled by default

## Impact

- `executor/engine.py`: Config reload path, Nordpool fetch block (~lines 1820-1850), system state gathering
- `executor/profiles.py`: Profile loading wrapped with cache layer
- `backend/recorder.py`: Water heater sensor fetch loop gated by system flag
- `config.default.yaml`: Water heater sensor placeholder removed/cleared
- No API changes, no breaking changes, no new dependencies
