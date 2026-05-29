## 1. Create CommandBar.tsx

Reference source: `frontend/src/pages/DashboardLab.tsx`

- [x] 1.1 Create `frontend/src/components/CommandBar.tsx`. Define the props interface: `riskAppetite: number`, `comfortLevel: number`, `executorStatus`, `automationConfig`, `automationSaving: boolean`, `schedulerStatus`, `vacationMode: boolean`, `vacationModeHA: boolean`, `waterBoostActive`, `soc: number | null`, `plannerMeta`, `onSetRiskAppetite: (level: number) => void`, `onSetComfortLevel: (level: number) => void`, `onToggleScheduler: () => void`, `onRefresh: () => void`. Add constant arrays at top of file: `TOP_UP_SOC_OPTIONS = [30, 50, 80, 100]`, `BOOST_MINUTES_OPTIONS = [30, 60, 120]`, `VACATION_DAYS_OPTIONS = [1, 3, 7, 14, 30]`.

- [x] 1.2 Add internal state to CommandBar.tsx: `plannerProgress` (PlannerProgress | null), `quickActionLoading` (string | null), `quickActionFeedback` ({ type, message } | null), `vacationDaysIdx` (number, default 1), `boostMinutesIdx` (number, default 1), `topUpSocIdx` (number, default 1), `loadingVacation` (boolean), `loadingBoost` (boolean).

- [x] 1.3 Implement planner and pause handlers in CommandBar.tsx. Copy `handleRunPlanner` from DashboardLab.tsx:588–598 and `handleTogglePause` from DashboardLab.tsx:600–619. In `handleTogglePause`, replace `fetchAllData()` calls with `onRefresh()` and replace `executorStatus?.paused` checks with the `executorStatus` prop.

- [x] 1.4 Implement override handlers in CommandBar.tsx. Copy `handleToggleTopUp` from DashboardLab.tsx:547–564, `handleToggleBoost` from DashboardLab.tsx:521–545, `handleToggleVacation` from DashboardLab.tsx:495–519. Replace all `fetchAllData()` calls with `onRefresh()`. Replace local state references (`riskAppetite`, `comfortLevel`, `executorStatus`, `waterBoostActive`, `vacationMode`, `vacationModeHA`) with their prop equivalents.

- [x] 1.5 Add WebSocket listeners in CommandBar.tsx using `useSocket`: subscribe to `planner_progress` (updates `plannerProgress` state; auto-clear on 'failed' after 3000ms), `schedule_updated` (set phase to 'complete', auto-clear after 2000ms, call `onRefresh()`), `water_boost_updated` (update `waterBoostActive` state — note: this event was previously in `ControlParameters`; the handler receives `{ active, expires_at, remaining_seconds }`). Reference patterns from `frontend/src/components/QuickActions.tsx`.

- [x] 1.6 Implement derived values in CommandBar.tsx: `isPaused = executorStatus?.paused != null`, `isPlanning = plannerProgress !== null`, `isTopUpActive = executorStatus?.quick_action?.type === 'force_charge'`, `isBoostActive = waterBoostActive?.boost ?? false`, `isVacationActive = vacationMode || vacationModeHA`. Compute `planBadge` (status text) and `nextRunDate` from `schedulerStatus` and `plannerMeta` — reference DashboardLab.tsx:733–759.

- [x] 1.7 Implement JSX for CommandBar.tsx. Copy the command bar card from DashboardLab.tsx:1014–1094 (the `<Card className="px-4 py-2 ...">` block). Copy `CompactRiskPills` sub-render from DashboardLab.tsx:765–796, `CompactWaterPills` from DashboardLab.tsx:798–829, `OverrideButtons` from DashboardLab.tsx:831–959. These become private render functions or JSX fragments inside CommandBar (not inline page-level functions). Replace all references to page-level state/handlers with CommandBar's own state, props, and handlers.

## 2. Create BatteryStrategyCard.tsx

Reference source: `frontend/src/pages/DashboardLab.tsx`

- [x] 2.1 Create `frontend/src/components/BatteryStrategyCard.tsx`. Define props interface: `soc: number | null`, `socTarget: number`, `batteryCapacity: number`, `plannerMeta: PlannerMeta | null`, `batteryCycles: number | null`, `priceOutlook: PriceOutlookResponse | undefined`. Import `PlannerMeta` and `PriceOutlookResponse` types from their existing locations in the codebase.

- [x] 2.2 Implement JSX for BatteryStrategyCard.tsx. Copy the Battery & Strategy card block from DashboardLab.tsx:1136–1258 (the `<Card className="p-4 flex flex-col h-full ...">` block). Replace all page-level state references (`soc`, `currentSlotTarget`, `batteryCapacity`, `plannerMeta`, `todayStats?.batteryCycles`, `priceOutlook`) with the corresponding props. Remove the `lg:row-span-2` and `motion.div` wrapper — those belong in the Dashboard layout, not inside the component. The component root should be the `<Card>` directly.

## 3. Fix SmartAdvisor.tsx

- [x] 3.1 In `frontend/src/components/SmartAdvisor.tsx`, find and remove the text "Click the refresh icon to analyze your current schedule." — remove the surrounding JSX element as well. Verify the component still renders correctly in empty/loading states with no stale instructional copy.

## 4. Clean up CommandDomains.tsx

- [x] 4.1 In `frontend/src/components/CommandDomains.tsx`, remove the entire `ControlParameters` component (its props interface, internal state, WebSocket listener, handlers, and JSX). Remove its export. Also remove the `water_boost_updated` WebSocket event type if it was only used by ControlParameters.

- [x] 4.2 In `frontend/src/components/CommandDomains.tsx`, remove the entire `StrategyDomain` component (its props interface, tab toggle state, Battery tab, Price tab including all price alert display, and 7-day outlook display). Remove its export. `GridDomain` and `ResourcesDomain` must remain untouched.

## 5. Rewrite Dashboard.tsx layout

- [x] 5.1 In `frontend/src/pages/Dashboard.tsx`, remove the `handleBatteryTopUp` handler (its logic moves into CommandBar). Remove imports for `AdvisorCard`, `QuickActions`, and `ControlParameters`. Remove the `StrategyDomain` import from CommandDomains.

- [x] 5.2 In `frontend/src/pages/Dashboard.tsx`, import `CommandBar` from `../components/CommandBar` and replace the entire Row 2 JSX (the `grid grid-cols-1 lg:grid-cols-3` block containing AdvisorCard + ControlParameters + QuickActions/PlannerAutomation) with a single `<CommandBar>` passing all required props: `riskAppetite={riskAppetite}`, `comfortLevel={comfortLevel}`, `executorStatus={executorStatus}`, `automationConfig={automationConfig}`, `automationSaving={automationSaving}`, `schedulerStatus={schedulerStatus}`, `vacationMode={vacationMode}`, `vacationModeHA={vacationModeHA}`, `waterBoostActive={waterBoostActive}`, `soc={soc}`, `plannerMeta={plannerMeta}`, `onSetRiskAppetite={handleSetRiskAppetite}`, `onSetComfortLevel={handleSetComfortLevel}`, `onToggleScheduler={toggleAutomationScheduler}`, `onRefresh={fetchAllData}`.

- [x] 5.3 In `frontend/src/pages/Dashboard.tsx`, import `BatteryStrategyCard` from `../components/BatteryStrategyCard` and rewrite the entire Row 3 JSX as a bento grid (`grid grid-cols-1 lg:grid-cols-3 gap-6`). Layout: Col 1 = `<SmartAdvisor todaySummary={todaySummary} priceAdvice={priceAdvice} />` (row 1) + `<GridDomain netCost={...} importKwh={...} exportKwh={...} />` (row 2). Col 2 = `<PowerFlowCard systemConfig={config} data={...} />` (row 1) + `<ResourcesDomain ...existing props... />` (row 2). Col 3 = `<motion.div className="lg:row-span-2"><BatteryStrategyCard soc={soc} socTarget={currentSlotTarget} batteryCapacity={batteryCapacity} plannerMeta={plannerMeta} batteryCycles={todayStats?.batteryCycles ?? null} priceOutlook={priceOutlook} /></motion.div>`. Pass the same props to SmartAdvisor, GridDomain, PowerFlowCard, ResourcesDomain as currently used for their equivalents.

## 6. Remove DashboardLab traces

- [x] 6.1 In `frontend/src/components/Sidebar.tsx`, remove the Lab nav item (Flask icon, label "Lab", route `/dashboard-lab`).

- [x] 6.2 In `frontend/src/App.tsx`, remove the `import DashboardLab` statement and the `/dashboard-lab` route.

## 7. Delete dead files

- [x] 7.1 Delete `frontend/src/components/AdvisorCard.tsx`.
- [x] 7.2 Delete `frontend/src/components/QuickActions.tsx`.
- [x] 7.3 Delete `frontend/src/pages/DashboardLab.tsx`.

## 8. Verification

- [x] 8.1 Load `/` — three-row layout renders: ChartCard, CommandBar, bento grid with 5 cards.
- [x] 8.2 CommandBar left group: Run Planner button shows spinner while planning; Pause/Resume toggles color and icon correctly; Auto toggle reflects scheduler state.
- [x] 8.3 CommandBar center group: Risk pills highlight on selection and save; Water pills highlight on selection and save; Top Up activates with correct SoC target and shows STOP when active; Boost activates and shows countdown; Vacation activates and shows ON state.
- [x] 8.4 CommandBar right group: Status badge visible with plan freshness text.
- [x] 8.5 SmartAdvisor card: price alerts visible when present; "No price alerts this week" when empty; no "Click the refresh icon..." text anywhere.
- [x] 8.6 BatteryStrategyCard: SoC shown with correct color coding; metrics grid shows S-Index, Cycles, Safety Floor, Tradable; 7-day outlook bars render with correct colors and widths; no tab toggle visible.
- [x] 8.7 GridDomain and ResourcesDomain render in their bento cells with existing data.
- [x] 8.8 Navigate to `/dashboard-lab` — route not found.
- [x] 8.9 Sidebar: no Lab (flask) link visible.
- [x] 8.10 No TypeScript errors; no unused import warnings for deleted components.
