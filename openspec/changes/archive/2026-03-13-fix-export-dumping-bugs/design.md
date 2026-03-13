## Context

**Bug 1 — Force-dumping:** The Kepler solver applies a bidirectional penalty to the end-of-horizon SoC target. The `target_over_violation` term penalises the solver for finishing above the Safety Floor, which turns it from a minimum floor into a hard ceiling. Abundant solar energy causes the solver to dump energy at zero or negative prices rather than hold it.

**Bug 2 — Export threshold missing:** The user's `export_threshold_sek_per_kwh` config parameter is defined in `KeplerConfig` and actively used by the solver, but the mapping line in `adapter.py`'s `config_to_kepler_config()` was accidentally removed in a refactor. The field therefore always defaults to `0.0`, making any export appear profitable regardless of the user's threshold setting.

**Bug 3 — Water objective duplication:** The objective function assembly in `kepler.py` duplicates two terms: the `water_block_start_penalty_sek` term and the water scheduling symmetry-breaker (`water_heat[t] * t * 1e-5`) are each added twice. This doubles those costs for all users with water heating enabled, silently distorting the solver's decisions.

## Goals / Non-Goals

**Goals:**
- Stop the solver from force-dumping free solar energy at zero/negative prices to hit the Safety Floor.
- Ensure the solver respects the user's `export_threshold_sek_per_kwh` parameter.
- Fix the doubled water heating objective terms so the solver calculates water heating costs correctly.
- Add regression tests that prevent all three bugs from silently regressing.

**Non-Goals:**
- We are NOT removing the Safety Floor. The `target_under_violation` constraint remains to ensure the solver meets the minimum required SoC.
- We are NOT changing the underlying logic of the `StrategyEngine` (deprecated).
- We are NOT changing water heating comfort levels, penalties, or user-facing behaviour — only removing the code duplication.

## Decisions

**1. Remove `target_over_violation` from `kepler.py`:**
- **Rationale:** The Safety Floor must act as a true minimum floor, not a target. The solver should never be penalised for holding more free energy than required. The slot-by-slot economics (import cost, export revenue, wear cost) already cause the solver to discharge or export when it is genuinely profitable — the over-target penalty was fighting against this.
- **Behavioral safety:** In the absence of the penalty, the solver will still discharge when there is a profitable export window or a cheap overnight charge to arbitrage. It will simply no longer dump free solar at zero price to satisfy an artificial ceiling. The `target_under_violation` penalty (the actual Safety Floor) is fully preserved.
- **Alternative considered:** Tuning down the penalty. Rejected — any non-zero upward penalty on a free resource is fundamentally wrong in principle.

**2. Restore `export_threshold_sek_per_kwh` in `adapter.py`:**
- **Rationale:** The line mapping this value to `KeplerConfig` was accidentally removed. Restoring it is a one-line fix.

**3. Remove duplicate water objective terms in `kepler.py`:**
- **Rationale:** The `water_block_start_penalty_sek` term and the symmetry-breaker tiebreaker are each assembled twice in the objective function's `pulp.lpSum(...)` call. This is a straightforward deduplication. No functional change other than correcting the intended cost weighting.

**4. Implement Dynamic Export Threshold in StrategyEngine:**
- **Rationale:** The existing step-function logic (if spread > 1.5 / elif spread < 0.5) creates a problematic gap where spread between 0.5-1.5 SEK falls back to default 0.0 threshold. This causes unwanted micro-cycling on moderately volatile days. A continuous function provides smooth protection across all market conditions.
- **Formula Design:**
  - **High threshold at low spread (0.0-0.3 SEK):** 0.50 SEK — prevents micro-cycling in flat markets
  - **Low threshold at high spread (>2.0 SEK):** Risk-based baseline (0.00-0.15 SEK) — captures profitable opportunities
  - **Continuous interpolation:** Linear scaling between 0.3 and 2.0 SEK spread eliminates step-function cliffs
  - **Risk appetite integration:** Shifts the floor (minimum threshold) based on user preference, not the ceiling. Safe users (risk=1) always keep at least 0.15 SEK margin; gamblers (risk=5) can go to 0.00 on volatile days.
- **KISS Principle:** Single formula, two inputs (spread, risk), no magic numbers. Easy to understand, test, and tune.
- **Production Grade:** Bounded outputs (never >0.50, never <risk_floor), deterministic, well-documented behavior.

## Risks / Trade-offs

- **Risk (Bug 1 fix):** Without an over-target penalty, the solver might hold energy that could be profitably exported.
  - **Mitigation:** Standard slot economics handle this. If export spread covers wear and taxes, the solver will organically discharge. The penalty was preventing this natural optimization.
- **Risk (Bug 3 fix):** Removing the duplicated terms halves the effective weight of those specific penalties.
  - **Mitigation:** The duplicated terms were never intentional — halving them restores the weights that were designed and tuned. No user-facing comfort settings change.
