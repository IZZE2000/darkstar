## 1. MultiDayPlanner Core Engine

- [ ] 1.1 Create `planner/strategy/multi_day_planner.py` with a `MultiDayPlanner` class containing a `compute_quota()` method. Input: `remaining_kwh` (float), `deadline` (datetime), `daily_prices` (list[float]), `max_daily_kwh` (list[float]), `min_daily_fraction` (float, default 0.1). Output: `dict[date, float]` mapping each remaining date to its kWh quota. Use inverse-price weighting: `weight[day] = 1 / avg_price[day]`, `quota[day] = (weight[day] / sum(weights)) * remaining_kwh`.
- [ ] 1.2 Implement the minimum daily fraction guardrail: every day except the last SHALL receive at least `min_daily_fraction * remaining_kwh`. Apply the floor after inverse-price weighting, then redistribute any excess from capped days.
- [ ] 1.3 Implement the power capacity cap: each day's quota SHALL be capped at the corresponding `max_daily_kwh[day]` value. Excess energy from capped days SHALL be redistributed to uncapped days proportionally.
- [ ] 1.4 Handle edge cases: single day remaining (allocate all), zero/negative remaining_kwh (return zeros), all prices equal (distribute equally), missing price data for some days (use average of known prices as fill).
- [ ] 1.5 Write unit tests in `tests/planner/test_multi_day_planner.py` covering: basic inverse-price weighting allocation, minimum daily fraction enforcement, power cap redistribution, single day remaining, zero remaining energy, equal prices, partial price data fallback.

## 2. Config Extension

- [ ] 2.1 Add `deadline` (str | None, default None) and `target_kwh` (float | None, default None) fields to the `EVChargerDeviceConfig` dataclass in `executor/config.py`. Parse `deadline` as ISO 8601 datetime string. Add validation: if `deadline` is set but `target_kwh` is missing, log a warning and set both to None.
- [ ] 2.2 Add `deadline` and `target_kwh` example entries (commented out) to `config.yaml` and `config.default.yaml` under the first `ev_chargers` entry, with inline comments explaining multi-day mode.
- [ ] 2.3 Write unit test in `tests/ev/test_ev_config.py` (or extend existing) covering: valid deadline + target_kwh parsing, deadline without target_kwh (warning + fallback), missing deadline (None), deadline in the past (warning + None).

## 3. Pipeline Integration

- [ ] 3.1 Add a helper function `_calculate_remaining_kwh(charger_id: str, target_kwh: float, db_path: str, plugged_since: datetime | None) -> float` in `planner/pipeline.py` that queries `slot_observations` for total `ev_charging_kwh` since the charger was plugged in, and returns `max(0, target_kwh - delivered)`.
- [ ] 3.2 Add a helper function `_get_daily_price_averages(deadline: datetime, db_path: str) -> list[float]` in `planner/pipeline.py` (or a shared utility) that reads from the `price_forecasts` table (from Module 1), computes daily average `spot_p50` for each remaining day until deadline, and returns the list. If no forecasts exist, return an empty list.
- [ ] 3.3 In the EV section of `planner/pipeline.py` (around line 536-593), add multi-day logic: for each charger with a valid `deadline` + `target_kwh` + `price_forecast.enabled`, compute `remaining_kwh` via 3.1, fetch daily prices via 3.2, compute `max_daily_kwh` per day from `max_power_kw * available_hours`, call `MultiDayPlanner.compute_quota()`, and attach `daily_quota_kwh` (today's quota) to the charger state dict.
- [ ] 3.4 In the same pipeline section, set the Kepler deadline: if today is before the deadline day, use end-of-day (23:59 local time) as the deadline. If today IS the deadline day, use the actual deadline time. This replaces the `departure_time`-based calculation for multi-day chargers.
- [ ] 3.5 When `price_forecast.enabled` is false but `deadline` is set, use the `deadline` datetime directly as a simple Kepler deadline (no quota, no MultiDayPlanner call). This provides a basic "charge by date X" mode without price intelligence.
- [ ] 3.6 Write integration tests in `tests/planner/test_pipeline_multi_day_ev.py` covering: multi-day charger gets quota and deadline from pipeline, single-day charger is unaffected, price_forecast disabled falls back to simple deadline, unplugged charger skips quota calculation.

## 4. Solver Integration

- [ ] 4.1 Add `daily_quota_kwh: float | None = None` field to the `EVChargerInput` dataclass in `planner/inputs/types.py`.
- [ ] 4.2 In `planner/solver/adapter.py` `build_ev_charger_inputs()`, read `daily_quota_kwh` from the charger state dict and set it on `EVChargerInput`.
- [ ] 4.3 In `planner/solver/kepler.py`, after existing EV constraint setup, add a daily quota constraint for each charger where `daily_quota_kwh` is not None: `prob += pulp.lpSum(ev_energy[d][t] for t in all_slots) <= charger.daily_quota_kwh`. This limits total energy across the solve horizon for that charger.
- [ ] 4.4 Write solver unit tests in `tests/planner/test_kepler_multi_day_quota.py` covering: charger with quota limits total energy, charger without quota is unconstrained, quota + deadline interact correctly (quota limits energy, deadline limits time window), quota of 0 results in no charging.

## 5. EV Charger State API

- [ ] 5.1 Create `backend/api/routers/ev.py` with a `GET /api/ev/chargers` endpoint. Register the router in `backend/api/app.py`.
- [ ] 5.2 Implement state file persistence: at the end of the multi-day quota calculation in `planner/pipeline.py` (after task 3.3), write per-charger multi-day state (deadline, target_kwh, remaining_kwh, energy_delivered_kwh, daily_quota_kwh, days_remaining, quota_schedule, status) to `data/ev_multi_day_state.json`. Include a `last_updated` timestamp. If no chargers are in multi-day mode, write an empty chargers list.
- [ ] 5.3 In the `GET /api/ev/chargers` endpoint: read the state file, merge with live HA sensor data (plugged_in, soc_percent, power_kw — reuse the same HA fetching pattern from `backend/api/routers/system.py` lines 123-144), and return the combined response. Include `mode` field per charger: `"multi_day"` if deadline is active, `"daily"` if only departure_time is set, `"none"` if neither.
- [ ] 5.4 Compute the `status` field: `"complete"` if remaining_kwh ≤ 0, `"on_track"` if remaining energy can be delivered within remaining days given max_power_kw, `"behind"` if it cannot, `"idle"` if no active deadline. Include chargers in `"daily"` mode with null multi-day fields.
- [ ] 5.5 Write unit tests in `tests/backend/test_ev_api.py` covering: endpoint returns all configured chargers, multi-day charger includes quota_schedule and status, daily-mode charger has null multi-day fields, state file missing or stale returns chargers with `"idle"` status and null multi-day fields.

## 6. End-to-End Verification

- [ ] 6.1 Write an end-to-end test in `tests/planner/test_e2e_multi_day_ev.py` that configures a charger with `deadline` 3 days away, `target_kwh=60`, mocks price forecasts with day 2 being cheapest, runs the full pipeline, and verifies: today's quota is lower than day 2's allocation, Kepler respects the quota, and the schedule contains valid EV charging slots.
- [ ] 6.2 Write a backward-compatibility test that runs the full pipeline with NO multi-day config (standard `departure_time` only) and verifies the output is identical to the existing behavior (no quota constraint, standard deadline calculation).
