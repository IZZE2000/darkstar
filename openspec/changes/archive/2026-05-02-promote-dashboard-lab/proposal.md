## Why

The dashboard has been redesigned in a DashboardLab experiment page that is now validated and ready to ship. Promoting it replaces a fragmented 3-column controls layout with a unified command bar and a bento grid that groups cards logically. This is the first time the dashboard has a formal spec — the new components become the permanent foundation for future card iterations.

## What Changes

- **New**: `CommandBar.tsx` — full-width command bar replacing the old 3-column control row (AdvisorCard + ControlParameters + QuickActions). Owns all execution controls, parameter selectors, and override actions.
- **New**: `BatteryStrategyCard.tsx` — standalone Battery & Strategy card replacing the inline StrategyDomain. Shows SoC, metrics, and 7-day price outlook with no tab toggle.
- **Modified**: `SmartAdvisor.tsx` — remove stale placeholder text; becomes the sole display location for price alerts.
- **Modified**: `Dashboard.tsx` — layout rewrite using the new components and bento grid. Data-fetching logic is unchanged.
- **Modified**: `CommandDomains.tsx` — remove `ControlParameters` (replaced by CommandBar) and `StrategyDomain` (replaced by BatteryStrategyCard).
- **BREAKING**: Price alerts removed from `StrategyDomain` — SmartAdvisor is now the single source.
- **Deleted**: `AdvisorCard.tsx`, `QuickActions.tsx` — fully replaced by CommandBar.
- **Deleted**: `DashboardLab.tsx`, `/dashboard-lab` route, sidebar Lab link.

## Capabilities

### New Capabilities

- `command-bar`: The unified full-width command bar component — planner execution, executor pause/resume, auto scheduler toggle, risk appetite selector, water comfort selector, and override actions (Top Up, Boost, Vacation).
- `battery-strategy-card`: The Battery & Strategy card component — SoC with color coding, target SoC, strategy metrics, and 7-day price outlook bars in a single scrollable view.
- `smart-advisor`: The Aurora Advisor card component — today's plan summary, price alerts (sole source), AI/analyst advice, and auto-fetch controls.
- `dashboard-layout`: The main dashboard page layout — 3-row structure (chart / command bar / bento grid) and bento cell placement.

### Modified Capabilities

<!-- None — no existing specs are changing. All capabilities above are new. -->

## Impact

- `frontend/src/components/CommandBar.tsx` — created
- `frontend/src/components/BatteryStrategyCard.tsx` — created
- `frontend/src/components/SmartAdvisor.tsx` — modified
- `frontend/src/components/CommandDomains.tsx` — ControlParameters and StrategyDomain removed
- `frontend/src/components/Sidebar.tsx` — Lab link removed
- `frontend/src/components/AdvisorCard.tsx` — deleted
- `frontend/src/components/QuickActions.tsx` — deleted
- `frontend/src/pages/Dashboard.tsx` — layout rewrite
- `frontend/src/pages/DashboardLab.tsx` — deleted
- `frontend/src/App.tsx` — Lab route and import removed
