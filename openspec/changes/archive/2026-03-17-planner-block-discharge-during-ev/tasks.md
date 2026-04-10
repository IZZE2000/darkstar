## 1. Add Big-M Constraint to Kepler Solver

- [x] 1.1 In `planner/solver/kepler.py`, inside the per-slot loop (the `for t in range(T):` block), find the existing EV grid-only constraint at ~line 236-241 that reads:
  ```python
  if ev_enabled:
      prob += (
          ev_energy[t] <= grid_import[t] + s.pv_kwh + 1e-6
      )
  ```
  Immediately AFTER that constraint (still inside the `if ev_enabled:` block), add a new Big-M constraint:
  ```python
  # Block discharge when EV is charging (match executor source isolation)
  M_discharge = config.max_discharge_power_kw * h
  prob += discharge[t] <= (1 - ev_charge[t]) * M_discharge
  ```
  Note: `h` is `slot_hours[t]` (already defined at ~line 204 as `h: float = slot_hours[t]`). `discharge[t]` is already defined at line 55. `ev_charge[t]` is the binary variable defined at line 105.

## 2. Add Unit Test: Discharge Blocked During EV Charging

- [x] 2.1 In `tests/planner/test_kepler_solver.py`, add a new test function `test_kepler_ev_blocks_discharge()` after the existing `test_kepler_ev_no_battery_drain()` function (~line 241). This test must verify that when EV charging is active, the solver sets discharge to zero even when discharge would otherwise be profitable. Use this exact test:
  ```python
  def test_kepler_ev_blocks_discharge():
      """Verify solver cannot plan discharge and EV charging in the same slot.

      Scenario: Battery is full, house has load, grid is cheap (good for EV charging),
      and there's a high export price (making discharge attractive). The solver must
      NOT discharge and charge EV in the same slot.
      """
      start = datetime(2025, 1, 1, 12, 0)
      slots = []
      for i in range(4):
          slots.append(
              KeplerInputSlot(
                  start_time=start + timedelta(minutes=15 * i),
                  end_time=start + timedelta(minutes=15 * (i + 1)),
                  load_kwh=0.5,     # Some house load
                  pv_kwh=0.0,       # No solar
                  import_price_sek_kwh=0.5,   # Cheap grid (good for EV)
                  export_price_sek_kwh=3.0,   # High export price (tempting discharge)
              )
          )

      input_data = KeplerInput(slots=slots, initial_soc_kwh=10.0)

      config = KeplerConfig(
          capacity_kwh=10.0,
          max_charge_power_kw=5.0,
          max_discharge_power_kw=5.0,
          charge_efficiency=1.0,
          discharge_efficiency=1.0,
          min_soc_percent=0.0,
          max_soc_percent=100.0,
          target_soc_kwh=0.0,  # No target - free to discharge
          wear_cost_sek_per_kwh=0.01,
          enable_export=True,
          max_export_power_kw=5.0,
          # EV Settings - strong incentive to charge
          ev_charging_enabled=True,
          ev_plugged_in=True,
          ev_max_power_kw=10.0,
          ev_battery_capacity_kwh=100.0,
          ev_current_soc_percent=0.0,
          ev_incentive_buckets=[
              IncentiveBucket(threshold_soc=50.0, value_sek=5.0),
          ],
      )

      solver = KeplerSolver()
      result = solver.solve(input_data, config)

      assert result.is_optimal

      for s in result.slots:
          if s.ev_charge_kw > 0.1:
              # In any slot where EV is charging, discharge MUST be zero
              assert s.battery_discharge_kw == pytest.approx(0.0, abs=0.01), (
                  f"Discharge must be 0 when EV is charging! "
                  f"Got discharge={s.battery_discharge_kw}, ev_charge={s.ev_charge_kw}"
              )
  ```
  Note: The existing tests use `KeplerInputSlot`, `KeplerInput`, `KeplerConfig`, `KeplerSolver`, `IncentiveBucket` — all already imported at the top of the test file. Use `pytest.approx` for float comparisons. The result slot field for discharge is `battery_discharge_kw` and for EV is `ev_charge_kw`.

## 3. Run Tests and Verify

- [x] 3.1 Run the full planner test suite: `python -m pytest tests/planner/test_kepler_solver.py -v`. ALL existing tests must still pass. The new `test_kepler_ev_blocks_discharge` test must pass.
