## Context

The main dashboard at `/` has had no formal spec — it evolved organically. DashboardLab was built as an experiment and is now validated. This change promotes the lab layout to production as properly extracted component files. The lab's inline functions (`CompactRiskPills`, `CompactWaterPills`, `OverrideButtons`, Battery & Strategy card) become first-class components that can be independently maintained and iterated on.

Current dashboard structure (being replaced):
- Row 1: `ChartCard` (full width)
- Row 2: 3-column grid — `AdvisorCard` (hardcoded to powerflow) | `ControlParameters` | `QuickActions` + PlannerAutomation stacked
- Row 3: 3-column domain grid — `GridDomain` | `ResourcesDomain` | `StrategyDomain` (Battery/Price tab toggle)

Known issues resolved by this change:
- `SmartAdvisor` is hidden inside `AdvisorCard` (hardcoded to powerflow) — users never see AI advice
- Price alerts appear in two places (StrategyDomain Price tab + SmartAdvisor)
- Execution controls split across `ControlParameters` and `QuickActions` — fragmented UX
- No dashboard or component specs exist

## Goals / Non-Goals

**Goals:**
- Extract lab inline code into proper component files: `CommandBar.tsx`, `BatteryStrategyCard.tsx`
- Promote validated layout to production dashboard
- Establish permanent specs for all new/modified components
- Consolidate price alerts to SmartAdvisor only
- Remove all DashboardLab traces

**Non-Goals:**
- No backend API changes
- No changes to Dashboard.tsx data fetching, state variables, or WebSocket listeners (layout-only rewrite)
- No changes to ChartCard, PowerFlowCard, GridDomain, ResourcesDomain internals
- No mobile-specific layout redesign

## Decisions

### 1. Proper component files, not inline code

The lab used inline function components (`CompactRiskPills`, etc.) and inlined the Battery & Strategy card JSX inside the page. Production requires each card to be its own `.tsx` file in `frontend/src/components/` so it can be iterated on independently, specced, and tested.

### 2. CommandBar.tsx owns its own interaction state and WebSocket subscriptions

CommandBar manages internally: `plannerProgress`, `quickActionLoading`, `quickActionFeedback`, `vacationDaysIdx`, `boostMinutesIdx`, `topUpSocIdx`, `loadingVacation`, `loadingBoost`. It subscribes to `planner_progress`, `schedule_updated`, and `water_boost_updated` WebSocket events directly.

State it receives as props from Dashboard.tsx (already exists there): `riskAppetite`, `comfortLevel`, `executorStatus`, `automationConfig`, `automationSaving`, `schedulerStatus`, `vacationMode`, `vacationModeHA`, `waterBoostActive`, `soc`, `plannerMeta`.
Callbacks it receives: `onSetRiskAppetite`, `onSetComfortLevel`, `onToggleScheduler`, `onRefresh`.

This matches how `ControlParameters` and `QuickActions` worked — they each owned their interaction state and called back to Dashboard. CommandBar consolidates both patterns.

**What changes in Dashboard.tsx state:** `handleBatteryTopUp` is removed (CommandBar calls the API directly). Everything else is unchanged.

### 3. BatteryStrategyCard.tsx is a pure display component

No API calls, no WebSocket. Receives props: `soc`, `socTarget`, `batteryCapacity`, `plannerMeta`, `batteryCycles`, `priceOutlook`. Replaces `StrategyDomain` entirely.

### 4. Price alerts → SmartAdvisor only

`StrategyDomain`'s Price tab and price alert display are removed. SmartAdvisor already renders price alerts (lines 155–165) and receives `priceAdvice` as a prop — no new code needed there, just removal of the duplicate.

### 5. AdvisorCard.tsx and QuickActions.tsx deleted

Both have exactly one consumer (Dashboard.tsx) and are fully replaced. Delete them to avoid dead code.

### 6. ControlParameters and StrategyDomain removed from CommandDomains.tsx

Both are fully replaced by the new components. GridDomain and ResourcesDomain remain in CommandDomains.tsx.

## Risks / Trade-offs

- **CommandBar.tsx is a large component** — it consolidates two previously separate components. This is acceptable because all interactions are logically unified (one command bar, one place to control the system). Future splitting is straightforward.
- **GridDomain in a smaller bento cell** — was designed for a full-width row. Verify padding/layout at runtime; no spec change needed, just visual QA.
- **StrategyDomain Price tab removal** — any direct link to the price tab breaks. Price alerts are still accessible in SmartAdvisor.

## Migration Plan

1. Create `CommandBar.tsx` with full props, state, handlers, WebSocket, and JSX
2. Create `BatteryStrategyCard.tsx` with props and display JSX
3. Remove placeholder text from `SmartAdvisor.tsx`
4. Remove `ControlParameters` and `StrategyDomain` from `CommandDomains.tsx`
5. Rewrite `Dashboard.tsx` layout (remove old Row 2/Row 3, add CommandBar + bento grid)
6. Remove Lab from `Sidebar.tsx`, `App.tsx`
7. Delete `AdvisorCard.tsx`, `QuickActions.tsx`, `DashboardLab.tsx`
8. Verify all acceptance criteria in the specs
