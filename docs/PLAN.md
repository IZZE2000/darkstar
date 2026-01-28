# Darkstar Energy Manager: Active Plan

**Vision: From Calculator to Agent**
Darkstar is transitioning from a deterministic optimizer (v1) to an intelligent energy agent (v2). It does not just optimize based on static config; it observes context (Weather, Vacation, Prices), predicts outcomes (Aurora ML), and actively strategizes (Strategy Engine) to maximize efficiency and comfort.

---

## Revision Naming Conventions

| Prefix | Area | Examples |
|--------|------|----------|
| **K** | Kepler (MILP solver) | F41 |
| **E** | Executor | E1 |
| **A** | Aurora (ML) | A29 |
| **H** | History/DB | H1 |
| **O** | Onboarding | O1 |
| **UI** | User Interface | UI2 |
| **DS** | Design System | DS1 |
| **F** | Fixes/Bugfixes | F6 |
| **DX** | Developer Experience | DX1 |
| **ARC** | Architecture | ARC1 |

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

### [DONE] REV // F42 — Ghost Notifications & Default Config Cleanup

**Goal:** Eliminate "Ghost" entities re-appearing after deletion due to `soft_merge_defaults` filling in keys from `config.default.yaml`.

**Context:**
- `backend/config_migration.py` fills missing user config keys bundle from `config.default.yaml`.
- The default config contains specific entity IDs (e.g., "notify.mobile_app_sebastians_iphone") which re-appear if a user deletes them.
- This results in "Ghost" entities and invalid service calls in the Executor.

**Plan:**

#### Phase 1: Configuration Hygiene [DONE]
* [x] **Refactor `config.default.yaml`**: Set all `input_sensors`, `executor.inverter`, and `notifications` entity IDs to `""` (empty string).
    *   Preserve keys for structure/documentation.
    *   Remove personal data.
*   *Note: Existing user configs will NOT be touched. Users with legacy defaults in their `config.yaml` will remain as-is.*

#### Phase 2: Backend Defense [DONE]
* [x] **Executor Safety (`executor/actions.py`)**:
    *   Modify `send_notification` to return early (no-op) if `service` is an empty string.
    *   Add defensive check for `None` service.
*   [x] **Health Check Update (`backend/health.py`)**:
    *   Update `check_entities` to ignore keys with empty string values (do not flag as "Missing Entity" or "Critical").
*   [x] **Config Loader (`executor/config.py`)**:
    *   Verify `_str_or_none` utility correctly converts `""` to `None` for internal handling.
