## Context

The `calculate_safety_floor` function (s_index.py:664-781) computes the end-of-horizon target SoC that the MILP solver must respect as a minimum floor. Currently it uses an aggregate deficit ratio: `(total_load - total_pv) / total_load`. When PV exceeds load over the horizon (spring/summer), this ratio is 0.0 and the floor collapses to `min_soc` regardless of risk level. The function receives `df` from `pipeline.py:368` which is joined on price data — so when planning at midday before tomorrow's prices arrive, the horizon may only extend ~11.5h to midnight.

The MILP solver handles all economic optimization (self-consumption vs export vs grid import) correctly. The safety floor's role is to set a meaningful minimum for energy the solver should preserve for the period **beyond** its optimization horizon.

## Goals / Non-Goals

**Goals:**
- Safety floor reflects temporal energy deficit (per-slot load minus PV) instead of aggregate surplus/deficit
- Safety floor covers the 24h window beyond the price horizon using extended load/PV forecasts
- Risk appetite meaningfully scales the safety floor at all times of year
- A minimum floor per risk level prevents collapse to min_soc in any condition

**Non-Goals:**
- Changing the MILP solver logic, export threshold, or wear cost calculations
- Including EV charging or water heating in safety floor (MILP handles these as separate decision variables)
- Changing the `target_under_violation` enforcement mechanism (unidirectional penalty is correct)
- Adding new configuration parameters (reuse existing `risk_appetite`, `max_safety_buffer_pct`)

## Decisions

### Decision 1: Temporal deficit instead of aggregate deficit ratio

Replace `deficit_ratio = (total_load - total_pv) / total_load` with per-slot net deficit: `sum(max(0, load - pv))` for each slot. This captures energy needed from battery when PV is unavailable.

**Why**: The aggregate approach treats 20 kWh of afternoon PV as offsetting 20 kWh of evening load, but the battery must still supply the evening load. The temporal approach naturally handles overnight gaps, cloudy periods, and winter days without special-case logic.

**Alternative considered**: Time-of-day splitting (daytime vs nighttime buckets). Rejected because temporal deficit is simpler and handles all edge cases (cloudy mornings, partial PV days) without defining arbitrary day/night boundaries.

### Decision 2: Look-ahead window = 24h beyond price horizon end

The safety floor calculates temporal deficit over a 24h window starting from where the price data ends. This requires passing extended forecast data (load/PV forecasts that extend beyond the price horizon) to `calculate_safety_floor`.

**Why**: The MILP optimizes everything within the price horizon. The safety floor protects against what the MILP can't see. A 24h look-ahead covers one full day/night cycle beyond the horizon, which shifts naturally as prices arrive (at 13:00, horizon extends to tomorrow midnight, so the safety floor covers the day after tomorrow's overnight).

**Data source**: The pipeline already has access to multi-day load/PV forecasts via `forecast_data` in `input_data`. Currently `prepare_df` truncates this to the price horizon (LEFT join on prices). The safety floor needs the raw forecast data beyond prices.

**Implementation**: Pass the full forecast DataFrame (not truncated to prices) to `calculate_safety_floor`, along with the price horizon end timestamp. The function filters to `[price_horizon_end, price_horizon_end + 24h]` for its deficit calculation.

### Decision 3: Risk appetite scales margin + sets minimum floor

Two mechanisms ensure risk appetite always matters:

1. **Margin on temporal deficit**: Risk multiplier applied to the calculated temporal deficit. Higher risk appetite = lower margin (you trust the forecast more).
2. **Minimum floor**: Absolute minimum buffer above min_soc per risk level. Even with zero temporal deficit (e.g. 24h sunshine forecast beyond horizon), risk level 1 still holds a buffer.

**Risk scaling**:
- Risk 1 (Safety): 30% margin on deficit, minimum 25% capacity above min_soc
- Risk 2 (Conservative): 20% margin, minimum 15% above min_soc
- Risk 3 (Neutral): 15% margin, minimum 10% above min_soc
- Risk 4 (Aggressive): 5% margin, minimum 3% above min_soc
- Risk 5 (Gambler): 0% margin, 0% minimum

The existing `max_safety_buffer_pct` cap (default 20% of capacity) still applies to prevent the floor from exceeding reasonable levels in extended bad weather.

### Decision 4: Keep weather buffer as additive layer

The existing weather buffer logic (temperature, snow, cloud cover) remains as an additive layer on top of the temporal deficit reserve. It handles short-term weather risks that the forecast-based deficit may not fully capture.

## Risks / Trade-offs

- **[Forecast data availability]** If extended forecasts beyond the price horizon are unavailable, the safety floor falls back to a calculation based on the available horizon only, using the minimum floor per risk level as a baseline. → Mitigation: Log a warning when extended data is missing.
- **[Max buffer cap may be too low]** With `max_safety_buffer_pct = 20%` (6.84 kWh on a 34.2 kWh battery), winter scenarios with high temporal deficit may hit the cap. → Mitigation: The cap is configurable; document that users in extreme climates may want to raise it.
- **[Behavioral change for existing users]** Users currently on risk level 5 (Gambler) with PV surplus see no change (0% margin, 0% minimum). Users on risk 1-4 will see higher safety floors in spring/summer. → Mitigation: This is the desired behavior — the current floor of min_soc in spring is a bug.
