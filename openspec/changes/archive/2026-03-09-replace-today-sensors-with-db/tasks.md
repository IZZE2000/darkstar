## 1. Backend API Changes

- [x] 1.1 Rewrite `/api/services/energy/today` to query SlotObservation table — prefer delegating to `energy/range(period="today")` internally to avoid duplicate query logic
- [x] 1.2 Modify `/api/services/energy/range` to remove HA sensor overlay for "today" period (use DB only)
- [x] 1.3 Add `ev_charging_kwh` and `water_kwh` aggregation to both energy endpoints
- [x] 1.4 Carry over `battery_cycles` calculation (`batt_discharge_kwh / capacity_kwh`) to new `energy/today` response
- [x] 1.5 Unify response keys between `energy/today` and `energy/range` — align legacy aliases (`solar`, `consumption`, `net_cost_kr`) to match range keys (`pv_production_kwh`, `load_consumption_kwh`, `net_cost_sek`)
- [x] 1.6 Remove unused HA sensor reading code from services.py
- [x] 1.7 Deprecate `GET /api/ha/water_today` endpoint (now covered by `energy/today`)

## 2. Configuration and Validation

- [x] 2.1 Remove all `today_*` sensors from `config.default.yaml` input_sensors section
- [x] 2.2 Update `backend/config/validation.py` to reject or warn about `today_*` sensors
- [x] 2.3 Remove `today_*` sensor requirements from `backend/health.py` health checks
- [x] 2.4 Update config-help.json to remove today_* sensor documentation

## 3. Frontend Dashboard Updates

- [x] 3.1 Add `ev_charging_kwh`, `water_heating_kwh` to `ResourcesDomain` component (CommandDomains.tsx)
- [x] 3.2 Fetch system config once on Dashboard initialization, read `has_solar`, `has_battery`, `has_water_heater`, `has_ev_charger`
- [x] 3.3 Conditionally render Solar, Battery, Water, and EV metrics in Energy Resources card based on respective `has_*` flags
- [x] 3.4 Update Dashboard to receive and display EV and water data from API response
- [x] 3.5 Remove separate `Api.haWaterToday()` call, use data from unified energy endpoint
- [x] 3.6 Update Dashboard TypeScript types for new API response structure (unified keys)

## 4. Settings UI Cleanup

- [x] 4.1 Remove `today_*` sensor fields from Settings UI configuration forms
- [x] 4.2 Update Settings page to display only cumulative sensors
- [x] 4.3 Remove today_* sensor references from settings help text

## 5. Testing and Validation

- [x] 5.1 Update backend tests for new DB-only energy endpoints
- [x] 5.2 Update health check tests to remove today_* sensor validations
- [x] 5.3 Add tests for ev_charging_kwh aggregation in API responses
- [x] 5.4 Test Dashboard EV field conditional rendering with has_ev_charger flag
- [x] 5.5 Verify DB-only aggregation matches expected energy totals

## 6. Documentation and Release Notes

- [x] 6.1 Update README or configuration guide to reflect new sensor requirements
- [x] 6.2 Update release notes for v2.6.1-beta to include breaking change notice and new architecture
- [x] 6.3 Update architecture documentation to reflect DB-as-source-of-truth
