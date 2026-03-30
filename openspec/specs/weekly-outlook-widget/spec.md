## Purpose

Integrate the Weekly Outlook and Price Advisor features into the existing StrategyDomain card via a toggle, allowing users to view battery/strategy information alongside 7-day price forecasts and actionable price advice within a familiar UI pattern.

## Requirements

### Requirement: Weekly Outlook and Advisor integrated into StrategyDomain via toggle
The existing `StrategyDomain` component ("Battery & Strategy" card) SHALL support a two-view toggle when `price_forecast.enabled` is true and forecast data is available. View A shows the current battery/strategy content. View B shows the 7-day price outlook pills and price advice items.

#### Scenario: Toggle visible when forecast enabled and data available
- **WHEN** `price_forecast.enabled` is `true` and the outlook API returns at least one day of forecast data
- **THEN** a toggle control (tab or icon button) appears in the StrategyDomain card header, allowing the user to switch between View A and View B

#### Scenario: Toggle hidden when forecast disabled or no data
- **WHEN** `price_forecast.enabled` is `false` OR the outlook API returns an empty `days` array
- **THEN** no toggle appears and the card shows only View A (current battery/strategy content) unchanged

#### Scenario: Default view is battery/strategy
- **WHEN** the Dashboard loads
- **THEN** the StrategyDomain card defaults to View A (battery/strategy)

#### Scenario: Toggle persists within session
- **WHEN** a user switches to View B
- **THEN** the card remains on View B until the user switches back or the page reloads

### Requirement: View B displays 7-day price pills
When the user switches to View B, the StrategyDomain card SHALL display 7 pill elements for D+1 through D+7.

#### Scenario: Pills render from outlook data
- **WHEN** View B is active and outlook data is available
- **THEN** 7 pills are rendered, each showing the short weekday label (e.g., "Mon", "Tue")

#### Scenario: Forecast disabled or no data
- **WHEN** `price_forecast.enabled` is `false` or no data exists
- **THEN** View B is not accessible (no toggle shown) — this scenario cannot occur

### Requirement: Pills are color-coded by price level
Each pill SHALL be colored based on the `level` field from the outlook API.

#### Scenario: Cheap day
- **WHEN** a day's `level` is `"cheap"`
- **THEN** the pill uses a green color

#### Scenario: Normal day
- **WHEN** a day's `level` is `"normal"`
- **THEN** the pill uses an amber/yellow color

#### Scenario: Expensive day
- **WHEN** a day's `level` is `"expensive"`
- **THEN** the pill uses a red color

#### Scenario: Unknown level (insufficient history)
- **WHEN** a day's `level` is `"unknown"`
- **THEN** the pill uses a neutral/gray color

### Requirement: Pills encode forecast confidence via opacity
Each pill's opacity SHALL reflect the `confidence` field from the outlook API.

#### Scenario: High confidence (D+1/D+2)
- **WHEN** a pill's `confidence` is `"high"`
- **THEN** the pill renders at 100% opacity

#### Scenario: Medium confidence (D+3/D+4)
- **WHEN** a pill's `confidence` is `"medium"`
- **THEN** the pill renders at approximately 75% opacity

#### Scenario: Low confidence (D+5-D+7)
- **WHEN** a pill's `confidence` is `"low"`
- **THEN** the pill renders at approximately 50% opacity

### Requirement: Pill tooltip shows price detail
Each pill SHALL show additional detail on hover or tap.

#### Scenario: Hover/tap reveals detail
- **WHEN** a user hovers over or taps a day pill
- **THEN** a tooltip shows the day's average price (p50), cheapest hour price (min_hour_p50), most expensive hour price (max_hour_p50), and the confidence label

### Requirement: View B displays price advice items
Below the 7-day pills, View B SHALL display the price advice items returned in the analyst endpoint response (items with `category: "price"`).

#### Scenario: Price advice items shown in View B
- **WHEN** View B is active and the analyst endpoint returns advice items with `category: "price"`
- **THEN** each advice item's `message` is displayed as a text line in the card

#### Scenario: No price advice items available
- **WHEN** View B is active but no `category: "price"` advice items exist
- **THEN** a neutral message is shown (e.g., "No price alerts this week")

### Requirement: Dashboard fetches outlook data and passes to StrategyDomain
`Dashboard.tsx` SHALL fetch `GET /api/price-forecast/outlook` as part of its deferred data fetches, and pass the result as props to `StrategyDomain`. Dashboard SHALL also fetch price advice items (from the analyst endpoint) and pass them as props.

#### Scenario: Data fetched on mount and schedule update
- **WHEN** the Dashboard mounts OR a `schedule_updated` WebSocket event fires
- **THEN** the outlook data and advice items are re-fetched and passed to StrategyDomain

### Requirement: No new dashboard layout elements
The integration SHALL NOT add any new cards, rows, or top-level layout elements to the Dashboard. All new UI is contained within the existing StrategyDomain card.

#### Scenario: Layout unchanged when forecast disabled
- **WHEN** `price_forecast.enabled` is `false`
- **THEN** the dashboard layout is visually identical to the current layout
