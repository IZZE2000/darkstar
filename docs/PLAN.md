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

### [DONE] REV // K23 — Battery Cycling & Economic Valuation Fix

**Goal:** Fix intra-day battery cycling bugs and simplify strategy by removing redundant valuation logic (TVS) in favor of a robust Physical Deficit S-Index.

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

#### Phase 1: Fix Wear Cost Bug [DONE]

**Problem:** Wear cost is currently applied to BOTH charge AND discharge energy, doubling the cost per cycle.
- Config says: `wear_cost_sek_per_kwh: 0.20` (intention: 0.20 SEK per full cycle)
- Current behavior: `(charge[t] + discharge[t]) * 0.20` = 0.40 SEK for 1 kWh cycle
- Expected behavior: 0.20 SEK for 1 kWh cycle

**Solution:** Apply 50% of config value per action (charge OR discharge), so full cycle = 100%.

* [x] Modify `planner/solver/kepler.py:179`
* [x] **Before:** `slot_wear_cost = (charge[t] + discharge[t]) * config.wear_cost_sek_per_kwh`
* [x] **After:** `slot_wear_cost = (charge[t] + discharge[t]) * config.wear_cost_sek_per_kwh * 0.5`
* [x] Add inline comment explaining formula:
```python
# Wear cost modeling: Apply 50% of config value per action (charge OR discharge)
# so that a full cycle (charge + discharge) costs exactly config.wear_cost_sek_per_kwh
# Example: 0.20 SEK/kWh config → 0.10/action → 0.20 total for 1 kWh cycle
slot_wear_cost = (charge[t] + discharge[t]) * config.wear_cost_sek_per_kwh * 0.5
```

* [x] **Verification:**
  * [x] Run `uv run python debugging/test_ramping_values.py`
  * [x] Confirm output shows `Wear (CORRECT): 0.20 SEK` (not 0.40 SEK)
  * [x] Verify 0.05 SEK/kW ramping NOW permits cycling (friction reduced from 0.81 to 0.61 SEK)
  * [x] If 0.05 still blocks, confirm 0.01 works as before

* [x] **Commit:**
```
git commit -m "fix(k23): correct wear cost to apply once per cycle, not per action

- Multiply wear_cost_sek_per_kwh by 0.5 in slot calculation
- Full cycle (charge + discharge) now costs exactly config value
- Reduces friction from 0.40 to 0.20 SEK per kWh cycled
- Addresses REV K23 Phase 1"
```

#### Phase 2: Terminal Value System (TVS) [ABANDONED/REVERT]

**Goal:** Enable economically correct battery valuation so stored energy has intrinsic value.
**Outcome:** Implemented but found to be redundant. The "Blind Spot" is better solved by the S-Index (Physical Deficit) + High Penalties.
**Decision:** Remove TVS to reduce complexity.

* [x] Create `planner/strategy/terminal_value.py`. [REVERTING]
* [x] Integrate into `planner/pipeline.py`. [REVERTING]

#### Phase 3: S-Index Refactor (Physical Deficit) [DONE]

**Goal:** Replace "Fixed Buffer" logic with "Physical Deficit" logic.
**Pivot:** Instead of variable penalties, use a **Hard Soft-Constraint** (High Penalty) for the Safety Floor.

**Design:**
- **Safety Floor (kWh)** = `MinSoC + (Capacity * Deficit_Ratio * Risk_Multiplier) + Weather_Buffer`
- **Penalty:** `200.0 SEK` (Fixed High Penalty) - "Do Not Violate unless impossible".
- **Risk Multipliers (Aggressive):**
  - Risk 4: `0.50x` deficit coverage.
  - Risk 5: `0.00x` deficit coverage (Gambler).

**Tasks:**
* [x] Refactor `planner/strategy/s_index.py` (Physical Deficit).
* [x] Update `planner/pipeline.py` to target Safety Floor.
* [x] **Calibration:** Finalize multipliers (0.50/0.00) and Penalties (200 SEK).

#### Phase 4: Architecture Simplification (Cleanup) [DONE]

**Goal:** Remove the redundant TVS code.

* [x] **Delete:** `planner/strategy/terminal_value.py`.
* [x] **Cleanup:** Remove TVS logic from `planner/pipeline.py`.

#### Phase 5: Internal Telemetry & UI [DONE]

**Goal:** Vizualize the strategy on the Dashboard so the user (and we) can see *why* the agent is acting.

**Metrics to Add (API & UI):**
*   `safety_floor_kwh`: The physical safety floor (min allowed SoC) driven by the deficit.
*   `s_index_deficit_kwh`: The forecasted shortage (Load - PV) explaining *why* the floor is high.
*   *(Existing)* `strategy_factor`: The risk multiplier.

**Tasks:**
* [x] Update `backend/api/routers/services.py` or `telemetry` to expose these new computed values.
* [x] Update `frontend/src/components/dashboard/BatteryCard.tsx` (actually `CommandDomains.tsx`) to display:
  *   "Safety Floor: X kWh"
  *   "Tradable: Y kWh"
  *   "Future Value: Z SEK/kWh"

#### Phase 6: Validation & Cleanup [DONE]

**Goal:** Ensure the system behaves rationally in E2E scenarios.

**Tasks:**
* [x] **Scenario A (High Price Spread):** Verify Risk 5 dumps to `safety_floor` but NOT to 0%.
* [x] **Scenario B (Safety Mode):** Verify Risk 1 maintains high `safety_floor` even if prices are high.
* [x] **Documentation:** Update `ARCHITECTURE.md` with final S-Index logic.
* [x] **Final Commit**

**Success Criteria:**
- Intra-day cycling works (due to Phase 1 fixes).
- End-of-day SoC is economically rational (TVS).
- Safety buffer scales with actual weather risk (S-Index).
