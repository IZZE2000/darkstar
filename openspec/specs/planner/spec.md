## Purpose

The Planner is responsible for generating optimized energy management schedules by solving MILP (Mixed Integer Linear Programming) problems. It coordinates data fetching, solver execution, and result delivery.

## Requirements

### Requirement: Planner Handles Formatting Safely
The planner logging logic SHALL correctly escape standard percent-formatting characters.

#### Scenario: Logging EV SoC fallback
- **WHEN** EV SoC sensor returns no data
- **THEN** the system logs a warning with the literal "0%" without crashing

### Requirement: Meaningful Planner Error Notifications
The planner error handler SHALL emit a string containing the error type for generic exceptions.

#### Scenario: Exception Caught in Planner
- **WHEN** a `ValueError` is raised during planner execution
- **THEN** the WebSocket notification includes "ValueError: incomplete format" instead of just "incomplete format"

### Requirement: End-of-Horizon SoC Target acts as a Minimum Floor (Safety Floor)
The solver SHALL enforce the end-of-horizon `target_soc` constraint solely as a minimum floor. It SHALL penalize the solver heavily if the final State of Charge (SoC) is *below* the target (`target_under_violation`). The solver SHALL NOT apply any penalty (`target_over_violation`) if the final SoC exceeds the target, allowing the system to naturally preserve excess free or cheap energy beyond the minimum safety requirement.

The safety floor calculation SHALL use **temporal (per-slot) deficit** instead of aggregate deficit ratio. For each forecast slot, the system SHALL compute `max(0, load_forecast - pv_forecast)` and sum these values to determine the total energy the battery must provide when PV is unavailable. This temporal deficit SHALL replace the previous `(total_load - total_pv) / total_load` aggregate ratio.

The safety floor calculation SHALL look **beyond the price horizon** by using extended load/PV forecast data for a 24h window starting from where the price data ends. When extended forecast data is unavailable, the system SHALL fall back to using only the available horizon and log a warning.

The safety floor SHALL incorporate two risk-based mechanisms:
1. A **risk margin** applied to the temporal deficit (higher risk appetite = lower margin, trusting the forecast more)
2. A **minimum floor** per risk level as a percentage of battery capacity above min_soc, ensuring the floor never collapses to min_soc regardless of forecast conditions

The existing `max_safety_buffer_pct` cap SHALL still apply to prevent the floor from exceeding reasonable levels.

#### Scenario: Excess Solar Energy at End of Horizon
- **WHEN** the battery receives abundant solar energy and covering all loads leaves the end-of-horizon SoC higher than the calculated Safety Floor target
- **THEN** the solver finishes the horizon with the high SoC without attempting to force-dump the energy into the grid to hit the target

#### Scenario: Spring day with aggregate PV surplus but overnight deficit
- **WHEN** total PV forecast over the horizon exceeds total load forecast (aggregate surplus)
- **AND** evening/night slots have load but zero PV (temporal deficit exists)
- **THEN** the safety floor SHALL reflect the temporal deficit (not zero)
- **AND** the risk appetite setting SHALL meaningfully scale the floor

#### Scenario: Midday planning with short price horizon
- **WHEN** planning occurs at midday and price data only extends to midnight (~11.5h horizon)
- **AND** load/PV forecasts extend beyond midnight
- **THEN** the safety floor SHALL use the extended forecast data for the 24h window beyond midnight to account for tomorrow's overnight energy needs

#### Scenario: Price horizon expands after 13:00
- **WHEN** tomorrow's prices arrive at 13:00 and the price horizon extends to tomorrow midnight
- **THEN** the safety floor look-ahead window SHALL shift to cover the 24h beyond tomorrow midnight
- **AND** the MILP can now directly optimize the previously-blind overnight period

#### Scenario: Risk level 3 neutral user in spring
- **GIVEN** risk_appetite = 3, min_soc = 12%, battery capacity = 34.2 kWh
- **WHEN** the temporal deficit beyond the price horizon is approximately 15 kWh (overnight load)
- **THEN** the safety floor SHALL be significantly above min_soc (approximately 20-35% depending on margin and minimum floor)

#### Scenario: Risk level 5 gambler with PV surplus
- **GIVEN** risk_appetite = 5
- **WHEN** temporal deficit beyond the price horizon is calculated
- **THEN** the safety floor SHALL equal min_soc (0% margin, 0% minimum floor)

#### Scenario: Extended forecast data unavailable
- **WHEN** load/PV forecast data does not extend beyond the price horizon
- **THEN** the system SHALL log a warning
- **AND** the safety floor SHALL use only the available horizon data with the minimum floor per risk level as baseline

#### Scenario: Max safety buffer cap applies
- **WHEN** the calculated safety floor (temporal deficit reserve + weather buffer + minimum floor) exceeds `max_safety_buffer_pct` of battery capacity above min_soc
- **THEN** the safety floor SHALL be capped at min_soc + (max_safety_buffer_pct * capacity)

### Requirement: Solver Respects Export Threshold
The planner adapter MUST map the user's `export_threshold_sek_per_kwh` parameter to the solver configuration. The solver MUST mathematically deduct this threshold from the spot price before making export decisions, preventing micro-cycling for negligible profits.

#### Scenario: Spot price does not clear threshold
- **WHEN** the spot price is only 0.05 SEK higher than the import cost + wear cost, and the `export_threshold` is set to 0.20 SEK
- **THEN** the solver refrains from exporting energy, as the adjusted profit margin is negative

### Requirement: Dynamic Export Threshold Based on Price Volatility and Risk Appetite
The StrategyEngine SHALL calculate `export_threshold_sek_per_kwh` dynamically based on price spread (volatility) and user's `risk_appetite` setting. The calculation SHALL use a continuous function (not step-based) to eliminate threshold gaps.

**Formula:**
```python
# Risk appetite shifts the minimum threshold floor
RISK_BASELINE_SHIFTS = {
    1: 0.15,   # Safe: Never below 0.15 SEK
    2: 0.10,   # Conservative: Floor at 0.10
    3: 0.05,   # Neutral: Floor at 0.05
    4: 0.02,   # Aggressive: Floor at 0.02
    5: 0.00,   # Gambler: Can go to 0.00 on high spread days
}

# Normalize spread: 0.0 at 0.3 SEK, 1.0 at 2.0 SEK
spread_norm = max(0.0, min(1.0, (spread - 0.3) / 1.7))

# Threshold scales from 0.50 (low spread) down to risk-based baseline (high spread)
baseline = RISK_BASELINE_SHIFTS[risk_appetite]
threshold = 0.50 - (0.50 - baseline) * spread_norm
```

**Behavior:**
- At low price spread (< 0.3 SEK): Threshold = 0.50 SEK (conservative, prevents micro-cycling in flat markets)
- At high price spread (> 2.0 SEK): Threshold = risk-based baseline (aggressive users capture more marginal profits)
- Between 0.3 and 2.0 SEK: Linear interpolation
- Risk appetite only affects the floor, not the ceiling
- `wear_cost_sek_per_kwh` and `ramping_cost_sek_per_kw` overrides MUST always be applied alongside the threshold — they remain spread-dependent and are NOT removed by this change

#### Scenario: Flat price day with conservative user
- **GIVEN** price spread of 0.2 SEK and `risk_appetite = 1` (safe)
- **WHEN** the StrategyEngine calculates export threshold
- **THEN** the threshold is 0.50 SEK (high threshold prevents unnecessary cycling)

#### Scenario: Volatile price day with aggressive user
- **GIVEN** price spread of 2.5 SEK and `risk_appetite = 5` (gambler)
- **WHEN** the StrategyEngine calculates export threshold
- **THEN** the threshold is 0.00 SEK (captures all profitable opportunities)

#### Scenario: Moderate volatility with neutral user
- **GIVEN** price spread of 1.0 SEK and `risk_appetite = 3` (neutral)
- **WHEN** the StrategyEngine calculates export threshold
- **THEN** the threshold is approximately 0.24 SEK (balanced protection)

#### Scenario: Continuous scaling eliminates step-function gaps
- **GIVEN** price spread of 0.5 SEK (previously in the "gap")
- **WHEN** the StrategyEngine calculates export threshold for `risk_appetite = 3`
- **THEN** the threshold is approximately 0.38 SEK (no longer falls back to default 0.0)

### Requirement: Solver blocks battery discharge during EV charging
The solver SHALL force battery discharge to zero in any slot where EV charging is active. This SHALL be enforced via a Big-M MILP constraint: `discharge[t] <= (1 - ev_charge[t]) * M`, where `M = max_discharge_kw * slot_hours[t]`. This constraint SHALL only be added when EV optimization is enabled (`ev_enabled = True`). The existing grid-only constraint (`ev_energy[t] <= grid_import[t] + pv + epsilon`) SHALL remain unchanged.

#### Scenario: EV charging slot has zero discharge
- **WHEN** the solver schedules EV charging in slot t (`ev_charge[t] = 1`)
- **THEN** `discharge[t]` is forced to 0.0 by the Big-M constraint

#### Scenario: Non-EV slot allows normal discharge
- **WHEN** the solver does not schedule EV charging in slot t (`ev_charge[t] = 0`)
- **THEN** `discharge[t]` is bounded only by its normal upper bound (`max_discharge_kw * slot_hours`)

#### Scenario: Solver chooses between EV charging and discharge under load pressure
- **WHEN** house load is high and both EV charging and battery discharge would reduce cost
- **THEN** the solver picks the combination that minimizes total cost (may skip EV charging in that slot to allow discharge, or vice versa)
- **AND** load shedding penalty (10,000 SEK/kWh) ensures the solver never sheds load when discharge alone could serve it

#### Scenario: EV disabled users are unaffected
- **WHEN** `ev_enabled` is False
- **THEN** no EV-related discharge constraint is added to the MILP model
- **AND** solver behavior is identical to before this change
