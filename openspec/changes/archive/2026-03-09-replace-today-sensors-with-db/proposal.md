## Why

Currently, the Dashboard fetches daily energy totals from Home Assistant's `today_*` sensors (today_load_consumption, today_grid_import, etc.) for display in various cards. This creates several problems:

1. **Inconsistent data**: The recorder stores base load (EV subtracted) in the database, but the HA sensors report total load (EV included), causing confusion in the Dashboard
2. **Extra configuration burden**: Users must configure 7 additional "today_*" sensors on top of the cumulative sensors
3. **Unnecessary complexity**: We already have all the data in the database from the recorder's 15-minute observations

By querying the database instead, we ensure consistent, isolated data across all displays and simplify the configuration requirements.

## What Changes

**BREAKING**: Remove all `today_*` sensor configuration requirements and Dashboard reads

- **Remove** 7 `today_*` sensors from default config (`today_grid_import`, `today_grid_export`, `today_pv_production`, `today_load_consumption`, `today_battery_charge`, `today_battery_discharge`, `today_net_cost`)
- **Remove** these sensors from Settings UI configuration help and validation
- **Replace** `/api/services/energy/today` implementation to query database instead of HA sensors
- **Modify** `/api/services/energy/range` to remove HA sensor overlay for "today" period
- **Add** conditional EV charging data field to Dashboard Energy Resources card (only when `has_ev_charger` is enabled)
- **Update** Dashboard Energy Resources card to display EV charging as a separate metric

## Capabilities

### New Capabilities
- `dashboard-ev-display`: Add conditional EV charging display to Dashboard Energy Resources card based on `has_ev_charger` configuration

### Modified Capabilities
- `energy-totals-api`: Change `/api/services/energy/today` and `/api/services/energy/range` to source data from database instead of HA sensors
- `sensor-configuration`: Remove requirement for `today_*` sensors in configuration schema and UI

## Impact

**Backend:**
- `backend/api/routers/services.py`: Rewrite energy endpoints to query DB
- `backend/config/validation.py`: Remove today_* sensor requirements
- `backend/health.py`: Remove today_* sensor checks

**Frontend:**
- `frontend/src/pages/settings/`: Remove today_* sensors from config UI
- `frontend/src/pages/Dashboard.tsx`: Update to receive EV data from API
- `frontend/src/components/CommandDomains.tsx`: Add EV field to ResourcesDomain

**Configuration:**
- `config.default.yaml`: Remove today_* sensors
- Settings UI help: Remove references to today_* sensors

**Breaking Change:**
This is a hard switch. Users must remove today_* sensors from their config.yaml. No migration path or fallback will be provided (Beta phase).
