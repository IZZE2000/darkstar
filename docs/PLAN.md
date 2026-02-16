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

---

### [PLANNED] REV // K22 — Effekttariff (Active Guard)

**Goal:** Implement a dual-layer strategy (Planner + Executor) to minimize peak power usage ("Effekttariff").

**Plan:**

#### Phase 1: Configuration & Entities [PLANNED]
* [ ] Add `grid.import_breach_penalty_sek` (Default: 5000.0) to `config.default.yaml`.
* [ ] Add `grid.import_breach_penalty_enabled` (Default: false) to `config.default.yaml`.
* [ ] Add `grid.import_breach_limit_kw` (Default: 11.0) for the hard executor limit.
* [ ] Add override entities to `executor.config`.
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

#### Phase 2: Planner Logic (Economic) [PLANNED]
* [ ] **Planner Logic:** Pass the penalty cost to Kepler if enabled.
* [ ] **Re-planning:** Trigger re-plan if penalty configuration changes.
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

#### Phase 3: Executor Active Guard (Reactive) [PLANNED]
* [ ] **Monitor:** In `executor/engine.py` `_tick`, check `grid_import_power` vs `import_breach_limit_kw`.
* [ ] **Reactive Logic:**
    *   If Breach > Limit:
        *   Trigger `ForceDischarge` on Battery (Max power).
        *   Trigger `Disable` on Water Heating.
        *   Log "Grid Breach Detected! Engaging Emergency Shedding".
* [ ] **Recovery:** Hysteresis logic to release overrides when grid import drops.
* [ ] **Frontend:** Add controls to `Settings > Grid`.
* [ ] **USER VERIFICATION AND COMMIT:** Stop and let the user verify, after the user approves commit the changes

---

### [DRAFT] REV // K26 — Inverter Clipping Support

**Goal:** Correctly model DC vs AC inverter limits in the Kepler solver to prevent over-optimistic planning on high-PV systems.
**Context:** User has a 15kWp array but a 10kW (AC) / 12kW (DC-Input) inverter. Current model assumes all PV is available at the AC bus.

**Plan:**

#### Phase 1: Configuration & Schema [DRAFT]
* [ ] Add `inverter.max_pv_input_kw` (DC limit) and `inverter.max_ac_output_kw` (AC limit) to `config.default.yaml`.
* [ ] Deprecate/Migration: Map old `system.inverter.max_power_kw` to `max_ac_output_kw`.
* [ ] **USER VERIFICATION:** Confirm schema covers all hardware limits (Access Power vs Input Power).

#### Phase 2: Solver Logic (DC Bus) [DRAFT]
* [ ] **Kepler Model:** Introduce `pv_to_ac[t]` and `discharge_to_ac[t]` variables.
* [ ] **Constraint:** `pv_actual[t] + discharge_dc[t] == charge_dc[t] + ac_produced[t]`.
* [ ] **Constraint:** `ac_produced[t] <= inverter_ac_limit`.
* [ ] **Constraint:** `pv_actual[t] <= inverter_pv_dc_limit`.
* [ ] Verify with test case (15kW PV, 10kW AC, 12kW DC battery charge).

#### Phase 3: Input Pipeline [DRAFT]
* [ ] **Inputs:** Update `inputs.py` to optionally clip forecasts early (for heuristic simplicity) or pass through raw data.
* [ ] **UI:** Show "Clipped Solar" in the dashboard forecast chart.


---

### [DONE] REV // F64 — EV Node Tooltip for Multiple EVs

**Goal:** Show per-EV details (name, power, SoC, plug status) in a tooltip on the PowerFlowCard EV node. Must work for both single and multiple EVs, and support both desktop hover and mobile tap.

**Context:** The backend `ha_socket.py:_get_monitored_entities` only monitors the **first** enabled EV charger (explicit `break` at line 119). State changes emit scalar keys (`ev_kw`, `ev_soc`, `ev_plugged_in`). The frontend `PowerFlowData` type, `Dashboard.tsx` state, and `CircuitNode.tsx` are all scalar — none support per-EV data. The `PowerFlowCard` renders inside an `<svg>`, so standard React tooltip libraries won't work out of the box.

**Backend Status:** Solver (`planner/solver/adapter.py`) already aggregates across all EVs. This REV addresses the **live metrics display** path only.

**Plan:**

#### Phase 1: Backend — Per-EV Live Metrics [DONE]
**Files:** `backend/ha_socket.py`

* [x] **Remove `break`** in `_get_monitored_entities` — monitor ALL enabled EV chargers, not just the first
* [x] **Per-EV entity keys** — Change flat `"ev_kw"` mapping to indexed keys: `"ev_kw_0"`, `"ev_soc_0"`, `"ev_plug_0"`, `"ev_kw_1"`, etc. Store the EV name alongside each index for display
* [x] **Rework `_handle_state_change`** — The `ev_plug`, `ev_soc`, and numeric sensor branches must:
  - Identify *which* EV index the entity belongs to
  - Update per-EV state in `self.latest_values` (e.g. `ev_chargers[0].kw`)
  - Emit the full `ev_chargers` array (not just the changed scalar) via `emit_live_metrics`
* [x] **Payload shape** — Emit `ev_chargers: [{name: str, kw: float, soc: float|null, plugged_in: bool}]` plus aggregate `ev_kw` (sum) for backward compat in the main node display
* [x] **Re-plan trigger** — Keep existing `_trigger_ev_replan` logic, but fire for ANY EV plug-in event
* [x] **Test:** Print/log WebSocket payload with 2+ mock EVs, verify array shape
* **Note:** EVs sharing sensors are handled gracefully - sensors already mapped are skipped to avoid overwrite

#### Phase 2: Frontend — Types & Dashboard State [DONE]
**Files:** `frontend/src/components/PowerFlowRegistry.ts`, `frontend/src/pages/Dashboard.tsx`

* [x] **`PowerFlowData` type** — Add `evChargers?: Array<{name: string, kw: number, soc: number | null, pluggedIn: boolean}>` to the interface (keep existing `ev`, `evPluggedIn`, `evSoc` for aggregate node display)
* [x] **`Dashboard.tsx` state** — Add `ev_chargers` to the `livePower` state shape
* [x] **`setLivePower` handler** (lines 109–118) — Merge incoming `ev_chargers` array into state; continue mapping aggregate `ev_kw` → `ev.kw` for the main node value
* [x] **Pass through** — Include `evChargers` in the `powerFlowData` prop object passed to `PowerFlowCard`

#### Phase 3: Frontend — EV Tooltip Component [DONE]
**Files:** `frontend/src/components/CircuitNode.tsx`, `frontend/src/components/PowerFlowCard.tsx`

* [x] **`CircuitNode` extension** — Add optional `onInteract?: () => void` prop (tooltipContent handled in PowerFlowCard)
* [x] **Interaction handling** — On the EV `<g>` group:
  - Tap/Click to toggle tooltip on both mobile and desktop
  - Dismiss on outside tap (via document event listener)
* [x] **Tooltip rendering strategy** — Use `<foreignObject>` inside the SVG to render a styled HTML tooltip div. Positioned centered above the EV node
* [x] **Tooltip content:**
  - Header: "X EVs Connected" (or "EV" for single)
  - Per-EV row: `name` • `kw` kW • `soc`% • plug icon (green/grey)
  - Styling: dark opaque bg, rounded corners, 11px JetBrains Mono, max-height 140px with overflow scroll
* [x] **Single EV case** — If only 1 EV, show its name + details (no redundant "1 EV" header)
* [x] **Hide tooltip** when PowerFlowCard is in `compact` mode (e.g. mobile widget) — not enough space

#### Phase 4: Test & Lint [DONE]
* [ ] Test: Single EV — node shows aggregate, tooltip shows single EV details *(blocked by Phase 5-6)*
* [ ] Test: Multiple EVs — node shows aggregate sum, tooltip lists all EVs *(blocked by Phase 5-6)*
* [x] Test: No EVs enabled — EV node hidden via `shouldRender` (existing behavior)
* [x] Test: Mobile — tap EV node to show tooltip, tap outside to dismiss
* [x] Run `pnpm lint` in `frontend/` — zero errors
* [x] Run `uv run ruff check backend/ha_socket.py` — zero errors
* [x] `pnpm run build` succeeds

#### Phase 5: 🔴 Critical Fix — Snake/CamelCase Mismatch [DONE]
**Root cause:** Backend emits `plugged_in` (snake_case) but `PowerFlowData` type expects `pluggedIn` (camelCase). Tooltip reads `ev.pluggedIn` which is always `undefined`.

**Files:** `frontend/src/pages/Dashboard.tsx`

* [x] **Map `ev_chargers` keys** in `setLivePower` handler — When receiving `data.ev_chargers` from WebSocket, transform each entry from `{name, kw, soc, plugged_in}` → `{name, kw, soc, pluggedIn}` before storing in state
* [x] Alternatively: change the backend to emit `pluggedIn` instead — but frontend mapping is safer since it keeps backend naming consistent with Python conventions

#### Phase 6: 🔴 Critical Fix — `ev_chargers` Empty After Page Load [DONE]
**Root cause:** On startup, `get_states` triggers `_handle_state_change` for each EV entity. If the EV power value is `0`, `unknown`, or `unavailable`, the generic numeric handler returns early (line 398) BEFORE reaching the `ev_kw_` array builder (line 440). The `ev_chargers` array is never emitted.

**Files:** `backend/ha_socket.py`

* [x] **Move `ev_kw_*` handling BEFORE the early return** — The `ev_kw_*` prefix check (line 440) must run before the generic `unknown`/`unavailable` filter. Moved it into its own dedicated branch alongside `ev_plug_*` and `ev_soc_*`, just like those handlers already are (they have their own early-return blocks at lines 282 and 341)
* [x] **Emit initial `ev_chargers` array** — After processing all `get_states` results (line 226-230 loop), emit the full `ev_chargers` array from `self.latest_values` so the frontend gets the complete state on connect
* [x] **Each EV handler emits consistent payload** — All three branches (`ev_plug_*`, `ev_soc_*`, `ev_kw_*`) now emit `ev_chargers` array + `ev_kw` aggregate + `ev_plugged_in` aggregate in every emission, not just their own subset

#### Phase 7: 🟡 Medium Fixes — Tooltip UX & Cleanup [DONE]
**Files:** `frontend/src/components/PowerFlowCard.tsx`, `frontend/src/components/CircuitNode.tsx`, `backend/ha_socket.py`

* [x] **Fix tooltip event timing bug** — The `useEffect` (line 39) adds a document `click` listener synchronously when `showEvTooltip` becomes `true`. The same click that opened the tooltip bubbles up to this listener and immediately closes it. **Fix:** Wrap the `addEventListener` in `setTimeout(() => ..., 0)` to defer to the next event loop tick
* [x] **Remove unused `onMouseEnter`/`onMouseLeave` props** from `CircuitNode.tsx` (lines 14-15, 29-30, 110-111) — dead code, not used anywhere
* [x] **Center tooltip in card** — Changed `foreignObject` positioning from fixed offset at EV node to centered in card viewBox (`x={compact ? 70 : 100}`)
* [x] **Dynamic tooltip dimensions** — Tooltip now uses `width: 'max-content'` and `minWidth: '180px'` with flexible height up to `maxHeight: '180px'`
* [x] **Fix `used_sensors` deduplication scope** — In `_get_monitored_entities`, changed from single `used_sensors` set to separate sets per sensor type: `used_power_sensors`, `used_soc_sensors`, `used_plug_sensors`. This prevents cross-type collisions while allowing same sensor for different types.
* [x] **Remove `ev_soc` aggregate** — Frontend now calculates SoC to display dynamically: shows plugged-in EV's SoC, or first EV if multiple are plugged in. Removed dependency on backend aggregate emission.
* [x] **Fix `foreignObject` clipping** — Updated dimensions to `width={compact ? 160 : 200} height={compact ? 120 : 160}` with centered flex container inside

#### Phase 8: Re-Test [IN PROGRESS]
* [ ] Test: Single EV — tooltip shows name, kW, SoC%, plug icon after page load
* [ ] Test: Multiple EVs — tooltip lists all EVs with correct per-EV data
* [ ] Test: Tap to open, tap outside to dismiss (no flicker/immediate close)
* [ ] Test: Verify `ev_chargers` array present in first `live_metrics` payload after WebSocket connect
* [ ] Test: Tooltip is centered in card (not at EV node position)
* [ ] Test: Tooltip dimensions adjust to content (dynamic sizing)
* [ ] Test: EV node subValue shows plugged-in EV's SoC or first EV's SoC
* [x] Run `pnpm lint` — zero errors
* [x] Run `uv run ruff check backend/ha_socket.py` — zero errors
* [x] `pnpm run build` succeeds

---
