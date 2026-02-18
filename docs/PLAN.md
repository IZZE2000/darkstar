# Darkstar Energy Manager: Active Plan

**Vision: From Calculator to Agent**
Darkstar is transitioning from a deterministic optimizer (v1) to an intelligent energy agent (v2). It does not just optimize based on static config; it observes context (Weather, Vacation, Prices), predicts outcomes (Aurora ML), and actively strategizes (Strategy Engine) to maximize efficiency and comfort.

---

| Prefix  | Area                 | Examples |
| ------- | -------------------- | -------- |
| **K**   | Kepler (MILP solver) | F41      |
| **E**   | Executor             | E1       |
| **A**   | Aurora (ML)          | A29      |
| **H**   | History/DB           | H1       |
| **O**   | Onboarding           | O1       |
| **UI**  | User Interface       | UI2      |
| **DS**  | Design System        | DS1      |
| **F**   | Fixes/Bugfixes       | F6       |
| **DX**  | Developer Experience | DX1      |
| **ARC** | Architecture         | ARC1     |
| **IP**  | Inverter Profiles    | IP1      |

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

### [DRAFT] REV // UI22 — Fix EV Plan "Actual" Dotted Line Showing in Future Slots

**Goal:** Fix the EV plan chart showing a dotted "Actual EV (kW)" line in future scheduled slots when it should only appear for historical (already executed) slots.

**Context:**
The "Actual EV" dotted line in the schedule chart is incorrectly displaying planned EV values for ALL slots (both historic and future) instead of showing actual executed values only for historical slots. This creates visual confusion since actual execution data should only exist for slots that have already occurred.

**Root Cause Analysis:**
1. **No Separate Actual Data Field:** The `ChartValues` type in `frontend/src/components/ChartCard.tsx` (lines 229-243) has no `actualEvCharging` field - unlike other actuals like `actualCharge`, `actualDischarge`, etc.
2. **Wrong Data Source:** The dotted line dataset (lines 554-566) uses `values.evCharging` (planned data) instead of a separate actual data source:
   ```typescript
   data: values.evCharging ?? values.labels.map(() => null), // WRONG: Uses planned data!
   ```
3. **Missing Backend Support:** The backend API in `backend/api/routers/schedule.py` does not populate actual EV charging data from the execution database (`SlotObservation` or execution history).
4. **Missing Frontend Mapping:** The data population code in `buildLiveData()` only pushes planned EV data: `evCharging.push(slot.ev_charging_kw ?? null)` - it never populates actual EV values from a field like `slot.actual_ev_charging_kw`.

**Plan:**

#### Phase 1: Backend - Add Actual EV Data Support [DRAFT]
* [ ] Add `actual_ev_charging_kw` field to slot response in `backend/api/routers/schedule.py`.
* [ ] Query execution database (LearningStore) for actual EV charging values from `SlotObservation` or execution history.
* [ ] Only populate `actual_ev_charging_kw` for historical slots where `is_executed=true`.
* [ ] Return `null` for future slots to ensure no actual data leaks into future periods.

#### Phase 2: Frontend - Add Actual EV Data Type and Mapping [DRAFT]
* [ ] Add `actualEvCharging?: (number | null)[]` to the `ChartValues` type in `ChartCard.tsx`.
* [ ] Update `buildLiveData()` function to populate `actualEvCharging` from `slot.actual_ev_charging_kw`.
* [ ] Ensure actual data is only pushed for historical slots (check `is_executed` flag).

#### Phase 3: Frontend - Fix Dotted Line Data Source [DRAFT]
* [ ] Update the "Actual EV (kW)" line dataset (lines 554-566) to use `values.actualEvCharging` instead of `values.evCharging`.
* [ ] Verify the dotted line only appears for historical slots with actual data.
* [ ] Ensure the line is hidden (null values) for future slots.

#### Phase 4: Testing and Verification [DRAFT]
* [ ] Run `pnpm lint` in `frontend/` directory to verify no TypeScript errors.
* [ ] Run `uv run ruff check .` to verify Python backend changes.
* [ ] Manual test: Verify dotted line appears only for past slots with executed EV charging.
* [ ] Manual test: Verify no dotted line appears in future scheduled slots.
* [ ] Verify the "Show Actual" toggle correctly shows/hides the EV actual line.

---
