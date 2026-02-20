# Darkstar Energy Manager: Active Plan

**Vision: From Calculator to Agent**
Darkstar is transitioning from a deterministic optimizer (v1) to an intelligent energy agent (v2). It does not just optimize based on static config; it observes context (Weather, Vacation, Prices), predicts outcomes (Aurora ML), and actively strategizes (Strategy Engine) to maximize efficiency and comfort.

---

| Prefix  | Area                 |
| ------- | -------------------- |
| **K**   | Kepler (MILP solver) |
| **E**   | Executor             |
| **A**   | Aurora (ML)          |
| **H**   | History/DB           |
| **O**   | Onboarding           |
| **UI**  | User Interface       |
| **DS**  | Design System        |
| **F**   | Fixes/Bugfixes       |
| **DX**  | Developer Experience |
| **ARC** | Architecture         |
| **IP**  | Inverter Profiles    |

Check this document or `docs/CHANGELOG_PLAN.md` for previous revisions.

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

### [DRAFT] REV // K25 — EV Discharge Protection via Actual Power Monitoring

**Goal:** Add real-time detection of actual EV power consumption to block battery discharge when EV is charging, regardless of whether the charging was triggered by Darkstar's schedule or external sources (manual HA trigger, Tesla app, etc.).

**Context:**
Currently, the executor only blocks battery discharge when the schedule indicates EV should be charging (`slot.ev_charging_kw > 0.1`). This means if a user manually starts EV charging through Home Assistant or another system, the battery can still discharge to the EV because Darkstar doesn't detect the actual power flow. This creates a safety gap where energy can leave the house battery to the car when it shouldn't.

**Current Implementation:**
- Planner level (`planner/solver/kepler.py:202-209`): Optimization ensures EV charging can only use grid + PV
- Executor level (`executor/engine.py:1137-1151`): Blocks discharge when schedule says EV should charge
- **Gap:** No detection of actual EV power draw from external sources

**Proposed Solution:**
Add a second layer of protection that monitors actual EV power consumption via the `LoadDisaggregator` (which already tracks all configured EV charger power sensors). When any EV is consuming power (> threshold), force battery discharge to 0 regardless of the schedule.

**Plan:**

#### Phase 1: Backend - Detect Actual EV Power [DRAFT]
* [ ] Add `get_total_ev_power()` method to `LoadDisaggregator` class to aggregate power from all registered EV chargers
* [ ] Update `executor/engine.py` to query actual EV power from disaggregator during decision making
* [ ] Modify discharge blocking logic to check: `if scheduled_ev_charge OR actual_ev_power > 0.1 kW: block_discharge()`
* [ ] Add logging: "EV detected consuming X kW - blocking battery discharge"

#### Phase 2: Testing [DRAFT]
* [ ] Create unit test: Manual EV trigger via HA sensor → discharge blocked
* [ ] Create unit test: Scheduled EV charging → discharge blocked (existing behavior)
* [ ] Create unit test: No EV charging → discharge allowed normally
* [ ] Run `uv run ruff check .` for linting
* [ ] Run `uv run python -m pytest tests/ -v -k ev` for EV-related tests

#### Phase 3: Documentation [DRAFT]
* [ ] Update executor architecture docs if they mention EV discharge blocking
* [ ] Add note about dual-layer protection (schedule + actual power detection)

---

### [DRAFT] REV // A25 — Fix Forecast Timestamp Alignment Bug

**Goal:** Fix the critical bug where load and PV forecasts show zeros and unexpected gaps due to timestamp misalignment between forecast generation and price slots.

**Context:**
A Fronius beta tester observes completely different load/PV forecasts between consecutive planning runs seconds apart. Load forecast shows huge gaps with zero values; PV forecast plummets unexpectedly. These should be identical between runs.

**Root Cause Analysis:**
The bug is in `ml/forward.py:94-98`. The code generates forecasts starting at the **next** 15-minute slot boundary (e.g., 09:15 if current time is 09:01), but price slots start at the **current** slot boundary (e.g., 09:00). When `inputs.py:build_db_forecast_for_slots()` looks up forecasts for price slots, the first slot (09:00) has no matching forecast → returns `pv=0.0, load=0.0`.

**Why it appears intermittent:**
- If planner runs at exactly 09:00:00, forecasts start at 09:00 → alignment OK
- If planner runs at 09:00:15, forecasts start at 09:15 → 09:00 slot has no forecast → zeros

**Plan:**

#### Phase 1: Fix Root Cause (Primary)
* [ ] Modify `ml/forward.py:94-98` to generate forecasts starting from the **current** 15-minute slot boundary instead of "next slot"
* [ ] Update comment to reflect the change: "Align to current slot boundary"
* [ ] Verify forecast timestamps now match price slot timestamps exactly

#### Phase 2: Add Defensive Fallback
* [ ] Modify `inputs.py:911` to implement fallback logic when exact timestamp match fails
* [ ] If `indexed.get(ts)` returns None, search for the closest forecast at or before the requested slot
* [ ] Only return 0.0 as absolute last resort (if no forecasts available at all)
* [ ] Add warning log when fallback is used: "No exact forecast match for {ts}, using fallback from {fallback_ts}"

#### Phase 3: Testing & Validation
* [ ] Run planner at various times within a 15-minute window and verify consistent forecasts
* [ ] Verify no zero values in load/PV forecasts when DB has valid data
* [ ] Run `uv run ruff check .` for linting
* [ ] Run `uv run python -m pytest tests/ -v -k forecast` for forecast-related tests

#### Phase 4: Documentation
* [ ] Add inline comments explaining timestamp alignment requirements
* [ ] Document the "belt and suspenders" approach (fix root cause + defensive fallback)

**Affected Files:**
- `ml/forward.py:94-98` - Forecast generation timestamp logic
- `inputs.py:909-914` - Forecast lookup with fallback needed

**Success Criteria:**
- Consecutive planner runs (seconds apart) produce identical load/PV forecasts
- No zero values in forecasts when the ML database contains valid predictions
- Graceful degradation with logged warnings if forecasts are ever stale/missing

---
