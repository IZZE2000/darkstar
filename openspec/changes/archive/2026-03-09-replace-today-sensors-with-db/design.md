## Context

The current implementation has a split-brain problem:

**Database path** (recorder → SlotObservation):
- Uses cumulative sensors to calculate energy deltas
- Subtracts EV and water heating from total load
- Stores clean base load in `load_kwh`

**HA sensor path** (Dashboard → /api/services/energy/*):
- Reads `today_*` sensors directly from Home Assistant
- These sensors report total consumption without EV isolation
- Causes Dashboard to show EV-inclusive load while ML/planner uses base load

This leads to user confusion when they see 80kWh house load in the Dashboard but the forecast and optimization treats it differently.

## Goals / Non-Goals

**Goals:**
- Unify all energy display data to come from database (SlotObservation)
- Ensure consistent EV isolation across all UI views
- Simplify configuration by removing 7 redundant sensors
- Add EV charging display to Dashboard (conditional on `has_ev_charger`)

**Non-Goals:**
- Change the recorder's isolation logic (it already works correctly)
- Modify the ML model training (it already uses clean DB data)
- Provide backwards compatibility or migration for today_* sensors (hard switch for Beta)
- Change 15-minute observation frequency

## Decisions

### 1. Use DB Aggregation for Daily Totals

**Decision:** Rewrite `/api/services/energy/today` to query `SUM(load_kwh)` for current day instead of reading HA sensors.

**Rationale:**
- Ensures data consistency between Dashboard and ML/planner
- Leverages existing recorder infrastructure
- Single source of truth (SlotObservation table)

**Alternative considered:** Keep HA sensors with client-side subtraction
- Rejected: Would require fetching EV data separately and doing math in the backend
- More complex, still need DB for EV values anyway

### 2. Hard Switch - No Backwards Compatibility

**Decision:** Remove today_* sensors entirely from config schema and code.

**Rationale:**
- Beta phase allows breaking changes
- Hard switch is simpler than maintaining dual paths
- All Beta users have cumulative sensors already configured

**Alternative considered:** Support both for migration period
- Rejected: Adds complexity, Beta phase is for iteration

### 3. Add EV Charging to API Response

**Decision:** Include `ev_charging_kwh` in the energy endpoints response.

**Rationale:**
- Frontend needs to display EV separately from house load
- Keeps UI logic simple (API provides ready-to-display data)
- Matches the pattern used for water_heating_kwh

### 4. Frontend Conditional Display

**Decision:** Frontend queries config to check `has_ev_charger` before showing EV field.

**Rationale:**
- Avoids flickering or showing "0 kWh" to users without EV
- Clean UI when feature not applicable

**Alternative considered:** API always returns EV field, null if not configured
- Rejected: Frontend logic is cleaner with explicit capability check

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| DB query slower than HA sensor read | Query is simple aggregation, DB is local SQLite. Unlikely to be perceptible. |
| No real-time updates (15-min delay) | Current behavior - not a regression. Cumulative sensors provide daily totals anyway. |
| Users missing data if recorder stops | Health check already monitors recorder. Would be same issue with HA sensors. |
| Breaking change confusion | Beta release notes. Users were told to expect changes during Beta. |

### Trade-offs

**15-minute resolution vs. real-time:**
- We lose second-by-second updates in the Dashboard
- But we gain data integrity and consistency
- For daily totals, 15-min resolution is sufficient

**SQLite vs. HA sensor reliability:**
- If Home Assistant is down, DB still works
- If DB is corrupted, we have bigger problems
- Net positive: removes external dependency

## Migration Plan

**Release Notes for Beta Users:**
1. Remove today_* sensors from your config.yaml input_sensors section
2. Keep your cumulative sensors (total_load_consumption, total_grid_import, etc.)
3. Restart Darkstar

**Code Changes Order:**
1. Backend API changes (query DB)
2. Frontend changes (display EV field)
3. Config cleanup (remove sensors from defaults and UI)
4. Health check cleanup
5. Tests update

**Rollback:**
- Not provided (hard switch)
- If critical issue, users can restore previous version from git

## Additional Optimization: Consolidate Water Data Fetch

**Decision:** Update Dashboard.tsx to pull `water_heating_kwh` from `/api/services/energy/today` response instead of calling `Api.haWaterToday()` separately.

**Rationale:**
- Unified DB endpoint already returns water_kwh along with all other energy metrics
- Removes unnecessary separate API call (one less round trip, one less HA dependency)
- Makes SlotObservation the true single source of truth for ALL daily energy metrics
- Consistent with the "hard switch" philosophy - no mixed data sources

**Implementation:**
- Extend energy/today API response to include water_kwh (SlotObservation already has this field)
- Update Dashboard.tsx to use `todayStats?.water_heating_kwh` instead of separate waterToday fetch
- Deprecate or remove the separate `/water_today` endpoint over time

## Open Questions

1. **Should we include `ev_charging_kwh` in the main response or a separate endpoint?**
   - Decision: Include in main response alongside `load_consumption_kwh`

2. **What if user has `has_ev_charger: true` but no EV charging happened today?**
   - Show "0.0 kWh" - this is correct information

3. **Should we aggregate EV for the forecast average too?**
   - Out of scope for this change
