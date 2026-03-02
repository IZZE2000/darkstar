# Design: Effekttariff Peak Guard (V1)

This document defines the technical architecture for the "KISS" version of the Effekttariff peak power management in Darkstar.

## 1. Core Philosophy: The "Dual-Layer" Strategy

To manage a power tariff effectively, Darkstar must act in two distinct ways:

1.  **The Accountant (Planner):** Strategic 15-minute planning. It sets a "Hard Wall" in the solver so the *planned* schedule never intentionally crosses the peak limit during expensive windows.
2.  **The Babysitter/Fuse (Executor):** Reactive 1-minute (or real-time) monitoring. It handles unpredictable house spikes (e.g., turning on a kettle) by immediately "shedding" controllable loads to keep the total import under the limit.

## 2. State & Inputs

The system relies on a dynamic "Effective Limit" to ensure it remains useful throughout the month.

### Inputs:
- `peak_power_limit`: User's target limit in kW (e.g., 5.0).
- `peak_window_start/stop`: Time window for the tariff (e.g., 07:00 - 19:00).
- `current_month_peak_sensor`: (Optional) HA sensor tracking the highest peak hit so far this month.

### The "Effective Limit" Formula:
```python
# If we hit 8kW on the 5th of the month, we don't want to keep
# annoying the user by trying to stay under 5kW for the rest of the month.
Effective Limit = MAX(peak_power_limit, current_month_peak_sensor)
```

## 3. Implementation Details

### Layer 1: The Planner (Kepler Solver)
- **File:** `planner/solver/kepler.py`
- **Action:** During the defined `peak_window`, add a hard constraint to the MILP problem:
  `grid_import[t] <= Effective Limit * slot_hours`
- **Goal:** Prevent the planner from *planning* to charge the EV or the battery at a rate that would breach the limit.

### Layer 2: The Executor (Reactive Override)
- **File:** `executor/override.py`
- **Action:** Add a high-priority `PEAK_GUARD` override that evaluates if `current_import_kw > Effective Limit`.
- **Shedding Priority (Order of Operations):**
    1.  **Throttle EV:** Reduce EV charging power (or stop it). This is the highest impact and fastest response. (Check `has_ev` toggle).
    2.  **Stop Water Heater:** Turn off the water heater immediately. (Check `has_water_heater` toggle).
    3.  **Force Battery Discharge:** If house spikes (kettle/oven) still exceed the limit, force the battery to discharge at maximum power to "shave the peak."

## 4. Syncing with Home Assistant
- The three core parameters (`limit`, `start`, `stop`) should be synced with HA `input_number` and `input_datetime` entities.
- If changed in the Darkstar UI, the `ActionDispatcher` must update the HA entity values to ensure "Single Source of Truth."

## 5. Why this is KISS (Keep It Simple, Stupid)
- **No Month-Long Forecasts:** We don't need to see 30 days ahead; the `MAX()` formula handles the "memory" of the month.
- **Binary Success:** The user either stays under their limit or they don't.
- **Zero Configuration:** If a user doesn't have an EV or a Water Heater, the Executor simply skips those steps and uses the battery (if available).
