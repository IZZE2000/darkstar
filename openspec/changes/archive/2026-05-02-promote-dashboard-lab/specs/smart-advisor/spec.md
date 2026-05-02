## ADDED Requirements

### Requirement: SmartAdvisor displays today's plan summary
The `SmartAdvisor` component (`frontend/src/components/SmartAdvisor.tsx`) SHALL display a `todaySummary` string when provided via props. The summary describes the planned charge/discharge/export phases for the day.

#### Scenario: Today's summary is shown when available
- **WHEN** the `todaySummary` prop is a non-empty string
- **THEN** the summary text is displayed in the card

#### Scenario: Today's summary section is hidden when not available
- **WHEN** `todaySummary` is null or undefined
- **THEN** the summary section is not rendered

---

### Requirement: SmartAdvisor is the sole display location for price alerts
The SmartAdvisor card SHALL display price alerts from the `priceAdvice` prop. Price alerts SHALL NOT appear anywhere else on the dashboard. When no price alerts exist, the card SHALL show "No price alerts this week".

#### Scenario: Price alerts rendered when present
- **WHEN** `priceAdvice` contains one or more items
- **THEN** each item is displayed as a labeled price alert in the SmartAdvisor card

#### Scenario: Empty state shown when no alerts
- **WHEN** `priceAdvice` is empty or undefined
- **THEN** the card shows "No price alerts this week"

---

### Requirement: SmartAdvisor displays AI analysis or analyst recommendations
The component SHALL fetch and display AI-generated advice (`Api.getAdvice()`) when LLM is enabled, or analyst report recommendations (`Api.analystRun()`) when LLM is disabled. The enabled state is fetched from `Api.config()` on mount.

#### Scenario: AI advice shown when LLM is enabled
- **WHEN** the advisor config has `enable_llm: true` and advice is available
- **THEN** AI-generated advice items are displayed

#### Scenario: Analyst recommendations shown when LLM is disabled
- **WHEN** the advisor config has `enable_llm: false`
- **THEN** analyst report recommendations are displayed as fallback

---

### Requirement: SmartAdvisor supports manual refresh and auto-fetch toggle
The card SHALL display a manual refresh button (↻ icon) that re-fetches advice on click. The card SHALL display an auto-fetch toggle (⏱ icon) that controls whether advice is automatically refreshed when the schedule changes. Both states SHALL be persisted via `Api.configSave`.

#### Scenario: Manual refresh triggers advice re-fetch
- **WHEN** the user clicks the refresh button
- **THEN** advice is re-fetched and the displayed content updates

#### Scenario: Auto-fetch toggle persists state
- **WHEN** the user toggles auto-fetch
- **THEN** the new state is saved via Api.configSave and the icon reflects the new setting

---

### Requirement: SmartAdvisor shows no placeholder text when advice is not yet loaded
The SmartAdvisor card SHALL NOT display any static instruction text such as "Click the refresh icon to analyze your current schedule." The loading state SHALL be communicated via a spinner or skeleton, not instructional copy.

#### Scenario: No instruction text visible at any time
- **WHEN** the user views the SmartAdvisor card in any state (loading, empty, loaded)
- **THEN** the text "Click the refresh icon to analyze your current schedule." is never shown
