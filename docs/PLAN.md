# Darkstar Energy Manager: Active Plan

**Vision: From Calculator to Agent**
Darkstar is transitioning from a deterministic optimizer (v1) to an intelligent energy agent (v2). It does not just optimize based on static config; it observes context (Weather, Vacation, Prices), predicts outcomes (Aurora ML), and actively strategizes (Strategy Engine) to maximize efficiency and comfort.

---

## Revision Naming Conventions

| Prefix | Area | Examples |
|--------|------|----------|
| **K** | Kepler (MILP solver) | K1-K19 |
| **E** | Executor | E1 |
| **A** | Aurora (ML) | A25-A29 |
| **H** | History/DB | H1 |
| **O** | Onboarding | O1 |
| **UI** | User Interface | UI1, UI2 |
| **DS** | Design System | DS1 |
| **F** | Fixes/Bugfixes | F1-F6 |
| **DX** | Developer Experience | DX1 |
| **ARC** | Architecture | ARC1-ARC* |

---

## 🤖 AI Instructions (Read First)

1.  **Structure:** This file is a **chronological stream**. Newest items are at the **bottom**.

2.  **No Reordering:** Never move items. Only update their status or append new items.

3.  **Status Protocol:**

    -   Update the status tag in the Header: `### [STATUS] REV // ID00 — Title`

    -   Allowed Statuses: `[DRAFT]`, `[PLANNED]`, `[IN PROGRESS]`, `[DONE]`, `[PAUSED]`, `[OBSOLETE]`.

4.  **New Revisions:** Always use the template below.

5.  **Cleanup:** When this file gets too long (>10 completed REV's), notify the user.


### Revision Template

```

### [STATUS] REV // ID — Title

**Goal:** Short description of the objective.
**Context:** Short description of the context and issues.

**Plan:**

#### Phase 1: [STATUS]
* [ ] Step 1
* [ ] Step 2

#### Phase 2: [STATUS]
* [ ] Step 1
* [ ] Step 2

```

---

## REVISION STREAM:

---

### [PLANNED] REV // K22 — Effekttariff (Active Guard)

**Goal:** Implement a dual-layer strategy (Planner + Executor) to minimize peak power usage ("Effekttariff").

**Plan:**

#### Phase 1: Configuration & Entities [PLANNED]
* [ ] Add `grid.import_breach_penalty_sek` (Default: 5000.0) to `config.default.yaml`.
* [ ] Add `grid.import_breach_penalty_enabled` (Default: false) to `config.default.yaml`.
* [ ] Add `grid.import_breach_limit_kw` (Default: 11.0) for the hard executor limit.
* [ ] Add override entities to `executor.config`.

#### Phase 2: Planner Logic (Economic) [PLANNED]
* [ ] **Planner Logic:** Pass the penalty cost to Kepler if enabled.
* [ ] **Re-planning:** Trigger re-plan if penalty configuration changes.

#### Phase 3: Executor Active Guard (Reactive) [PLANNED]
* [ ] **Monitor:** In `executor/engine.py` `_tick`, check `grid_import_power` vs `import_breach_limit_kw`.
* [ ] **Reactive Logic:**
    *   If Breach > Limit:
        *   Trigger `ForceDischarge` on Battery (Max power).
        *   Trigger `Disable` on Water Heating.
        *   Log "Grid Breach Detected! Engaging Emergency Shedding".
* [ ] **Recovery:** Hysteresis logic to release overrides when grid import drops.
* [ ] **Frontend:** Add controls to `Settings > Grid`.

---

### [PLANNED] REV // UI7 — Mobile Polish & Extensible Architecture

**Goal:** Improve mobile usability, fix chart tooltip/legend issues, and make PowerFlowCard extensible for future nodes (EV, heat pump, etc.) using a Node Registry pattern.

**Context:**
- Current PowerFlowCard hardcodes 5 nodes (solar, house, battery, grid, water) - adding EV requires refactoring
- Chart tooltips on mobile overlap chart content (screen too small)
- Tooltip color boxes render as white with color stroke (hard to scan)
- Dotted SoC lines in legend are unclear on mobile

**Plan:**

#### Phase 1: PowerFlowCard Node Registry [PLANNED]
* [ ] **Define Node Registry Types:** Create extensible registry structure:
  ```typescript
  interface FlowNodeConfig {
    id: 'solar' | 'house' | 'battery' | 'grid' | 'water' | 'ev'
    configKey: string  // e.g., 'system.has_solar', 'system.has_water_heater'
    position: { x: number; y: number }
    dataAccessor: (data: PowerFlowData) => NodeData
    connections: string[]  // defines valid flow connections
  }
  ```
* [ ] **Update PowerFlowCard Props:** Add `systemConfig?: Partial<SystemConfig>` prop to receive config
* [ ] **Config-Driven Enabled Check:** Replace hardcoded nodes with registry filtered by config flags:
  * `system.has_solar` → solar node
  * `system.has_battery` → battery node
  * `system.has_water_heater` → water node
* [ ] **Auto-positioning:** Calculate node positions dynamically based on enabled node count
* [ ] **EV Placeholder:** Add EV node entry (`configKey: 'system.has_ev'`, disabled by default)
* [ ] **Particle Streams:** Only render connections between enabled nodes

#### Phase 2: ChartCard Mobile UX [PLANNED]
* [ ] **Bottom Sheet Tooltip:** Replace standard Chart.js tooltip with fixed bottom overlay on mobile:
  * Trigger: Tap any point on chart
  * Position: Fixed overlay at bottom of chart container (thumb-reachable)
  * Desktop: Keep current tooltip behavior
* [ ] **Custom Tooltip Plugin:** Create React-based tooltip component rendered by Chart.js external plugin
* [ ] **Filled Color Boxes:** Fix tooltip color swatches:
  ```typescript
  // Instead of white box with stroke → solid filled box
  backgroundColor: context.dataset.borderColor,
  borderColor: context.dataset.borderColor,
  borderWidth: 2,
  borderRadius: 4,
  ```

#### Phase 3: Legend Polish [PLANNED]
* [ ] **Circle Markers Only:** Replace dotted SoC lines with circle markers:
  * SoC Target: Hollow circle (planned = target)
  * SoC Actual: Filled circle (actual = achieved)
* [ ] **Remove borderDash:** Set `pointStyle: 'circle'` with appropriate `pointRadius`
* [ ] **Mobile Legend Test:** Verify legibility on small screens

#### Phase 4: Dashboard Integration [PLANNED]
* [ ] **Update Dashboard.tsx:** Pass `system` config to PowerFlowCard component:
  ```typescript
  <PowerFlowCard data={flowData} systemConfig={config.system} />
  ```
* [ ] **Mobile Viewport Detection:** Add responsive hook for tooltip mode switching
* [ ] **Overlay Menu Mobile:** Ensure toggle buttons are touch-friendly (44px+ tap targets)

#### Phase 5: Testing & Validation [PLANNED]
* [ ] **Feature Combination Testing:** Verify conditional rendering works for:
  * Solar + Battery + Water (full system)
  * Solar + Battery only (no water)
  * Solar + Water only (no battery)
  * Battery + Water only (no solar)
  * Solar only (minimal system)
* [ ] **Regression Test:** Verify desktop tooltip/legend still works correctly
* [ ] **Mobile Test:** Test bottom sheet tooltip on various screen sizes (320px-428px)

---

### [PLANNED] REV // A24 — Production Model Deployment

 **Goal:** Implement a "Seed & Drift" deployment strategy for ML models to solve Git conflicts, Docker persistence, and eliminate dangerous model duplication.

 **Context:**
 1.  **Duplicate Tracking:** We currently track models in *both* `ml/models/*.lgb` (Stale, Jan 22) and `data/ml/models/*.lgb` (Fresh, Jan 27). This causes confusion and "clean slate" failures.
 2.  **Git Conflicts:** Users training locally (`data/ml/models`) cannot pull because Git tracks those files.
 3.  **Docker Persistence:** `run.sh` logic is brittle and fails to reliably bootstrap defaults.

 **Plan:**

 #### Phase 1: Promote & Restructure [DONE]
 * [x] **Promote Fresh Models:** Copy the *latest* models from `data/ml/models/*.lgb` to `ml/models/defaults/` (New Source of Truth).
 * [x] **Purge Stale Models:** Delete the old `ml/models/*.lgb` files.
 * [x] **Update Gitignore:**
     *   Ignore `data/ml/models/*.lgb` (Active runtime).
     *   Allow `ml/models/defaults/*.lgb` (Immutable defaults).
 * [x] **Commit:** Push the new structure, effectively "freezing" the latest local training as the new factory default.

 #### Phase 2: Robust Bootstrapping [DONE]
 * [x] **Create `ml/bootstrap.py`:**
     *   **Path Logic:** Use `Path(__file__)` relative paths to safely locate defaults in both Docker (`/app/ml/models/defaults`) and Local (`./ml/models/defaults`).
     *   **Logic:** `ensure_active_models()` checks if `data/ml/models` is empty. If so, copy from defaults. If not, **touch nothing**.
     *   **Defaults Backup:** Always copy defaults to `data/ml/models/defaults/` for potential "Factory Reset" features.
 * [x] **Integration:** Call duplicate-safe bootstrap in `backend/main.py`.

 #### Phase 3: Deployment Config [DONE]
 * [x] **Dockerfile:** Add `COPY ml/models/defaults/ /app/ml/models/defaults/`.
 * [x] **run.sh:** Remove lines 283-309 (Bash bootstrap). Rely 100% on Python.
 * [x] **Rollback Safety:** If bootstrap fails, log "CRITICAL" but allow app start (will revert to heuristic/Open-Meteo).

 #### Phase 4: Validation [PLANNED]
 * [ ] **Manual Rollback Test:** Simulate corrupt models and verify app survives.
 * [ ] **Fresh Start Test:** Move `data/ml/models` aside, restart, verify defaults appear.

---

### [IN PROGRESS] REV // K23 — Battery Cycling & Economic Valuation Fix

**Goal:** Fix two critical bugs blocking intra-day battery cycling and implement Terminal Value System for economically correct battery valuation.

**Context:**
Beta tester (v2.5.11-beta) reported "flat schedule" (no charging/cycling) with Risk Appetite 5 despite 1.37 SEK price spread and being below target SoC (5% actual vs 6% target). Investigation revealed TWO separate issues requiring fixes.

**Plan:**

#### Phase 0: Root Cause Investigation [DONE]

**Scripts Created:**
- `debugging/reproduce_beta_flat_schedule.py` - Reproduces beta scenario with real SE4 prices
- `debugging/detailed_cost_breakdown.py` - Manual economic calculations
- `debugging/why_no_cycling.py` - Investigates cycling economics
- `debugging/test_terminal_value_fix.py` - Tests if TVS fixes cycling (it doesn't!)
- `debugging/test_no_ramping_cost.py` - Isolates ramping cost impact
- `debugging/test_ramping_values.py` - Tests optimal ramping value with gap analysis

**Issue #1: Target Miss (Terminal Value = 0)**
- Solver pays 0.32 SEK penalty instead of charging 0.16 kWh at 2.25 SEK (costs 0.43 SEK)
- Economically rational under current system, but undesirable behavior
- **Fix:** Implement Terminal Value System so stored energy has intrinsic value

**Issue #2: No Intra-Day Cycling (Wear + Ramping Costs Too High)**
- Theoretical profit: 1.37 SEK spread - 0.38 SEK efficiency loss = 0.99 SEK gross
- **BUG 1 - Wear Cost Doubled:** `(charge[t] + discharge[t]) * 0.20` applies wear to BOTH actions
  - Expected: 0.20 SEK per full cycle
  - Actual: 0.40 SEK per full cycle (DOUBLE!)
  - Code: `planner/solver/kepler.py:179`
- **BUG 2 - Ramping Cost Too High:** 0.05 SEK/kW creates ~0.41 SEK friction per cycle
  - Combined friction: 0.40 (wear) + 0.41 (ramp) = 0.81 SEK > 0.59 SEK profit → BLOCKS cycling
  - Testing showed 0.01 SEK/kW enables cycling while preventing sawtooth patterns
  - Gap analysis: 0.00 produces `C.C` gaps, 0.01 produces smooth `CCC` blocks

**Terminal Value Testing Results:**
- Terminal value DOES fix target miss (charges 0.17 kWh to hit 0.96 kWh target) ✅
- Terminal value does NOT fix intra-day cycling (because cycle ends at same SoC = zero delta) ❌
- Cycling issue is purely cost-based, not terminal value related

**Key Findings:**
1. Two separate bugs compound to block cycling
2. Fix wear cost bug FIRST (highest impact: saves 0.20 SEK per cycle)
3. Ramping cost 0.01 SEK/kW is optimal (enables cycling + prevents sawtooth)
4. Terminal Value System still needed for target miss issue

#### Phase 1: Fix Wear Cost Bug [PLANNED]

**Problem:** Wear cost is currently applied to BOTH charge AND discharge energy, doubling the cost per cycle.
- Config says: `wear_cost_sek_per_kwh: 0.20` (intention: 0.20 SEK per full cycle)
- Current behavior: `(charge[t] + discharge[t]) * 0.20` = 0.40 SEK for 1 kWh cycle
- Expected behavior: 0.20 SEK for 1 kWh cycle

**Solution:** Apply 50% of config value per action (charge OR discharge), so full cycle = 100%.

* [ ] Modify `planner/solver/kepler.py:179`
* [ ] **Before:** `slot_wear_cost = (charge[t] + discharge[t]) * config.wear_cost_sek_per_kwh`
* [ ] **After:** `slot_wear_cost = (charge[t] + discharge[t]) * config.wear_cost_sek_per_kwh * 0.5`
* [ ] Add inline comment explaining formula:
```python
# Wear cost modeling: Apply 50% of config value per action (charge OR discharge)
# so that a full cycle (charge + discharge) costs exactly config.wear_cost_sek_per_kwh
# Example: 0.20 SEK/kWh config → 0.10/action → 0.20 total for 1 kWh cycle
slot_wear_cost = (charge[t] + discharge[t]) * config.wear_cost_sek_per_kwh * 0.5
```

* [ ] **Verification:**
  * [ ] Run `uv run python debugging/test_ramping_values.py`
  * [ ] Confirm output shows `Wear (CORRECT): 0.20 SEK` (not 0.40 SEK)
  * [ ] Verify 0.05 SEK/kW ramping NOW permits cycling (friction reduced from 0.81 to 0.61 SEK)
  * [ ] If 0.05 still blocks, confirm 0.01 works as before

* [ ] **Commit:**
```
git commit -m "fix(k23): correct wear cost to apply once per cycle, not per action

- Multiply wear_cost_sek_per_kwh by 0.5 in slot calculation
- Full cycle (charge + discharge) now costs exactly config value
- Reduces friction from 0.40 to 0.20 SEK per kWh cycled
- Addresses REV K23 Phase 1"
```

#### Phase 2: Implement Terminal Value System [PLANNED]

**Goal:** Enable economically correct battery valuation so stored energy has intrinsic value based on future prices and risk appetite.

**Design:**
- Terminal value = `avg(future_prices_in_horizon) × RISK_MULTIPLIER[risk_appetite]`
- Applied to final SoC only: `terminal_credit = soc[T] × terminal_value_sek_kwh`
- Higher risk = lower multiplier = more willing to discharge now
- Lower risk = higher multiplier = prefer holding energy for future

**Risk Multiplier Reasoning:**

| Risk Level | Multiplier | Interpretation | Behavior |
|------------|-----------|----------------|----------|
| 1 (Safety) | 1.50× | Battery worth 150% of future avg | Very conservative - hold energy for emergencies |
| 2 (Caution) | 1.25× | Battery worth 125% of future avg | Conservative - prefer holding over selling |
| 3 (Neutral) | 1.00× | Battery worth exactly future avg | Balanced - fair economic valuation |
| 4 (Bold) | 0.75× | Battery worth 75% of future avg | Aggressive - willing to discharge for smaller spreads |
| 5 (Gambler) | 0.50× | Battery worth 50% of future avg | Very aggressive - maximize immediate profit |

**Rationale:**
- Risk 1-2: Users prioritize backup power over profit → overvalue stored energy
- Risk 3: Pure economic optimization → energy worth exactly future opportunity cost
- Risk 4-5: Users prioritize arbitrage profit → undervalue stored energy to enable cycling

**Implementation Steps:**

* [ ] **Step 2.1:** Create `planner/strategy/terminal_value.py`
```python
"""
Terminal Value System (Rev K23)
Calculate economic value of end-of-horizon battery SoC.
"""
from typing import List

# Risk appetite to terminal value multiplier mapping
RISK_MULTIPLIERS = {
    1: 1.50,  # Safety: Overvalue stored energy (backup priority)
    2: 1.25,  # Caution: Modest overvalue (conservative)
    3: 1.00,  # Neutral: Fair value (pure economics)
    4: 0.75,  # Bold: Modest undervalue (pro-cycling)
    5: 0.50,  # Gambler: Aggressive undervalue (max cycling)
}

def calculate_terminal_value(
    import_prices_sek_kwh: List[float],
    risk_appetite: int = 3,
) -> float:
    """
    Calculate terminal value (SEK/kWh) for battery SoC at end of horizon.

    Args:
        import_prices_sek_kwh: Future import prices in planning horizon
        risk_appetite: 1 (Safety) to 5 (Gambler)

    Returns:
        Terminal value in SEK/kWh

    Examples:
        >>> calculate_terminal_value([2.0, 3.0, 4.0], risk_appetite=3)
        3.0  # avg(2,3,4) × 1.0 = 3.0
        >>> calculate_terminal_value([2.0, 3.0, 4.0], risk_appetite=5)
        1.5  # avg(2,3,4) × 0.5 = 1.5
    """
    if not import_prices_sek_kwh:
        return 0.0

    avg_price = sum(import_prices_sek_kwh) / len(import_prices_sek_kwh)
    multiplier = RISK_MULTIPLIERS.get(risk_appetite, 1.0)

    terminal_value = avg_price * multiplier

    # Debug logging
    print(f"[TVS] Horizon prices: min={min(import_prices_sek_kwh):.2f}, "
          f"max={max(import_prices_sek_kwh):.2f}, avg={avg_price:.2f}")
    print(f"[TVS] Risk {risk_appetite} → multiplier {multiplier}× → "
          f"terminal_value={terminal_value:.2f} SEK/kWh")

    return terminal_value
```

* [ ] **Step 2.2:** Integrate into `planner/pipeline.py`
  * [ ] Find where `KeplerConfig` is created (search for `config_to_kepler_config`)
  * [ ] Import terminal value calculator: `from planner.strategy.terminal_value import calculate_terminal_value`
  * [ ] Extract prices from `df['import_price_sek_kwh'].tolist()`
  * [ ] Get `risk_appetite` from `planner_config.get('risk_appetite', 3)`
  * [ ] Calculate: `terminal_value = calculate_terminal_value(prices, risk_appetite)`
  * [ ] Pass to adapter in `overrides` dict: `overrides={'terminal_value_sek_kwh': terminal_value}`

* [ ] **Step 2.3:** Update `planner/solver/adapter.py:193-197`
  * [ ] Current code already reads `terminal_value_sek_kwh` from overrides (line 193)
  * [ ] Verify it's passed correctly to `KeplerConfig` (line 265)
  * [ ] No changes needed - already handles dynamic terminal value!

* [ ] **Step 2.4:** Keep safety backstop
  * [ ] Do NOT remove `target_soc_penalty_sek` - keep as belt-and-suspenders
  * [ ] Terminal value handles economics, penalty handles edge cases
  * [ ] Can reduce penalty later if TVS proves sufficient

* [ ] **Verification:**
  * [ ] Run `uv run python debugging/test_terminal_value_fix.py`
  * [ ] Confirm Risk 5 now charges to target (0.96 kWh) with TVS enabled
  * [ ] Test all risk levels 1-5:
    * [ ] Risk 1: Should hold energy aggressively (minimal discharge)
    * [ ] Risk 3: Should show balanced behavior
    * [ ] Risk 5: Should discharge aggressively but still hit target
  * [ ] Verify terminal value logging shows correct multipliers
  * [ ] Check final SoC meets target in Scenario A (before 13:00)

* [ ] **Commit:**
```
git commit -m "feat(k23): implement terminal value system for economic SoC valuation

- Create planner/strategy/terminal_value.py with risk-based multipliers
- Risk 1-5 map to 1.5×/1.25×/1.0×/0.75×/0.5× future avg price
- Integrate into pipeline.py for dynamic calculation
- Keep target_soc_penalty as safety backstop
- Addresses REV K23 Phase 2

Multiplier reasoning:
- Low risk (1-2): Overvalue stored energy for backup priority
- Neutral (3): Fair economic value = future opportunity cost
- High risk (4-5): Undervalue to enable aggressive cycling"
```

#### Phase 3: Update Ramping Cost Settings UI [PLANNED]

* [ ] Edit `frontend/src/pages/settings/types.ts` line 792
* [ ] **Before:**
```typescript
helper: 'Penalty for rapid battery power changes (higher = smoother power flow, reduces "sawtooth" behavior).',
```
* [ ] **After:**
```typescript
helper: 'Penalty for rapid battery power changes. Prevents sawtooth patterns (C.C.C) when too low. Lower values (0.01) enable aggressive arbitrage cycling but allow some gaps. Higher values (0.05+) create perfectly smooth blocks but may block small spreads. Recommended: 0.01-0.02 SEK/kW for active cycling, 0.03-0.05 SEK/kW for conservative operation.',
```

* [ ] **Verification:**
  * [ ] Start frontend dev server: `cd frontend && pnpm dev`
  * [ ] Navigate to Settings → Parameters → Arbitrage & Economics → Advanced Tuning
  * [ ] Hover over "Ramping Cost" field
  * [ ] Confirm tooltip shows updated guidance text
  * [ ] Verify line breaks and formatting render correctly

* [ ] **Commit:**
```
git commit -m "docs(k23): clarify ramping cost impact on battery cycling behavior

- Update tooltip to explain sawtooth prevention vs cycling trade-off
- Add recommended ranges: 0.01-0.02 (active) vs 0.03-0.05 (conservative)
- Addresses REV K23 Phase 3"
```

#### Phase 4: E2E Validation [PLANNED]

* [ ] **Step 4.1:** Update `debugging/reproduce_beta_flat_schedule.py`
  * [ ] Modify `get_config()` to accept `terminal_value_sek_kwh` param
  * [ ] Import fixed wear cost logic (or wait for Phase 1 fix to merge)
  * [ ] Add test case with TVS enabled:
```python
# Test 4: Fixed System (Wear Fix + TVS + 0.01 Ramping)
config4 = get_config(
    ramping_cost=0.01,
    terminal_value_sek_kwh=calculate_terminal_value(prices, risk_appetite=5)
)
```

* [ ] **Step 4.2:** Run full test suite
  * [ ] Execute: `uv run python debugging/reproduce_beta_flat_schedule.py`
  * [ ] Capture output to `debugging/validation_output_k23.txt`

* [ ] **Success Criteria:**
  * [ ] ✅ Scenario A (before 13:00): Charges to target (0.96 kWh)
  * [ ] ✅ Scenario A: Shows intra-day cycling (charge + discharge > 0.5 kWh)
  * [ ] ✅ Scenario A: Gap analysis shows smooth blocks (`CCC...DDDD`)
  * [ ] ✅ Scenario B (after 13:00): Maintains existing cycling behavior
  * [ ] ✅ Both scenarios: Final SoC ≥ target (no penalty paid)
  * [ ] ✅ Wear cost output: 0.20 SEK (not 0.40 SEK)
  * [ ] ✅ Total friction: ≤0.25 SEK per kWh cycled

* [ ] **Commit:**
```
git commit -m "test(k23): validate wear fix + TVS + ramping changes

- Update reproduce_beta_flat_schedule.py with fixed system tests
- Confirm cycling activates in Scenario A (before 13:00)
- Verify smooth block patterns (no sawtooth)
- Validate all success criteria met
- Addresses REV K23 Phase 4"
```

#### Phase 5: Documentation [PLANNED]

* [ ] **Step 5.1:** Update `docs/ARCHITECTURE.md`
  * [ ] Add new section: "Terminal Value System (Rev K23)"
  * [ ] Document risk multiplier table and reasoning
  * [ ] Explain wear cost modeling (0.5× per action = 1× per cycle)
  * [ ] Add ramping cost guidance (when to use 0.01 vs 0.05)

* [ ] **Step 5.2:** Update code comments
  * [ ] `planner/solver/kepler.py:179` - Already done in Phase 1
  * [ ] `config.default.yaml:194` - Add ramping cost guidance:
```yaml
ramping_cost_sek_per_kw: 0.01  # Prevents sawtooth (C.C.C) patterns.
                                # 0.01-0.02: Active cycling, some gaps OK
                                # 0.03-0.05: Smooth blocks, may block small spreads
```

* [ ] **Step 5.3:** Archive investigation scripts
  * [ ] Create `debugging/archive/k23/`
  * [ ] Move all K23 scripts: `mv debugging/{detailed_cost_breakdown,why_no_cycling,test_terminal_value_fix,test_no_ramping_cost,test_ramping_values}.py debugging/archive/k23/`
  * [ ] Keep `reproduce_beta_flat_schedule.py` in main debugging/ (useful for regression tests)

* [ ] **Step 5.4:** Update PLAN.md
  * [ ] Mark all K23 phases as [DONE]
  * [ ] Move entire REV K23 section to `docs/CHANGELOG_PLAN.md` (prepend to top)
  * [ ] Update CHANGELOG entry date to completion date

* [ ] **Commit:**
```
git commit -m "docs(k23): document terminal value system and cost modeling fixes

- Add TVS design to ARCHITECTURE.md with risk multiplier reasoning
- Document wear cost formula (0.5× per action)
- Add ramping cost guidance to config.default.yaml
- Archive investigation scripts to debugging/archive/k23/
- Move completed K23 plan to CHANGELOG_PLAN.md
- Addresses REV K23 Phase 5"
```

**Success Criteria:**
- Beta tester at 5% SoC charges to target even at 3.20 SEK prices (terminal value fix) ✅
- Intra-day cycling activates with ≥0.60 SEK net spread after wear fix (was 0.80 SEK) ✅
- No sawtooth patterns with 0.01 SEK/kW ramping (gap analysis confirms) ✅
- Risk levels 1-5 show expected progression (conservative → aggressive) ✅
- All tests pass with fixed code ✅
