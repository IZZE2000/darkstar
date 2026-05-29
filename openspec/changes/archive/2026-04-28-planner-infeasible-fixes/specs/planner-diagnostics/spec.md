## MODIFIED Requirements

### Requirement: Persistent error banner with details drawer
The frontend SHALL render planner failures as persistent banners using the existing `SystemAlert` component. The banner SHALL NOT be fully dismissible: users MAY collapse it to a single-line indicator, but a visible marker SHALL remain until the underlying failure clears.

The `SystemAlert` component SHALL render whenever `health.issues` contains one or more entries — regardless of the value of `health.healthy`. The previous guard `if (health.healthy) return null` SHALL be replaced with a check that returns null only when there are no issues to display.

When a `HealthIssue` carries a `details` payload, the banner SHALL render a "View details" control that opens a drawer component (`PlannerErrorDetails`) displaying:

- The error code as a monospace chip
- The human message and fix hint
- A diagnostics table of all key/value pairs from `details`
- A live retry countdown derived from `retry_in_s`, ticking down in real time and refreshing when a new health snapshot arrives
- A "Copy diagnostic bundle" button that copies a JSON blob of the full issue to the clipboard
- An "Open Settings" link when the error code is config-blocking

Secrets-bearing values in the diagnostic bundle (HA tokens, API keys) SHALL be redacted as `***` before being displayed or copied.

The transient 3-second toast previously shown in `QuickActions.tsx` for `planner_error` WebSocket events SHALL be removed. The frontend SHALL read planner state exclusively from the health endpoint/stream.

#### Scenario: Planner failure shows persistent banner
- **WHEN** the health endpoint returns an issue with `category="planner"` and severity `critical`
- **THEN** a persistent critical banner is rendered at the top of the application
- **AND** the banner remains visible across navigation

#### Scenario: Warning-level planner issue shows banner even when system is healthy
- **WHEN** the health endpoint returns `healthy=true` but `issues` contains a planner `severity="warning"` entry (e.g. `SOLVER_INFEASIBLE`)
- **THEN** the warning banner IS rendered (not suppressed)
- **AND** the banner displays the warning message and fix hint

#### Scenario: Banner cannot be hidden entirely
- **WHEN** the user clicks the collapse control on a planner error banner
- **THEN** the banner shrinks to a single-line indicator
- **AND** the indicator remains visible until the underlying failure clears

#### Scenario: Details drawer opens and shows diagnostics
- **WHEN** the user clicks "View details" on a planner error banner
- **THEN** a drawer opens showing the error code, message, fix hint, diagnostics table, and live retry countdown
- **AND** the "Copy diagnostic bundle" button copies a valid JSON string to the clipboard

#### Scenario: Retry countdown ticks live
- **WHEN** the drawer is open with `retry_in_s=90`
- **THEN** the displayed countdown decrements approximately once per second
- **AND** when a new health snapshot arrives with a different `retry_in_s`, the countdown resets to the new value

#### Scenario: Secrets are redacted in diagnostic bundle
- **WHEN** the diagnostic bundle is generated for copy-to-clipboard
- **THEN** any key matching known secret patterns (`*token*`, `*api_key*`, `*password*`) has its value replaced with `***`

#### Scenario: Toast for planner_error is removed
- **WHEN** a `planner_error` WebSocket event is received
- **THEN** no transient toast appears
- **AND** the persistent banner reflects the current planner state on the next health refresh

## ADDED Requirements

### Requirement: Planner service emits terminal phase on failure
`PlannerService` SHALL emit a `"failed"` progress phase via WebSocket immediately before clearing `_current_phase` in every error path (both typed `PlannerError` and untyped `Exception`). The `"failed"` phase SHALL be emitted before any state cleanup so the frontend receives a definitive terminal signal.

#### Scenario: Typed planner error emits failed phase
- **WHEN** the planner raises a `PlannerError` (e.g. `SOLVER_INFEASIBLE`)
- **THEN** the service emits a `planner_progress` WebSocket event with `phase="failed"`
- **AND** `_current_phase` is subsequently set to `None`

#### Scenario: Unexpected exception emits failed phase
- **WHEN** the planner raises an unhandled `Exception`
- **THEN** the service emits a `planner_progress` WebSocket event with `phase="failed"`
- **AND** `_current_phase` is subsequently set to `None`

#### Scenario: Successful run does not emit failed phase
- **WHEN** the planner completes successfully
- **THEN** the service emits `phase="complete"` and never emits `phase="failed"`

### Requirement: Frontend treats "failed" as a terminal planner phase
The `QuickActions` component SHALL handle `phase="failed"` as a terminal state equivalent to `phase="complete"`. When a `planner_progress` event with `phase="failed"` is received, the button text SHALL update to indicate failure and the planning state SHALL be cleared after a short delay so `isPlanning` returns to `false`. The `'failed'` phase SHALL NOT fall through to the generic `'Planning...'` default label.

#### Scenario: Failed phase shows failure label
- **WHEN** a `planner_progress` event with `phase="failed"` is received
- **THEN** the planner button shows a failure label (e.g. `"Failed ✗"`)
- **AND** the progress bar does not remain at a mid-run position

#### Scenario: Planning state clears after failed phase
- **WHEN** a `planner_progress` event with `phase="failed"` is received
- **THEN** `isPlanning` becomes `false` after a short delay
- **AND** the "Run Planner" button returns to its idle state
