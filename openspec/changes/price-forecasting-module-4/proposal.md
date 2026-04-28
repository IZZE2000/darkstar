## Why

Darkstar's EV charging currently operates on a single-day horizon: plug in, charge by tomorrow's departure time. When a user has a multi-day window (e.g., plug in Monday, depart Friday), the system cannot spread charging across cheaper days — it front-loads everything into the first overnight window. With Module 1's 7-day price forecasts now available, the system can distribute energy quotas across days to minimize cost. This change builds a reusable deferral controller that sits above Kepler, assigning daily energy budgets based on forecast price trends while letting Kepler handle within-day optimization using exact Nordpool prices.

## What Changes

- Create a `MultiDayPlanner` class that takes an energy requirement (kWh), a deadline (datetime), and a 7-day price forecast, and returns a daily kWh quota allocation.
- Extend EV charger config with an optional `deadline` field (datetime) as an alternative to the existing daily `departure_time`. When set, the deferral controller distributes charging across days; when absent, existing single-day behavior is unchanged.
- Integrate the `MultiDayPlanner` into the planner pipeline: before Kepler runs, the controller determines today's EV energy quota. Kepler then optimizes that quota using exact Nordpool prices.
- The quota is recalculated daily — if the forecast was wrong, the remaining energy is redistributed across remaining days using updated forecasts.
- All multi-day deferral behavior is gated behind `price_forecast.enabled`. When disabled, EV charging uses the existing single-day `departure_time` logic.

## Capabilities

### New Capabilities
- `multi-day-deferral-controller`: The reusable `MultiDayPlanner` engine that distributes energy requirements across days based on price forecasts. Takes energy target, deadline, and price forecast; returns daily quota allocation.
- `ev-multi-day-charging`: Integration of the deferral controller with EV charger config, pipeline, and Kepler. Extends per-device config with optional deadline, wires quota into Kepler's EV energy constraints.

### Modified Capabilities
- `per-device-ev-scheduling`: The existing EV scheduling gains an optional multi-day deadline mode alongside the existing daily `departure_time`. Pipeline deadline calculation is extended to support both modes.

## Impact

- **Planner** (`planner/`): New `MultiDayPlanner` class (likely `planner/strategy/multi_day_planner.py`). Pipeline changes to invoke the controller before Kepler. Pipeline writes per-charger multi-day state to `data/ev_multi_day_state.json` after quota computation.
- **Config** (`config.yaml`, `executor/config.py`): New optional `deadline` field per EV charger. Existing `departure_time` behavior preserved.
- **Solver** (`planner/solver/`): Kepler receives a daily energy quota as an upper bound on EV charging when in multi-day mode. Adapter changes to pass quota through.
- **API** (`backend/api/routers/ev.py`): New read-only `GET /api/ev/chargers` endpoint returning per-charger state (mode, multi-day progress, quota schedule, live HA sensor data). This is the contract that Module 5's frontend consumes.
- **Tests**: Unit tests for `MultiDayPlanner` quota logic. Integration tests for pipeline with multi-day EV deadlines. API endpoint tests.
- **Dependencies**: Requires Module 1 (price-forecasting-core) — specifically the price forecast API/DB. No new external dependencies.
- **No breaking changes**: All modifications are additive and gated. Single-day `departure_time` remains the default.
