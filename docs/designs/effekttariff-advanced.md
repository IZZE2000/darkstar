# Design: Advanced Effekttariff Profiles (V2)

This document defines the "State of the Art" vision for power tariff management. While V1 (KISS) uses hard limits, V2 uses **Economic Optimization** to decide if a peak is "worth it."

## 1. Core Philosophy: Economic Negotiation

Instead of treating a peak as a "Wall" (Constraint), V2 treats it as a **Variable Cost**.

The Planner (Kepler) will mathematically weigh:
- "Is it cheaper to pay 55 SEK for a 1kW higher peak today, so I can charge my car at -1.00 SEK/kWh?"

## 2. The Tariff Profile (`profiles/tariffs/*.yaml`)

Just like Inverter Profiles, we use declarative YAML to define regional rules.

```yaml
metadata:
  name: "E.ON Syd (Effekttariff)"
  description: "Average of top 3 peaks (07:00-19:00 Mon-Fri)"

rules:
  - type: "average_top_n"
    n: 3
    cron: "0 7 * * 1-5" # Mon-Fri daytime
    price_sek_kw: 55.0
    season: "winter"    # Dec-Feb
  - type: "monthly_max"
    cron: "0 0 * * *"   # All other times
    price_sek_kw: 25.0
```

## 3. Solver Logic: Peak Variables ($P_{max}$)

In the MILP solver, we replace the "Hard Limit" with a dynamic variable:

1.  **Variable:** $P_{max,w}$ (Continuous, >= 0) for each window $w$ in the tariff.
2.  **Constraint:** $	ext{Grid Import}_t / h \leq P_{max,w}$ for all slots $t$ in that window.
3.  **Objective:** Add $(P_{max,w} 	imes 	ext{Tariff Price}_w)$ to the total cost.

### The "Memory" Problem (36h vs 1 Month)
To solve the 1-month window within a 36h planner, we must pass the **Current Peaks List** into the solver as an initial state.
- *If Top-3-Peaks so far are [9kW, 8kW, 7kW]:* The solver knows that setting $P_{max}$ to 6kW today adds **zero cost** to the monthly average. Setting it to 10kW adds a calculated marginal cost.

## 4. Why this is "State of the Art"

1.  **Community Driven:** Users can share profiles for Skellefteå Kraft, Vattenfall, etc.
2.  **Truly Optimal:** It handles "Negative Price" events perfectly. It will intentionally spike the grid import to "Gulp" cheap energy if the profit outweighs the tariff fee.
3.  **Flexible:** It supports Day/Night pricing, Seasonal differences, and complex averaging rules without changing the Python code.

## 5. Implementation Path
- **Prerequisite:** V1 (KISS) must be stable.
- **Phase 1:** Implement "Tariff Profile" loader.
- **Phase 2:** Update `KeplerSolver` to support $P_{max}$ variables and window-aware objective terms.
- **Phase 3:** Create a library of YAML profiles for major Swedish providers.
