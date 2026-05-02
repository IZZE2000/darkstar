## ADDED Requirements

### Requirement: Dashboard uses a three-row layout
The dashboard at `/` SHALL consist of three vertical sections in order: (1) schedule chart row using `ChartCard`, (2) unified command bar row using `CommandBar`, (3) bento grid row. The layout SHALL be responsive and collapse to a single column on small screens.

#### Scenario: Desktop layout renders all three rows
- **WHEN** a user loads the dashboard on a large screen (lg breakpoint)
- **THEN** the page displays ChartCard at the top, CommandBar below it, and the bento grid below that

#### Scenario: Mobile layout collapses to single column
- **WHEN** a user loads the dashboard on a small screen
- **THEN** all sections stack vertically in a single column in the same top-to-bottom order

---

### Requirement: Bento grid uses three columns with Battery & Strategy spanning two rows
The bento grid SHALL use three columns on large screens. The cell layout SHALL be:
- Column 1, Row 1: `SmartAdvisor`
- Column 1, Row 2: `GridDomain` (from CommandDomains)
- Column 2, Row 1: `PowerFlowCard`
- Column 2, Row 2: `ResourcesDomain` (from CommandDomains)
- Column 3, Rows 1–2: `BatteryStrategyCard` (`lg:row-span-2`)

#### Scenario: BatteryStrategyCard spans two rows on large screens
- **WHEN** a user views the dashboard on a large screen
- **THEN** BatteryStrategyCard occupies the full height of the bento grid in column 3

#### Scenario: Bento cells collapse to single column on mobile
- **WHEN** a user views the dashboard on a small screen
- **THEN** the five bento cards stack vertically: SmartAdvisor, PowerFlowCard, BatteryStrategyCard, GridDomain, ResourcesDomain

---

### Requirement: DashboardLab page is removed
The `/dashboard-lab` route, its sidebar navigation link, and its source file (`DashboardLab.tsx`) SHALL be removed from the application.

#### Scenario: Lab route is inaccessible
- **WHEN** a user navigates to `/dashboard-lab`
- **THEN** the application does not render the lab page (404 or redirect)

#### Scenario: Sidebar has no Lab link
- **WHEN** the user views the sidebar navigation
- **THEN** there is no Lab (flask) icon or `/dashboard-lab` link
