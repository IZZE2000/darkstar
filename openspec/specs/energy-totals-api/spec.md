# Energy Totals API

## Purpose

API endpoints for retrieving aggregated energy totals from the database.

## Requirements

### Requirement: Energy endpoints query database for totals
The `/api/energy/today` and `/api/energy/range` endpoints SHALL query the database (SlotObservation table) to calculate energy totals, instead of reading Home Assistant sensors. These endpoints are served from `backend/api/routers/energy.py`.

#### Scenario: /energy/today returns DB-aggregated data
- **WHEN** a client calls GET /api/energy/today
- **THEN** the endpoint queries SlotObservation table for today's records
- **AND** returns aggregated totals: load_consumption_kwh, pv_production_kwh, grid_import_kwh, grid_export_kwh, battery_charge_kwh, battery_discharge_kwh, ev_charging_kwh

#### Scenario: /energy/range returns DB data for today
- **WHEN** a client calls GET /api/energy/range with period="today"
- **THEN** the endpoint queries SlotObservation table for today's records
- **AND** returns DB-aggregated data WITHOUT overlaying HA sensor values
- **AND** does NOT use the previous max(db_value, ha_value) logic

### Requirement: Energy endpoints include EV charging data
The energy endpoints SHALL include `ev_charging_kwh` in the response, representing the sum of EV charging energy for the requested period. These endpoints are served from `backend/api/routers/energy.py`.

#### Scenario: Response includes ev_charging_kwh
- **WHEN** a client calls any energy endpoint
- **THEN** the response includes an `ev_charging_kwh` field
- **AND** the value is the sum of `ev_charging_kwh` from SlotObservation records for the period
- **AND** the value is `0.0` if no EV charging occurred or no EV is configured
