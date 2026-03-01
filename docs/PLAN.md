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
