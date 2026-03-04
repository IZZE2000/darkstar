## Why

Home Assistant sensors can occasionally report spurious values (NaN, Inf, or impossibly high spikes due to sensor glitches, communication errors, or counter resets). These bad values currently flow unchecked into the `slot_observations` database, corrupting historical data and skewing ML training and analysis. The existing 50 kWh threshold in `learning/engine.py` is too permissive (equivalent to 200 kW continuous) and only applies to backfill, not the live recorder path. Existing corrupted rows in the DB are not cleaned — instead all analytical pipelines are hardened to ignore them at read time.

## What Changes

- Add a config-derived `max_kwh_per_slot` calculation based on `system.grid.max_power_kw` with a 2.0x safety factor
- Validate all energy values in `recorder.py` before storing — spike values are set to 0.0 (marking them as unreliable)
- Fix the spike threshold in `learning/engine.py` (`etl_cumulative_to_slots` and `etl_power_to_slots`) from hardcoded 50 kWh to config-derived value
- Harden analytical read paths: `Analyst._fetch_observations`, `LearningStore.get_forecast_vs_actual`, and `LearningStore.calculate_metrics` filter out spike rows at query time so no migration is required

## Capabilities

### New Capabilities

- `sensor-validation`: Validation logic for detecting and handling unreasonable sensor values before database storage

### Modified Capabilities

- `energy-recording`: Adds requirement to validate energy values against physical limits before storage

## Impact

- **backend/recorder.py**: Add validation before `store.store_slot_observations`
- **backend/learning/engine.py**: Replace hardcoded `50.0` threshold in both ETL functions with config-derived value
- **backend/learning/analyst.py**: Filter spike rows in `_fetch_observations` before bias calculation
- **backend/learning/store.py**: Add spike guard to `get_forecast_vs_actual` and `calculate_metrics` queries
- **New utility function**: `get_max_energy_per_slot(config)` in `backend/validation.py`
- **Database**: Existing spiked rows are left untouched — pipelines ignore them at read time
