# Darkstar Energy Manager: Backlog

This document contains ideas, improvements, and tasks that are not yet scheduled for implementation.

---

## 🤖 AI Instructions (Read First)

1.  **Naming:** Use generic names (e.g., `Settings Cleanup`, `Chart Improvements`) until the item is promoted.

2.  **Categories:**
    - **Backlog** — Concrete tasks ready for implementation
    - **On Hold** — Paused work with existing code/design
    - **Future Ideas** — Brainstorming, needs design before implementation

3.  **Format:** Use the template below for new items.

### Backlog Item Template

```
### [Category] Item Title

**Goal:** What we want to achieve.

**Notes:** Context, constraints, or design considerations.
```

---

## 📋 Backlog

### 📥 Inbox (User Added / Unsorted)

<!-- Add new bugs/requests here. AI should wipe the item after processing into a OpenSpec change. -->

#### [Planner] Multiple Heating Sources/Deferrable Loads

**Goal:** Support control for multiple distinct heating sources (e.g., HVAC + Water Heater + Floor Heating) independently. A simple switch per each source to enable/disable it, and then the planner will decide when to turn them on/off based on the optimization problem. We need parameter for the kW consumption of each source and time/kWh goal.

**Notes:** Currently limited to a single water heater channel.

---

#### [Learning] Per-Device Load Forecasting

**Goal:** Train per-device load models (EV, water heater) instead of aggregated forecasts. Enables the planner to predict per-device consumption patterns (e.g., Tesla charges faster than Leaf, upstairs heater runs more at night).

**Notes:** Currently `ev_charging_kwh` and `water_kwh` in `slot_observations` are aggregated across all devices. Per-device energy recording (added in multi-device-ev-chargers change) provides the data foundation. Requires extending Aurora/Reflex models to accept device ID as a feature, and per-device forecast output in the pipeline. Not blocking for multi-device scheduling — the planner uses real-time sensor state, not forecasts, for per-device decisions.

---

### 💡 Future Ideas (Brainstorming)

#### [UI] Advisor Overhaul

**Goal:** Redesign and improve the Advisor feature to provide more actionable and reliable energy insights.

**Notes:** Current version is disabled/hidden as it needs a complete overhaul. Should integrate better with Kepler schedules and Aurora forecasts.

---
