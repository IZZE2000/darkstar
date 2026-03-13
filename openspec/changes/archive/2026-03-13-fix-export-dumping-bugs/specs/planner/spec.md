## MODIFIED Requirements

### Requirement: End-of-Horizon SoC Target acts as a Minimum Floor (Safety Floor)
The solver SHALL enforce the end-of-horizon `target_soc` constraint solely as a minimum floor. It SHALL penalize the solver heavily if the final State of Charge (SoC) is *below* the target (`target_under_violation`). The solver SHALL NOT apply any penalty (`target_over_violation`) if the final SoC exceeds the target, allowing the system to naturally preserve excess free or cheap energy beyond the minimum safety requirement.

#### Scenario: Excess Solar Energy at End of Horizon
- **WHEN** the battery receives abundant solar energy and covering all loads leaves the end-of-horizon SoC higher than the calculated Safety Floor target
- **THEN** the solver finishes the horizon with the high SoC without attempting to force-dump the energy into the grid to hit the target

## ADDED Requirements

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
