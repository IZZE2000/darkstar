## 1. Price Floor Addon Calculation

- [ ] 1.1 Add `RISK_PRICE_KW_FRACTION` dict constant near the top of `planner/strategy/s_index.py` (alongside the existing `RISK_CONFIG` dict):
  ```python
  RISK_PRICE_KW_FRACTION: dict[int, float] = {
      1: 0.15,  # Safety:       15% of capacity per SEK/kWh spread
      2: 0.12,  # Conservative: 12% of capacity per SEK/kWh spread
      3: 0.10,  # Neutral:      10% of capacity per SEK/kWh spread
      4: 0.05,  # Aggressive:    5% of capacity per SEK/kWh spread
      5: 0.02,  # Gambler:       2% of capacity per SEK/kWh spread
  }
  ```

- [ ] 1.2 Create a new function `calculate_price_floor_addon()` in `planner/strategy/s_index.py`. Signature:
  ```python
  def calculate_price_floor_addon(
      upcoming_daily_avg_spots: dict[str, float],  # ISO date -> avg spot p50 (SEK/kWh)
      trailing_avg_spot: float | None,             # 14-day trailing avg (SEK/kWh)
      capacity_kwh: float,
      risk_appetite: int,
  ) -> tuple[float, dict[str, Any]]:
  ```
  Logic:
  1. If `upcoming_daily_avg_spots` is empty or `trailing_avg_spot` is None or `<= 0`, return `(0.0, {"price_adjustment_active": False, "price_adjustment_reason": "insufficient_data"})`.
  2. Compute `peak_upcoming_sek = max(upcoming_daily_avg_spots.values())`.
  3. Compute `price_spread_sek = peak_upcoming_sek - trailing_avg_spot`.
  4. Look up `risk_fraction = RISK_PRICE_KW_FRACTION.get(risk_appetite, 0.10)`.
  5. Compute `price_addon_kwh = capacity_kwh * price_spread_sek * risk_fraction`.
  6. Return `(price_addon_kwh, {"price_adjustment_active": True, "price_spread_sek": price_spread_sek, "peak_upcoming_spot_sek": peak_upcoming_sek, "trailing_avg_spot_sek": trailing_avg_spot, "price_addon_kwh": price_addon_kwh, "price_reserve_fraction": risk_fraction})`.

## 2. Safety Floor Integration (Two-Tier)

- [ ] 2.1 Add three optional parameters to `calculate_safety_floor()` in `planner/strategy/s_index.py`:
  ```python
  upcoming_daily_avg_spots: dict[str, float] | None = None,
  trailing_avg_spot: float | None = None,
  risk_appetite: int = 3,
  ```
  These default to None/3 so the existing call sites are fully backward-compatible.

- [ ] 2.2 At the **end** of `calculate_safety_floor()`, after the existing `safety_floor_kwh` has been computed and capped at `min_soc_kwh + max_buffer_kwh` (Layer 1), add the Layer 2 price block. **The price addon is additive only — negative addons are clamped to zero effect so price never undercuts the deficit-based safety floor:**
  ```python
  # Layer 2: price floor addon (applied after existing 20% cap, additive only)
  if upcoming_daily_avg_spots is not None and trailing_avg_spot is not None:
      price_addon_kwh, price_debug = calculate_price_floor_addon(
          upcoming_daily_avg_spots, trailing_avg_spot, capacity_kwh, risk_appetite
      )
      # Asymmetric clamp: price can only RAISE the floor, never lower it.
      # Lower bound is safety_floor_kwh (Layer 1 result), not min_soc_kwh.
      final_floor_kwh = max(
          safety_floor_kwh,
          min(safety_floor_kwh + price_addon_kwh, 0.80 * capacity_kwh)
      )
      debug.update(price_debug)
      debug["price_addon_applied_kwh"] = final_floor_kwh - safety_floor_kwh
      debug["final_floor_kwh"] = final_floor_kwh
  else:
      final_floor_kwh = safety_floor_kwh
      debug["price_adjustment_active"] = False
      debug["price_adjustment_reason"] = "disabled_or_no_data"
  ```
  Return `final_floor_kwh` instead of `safety_floor_kwh`. Note: the *computed* `price_addon_kwh` may be negative (debug visibility), but the *effective* change to the floor is `max(0, price_addon_kwh)` after the clamp.

- [ ] 2.3 After computing `price_addon_kwh`, add strategy event logging only when the floor is meaningfully raised (negative addons produce no event since they have no effect):
  ```python
  if price_addon_kwh >= 0.5:
      append_strategy_event(
          event_type="STRATEGY_CHANGE",
          message=(
              f"Price signal: peak forecast {peak_upcoming_sek:.2f} SEK/kWh "
              f"({price_spread_sek:+.2f} vs trailing avg) → floor raised "
              f"by {price_addon_kwh:.1f} kWh"
          ),
          data={
              "price_spread_sek": price_spread_sek,
              "price_addon_kwh": price_addon_kwh,
              "peak_upcoming_spot_sek": peak_upcoming_sek,
          },
      )
  ```

## 3. Pipeline Wiring

- [ ] 3.1 In `planner/pipeline.py`, add a helper function (or inline, matching existing patterns) to fetch price data for the safety floor. The helper should:
  - Query `price_forecasts` table for `slot_start` in D+1 through D+7, grouping by date, returning `avg(spot_p50)` per day as `dict[str, float]` (ISO date string → avg SEK/kWh).
  - Query `slot_observations` for the trailing 14-day average of `export_price_sek_kwh` where at least 2 distinct calendar days exist; return `float | None`.
  - Return both. Use the existing async DB access pattern (same as how Aurora data is fetched in the pipeline).

- [ ] 3.2 In the strategy section of `planner/pipeline.py` (around the `calculate_safety_floor()` call), add:
  ```python
  upcoming_spots: dict[str, float] | None = None
  trailing_spot: float | None = None
  if active_config.get("price_forecast", {}).get("enabled", False):
      upcoming_spots, trailing_spot = await fetch_price_floor_inputs(sqlite_path)
  ```

- [ ] 3.3 Pass the fetched data and `risk_appetite` to `calculate_safety_floor()`:
  ```python
  target_soc_kwh, soc_debug = calculate_safety_floor(
      df,
      active_config.get("battery", {}),
      s_index_cfg,
      timezone_name,
      fetch_temperature_fn=...,
      full_forecast_df=full_forecast_df,
      price_horizon_end=price_horizon_end,
      upcoming_daily_avg_spots=upcoming_spots,
      trailing_avg_spot=trailing_spot,
      risk_appetite=int(s_index_cfg.get("risk_appetite", 3)),
  )
  ```

## 4. Tests

- [ ] 4.1 Create `tests/planner/strategy/test_s_index_price_awareness.py` with unit tests for `calculate_price_floor_addon()`:
  - **Rising prices:** `upcoming = {"2026-04-02": 3.0}`, `trailing = 1.0`, `capacity = 10.0`, `risk = 3` → addon = `10.0 × 2.0 × 0.10 = 2.0 kWh`, debug active = True.
  - **Cheap period:** `upcoming = {"2026-04-02": 0.5}`, `trailing = 1.5`, `capacity = 10.0`, `risk = 3` → addon = `10.0 × -1.0 × 0.10 = -1.0 kWh`.
  - **Peak selection:** `upcoming = {"2026-04-02": 1.0, "2026-04-05": 5.0}`, `trailing = 1.0` → addon uses `peak = 5.0`, spread = `4.0`.
  - **Insufficient forecast data:** empty `upcoming_daily_avg_spots` → `(0.0, {"price_adjustment_active": False, ...})`.
  - **Insufficient historical data:** `trailing_avg_spot = None` → `(0.0, {"price_adjustment_active": False, ...})`.
  - **Risk scaling:** same inputs at risk 1 (0.15) vs risk 5 (0.02) produce proportionally different addons.

- [ ] 4.2 Add integration tests for `calculate_safety_floor()` with price data in the same file:
  - **Two-tier floor increase:** pass price data with positive spread → `final_floor > safety_floor_kwh` (before price addon).
  - **Cheap-period asymmetry (Option B):** pass price data with negative spread → `final_floor == safety_floor_kwh` (negative addon clamped to zero effect). The computed `price_addon_kwh` in debug SHALL still reflect the negative value for observability, but `price_addon_applied_kwh` SHALL be 0.
  - **80% cap enforced:** construct scenario where addon would push floor above 80% capacity → clamped at 80%.
  - **safety_floor preserved on extreme negative addon:** very large negative spread → `final_floor == safety_floor_kwh` (never below). Verify result is *not* clamped to `min_soc_kwh`.
  - **Backward compatibility:** call `calculate_safety_floor()` with no price params → result identical to pre-change behavior.
  - **Disabled (no params):** `upcoming_daily_avg_spots=None` → `price_adjustment_active = False` in debug, no floor change.
  - **No strategy log on negative addon:** integration test verifies `append_strategy_event` is *not* called when spread is negative (since negative addons have no effective floor change).

- [ ] 4.3 Verify existing S-Index tests in `tests/planner/test_safety_floor_temporal.py` and `tests/planner/strategy/test_s_index_new.py` still pass without modification.
