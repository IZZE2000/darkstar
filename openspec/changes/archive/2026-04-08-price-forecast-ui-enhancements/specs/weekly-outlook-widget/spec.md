## MODIFIED Requirements

### Requirement: View B displays 7-day price pills
When the user switches to View B, the StrategyDomain card SHALL display 7 pill elements for D+1 through D+7. Each pill SHALL show the short weekday label and a numeric average price below it.

#### Scenario: Pills render from outlook data
- **WHEN** View B is active and outlook data is available
- **THEN** 7 pills are rendered, each showing the short weekday label (e.g., "Mon", "Tue")

#### Scenario: Numeric price shown below each pill
- **WHEN** View B is active and outlook data is available
- **THEN** each pill SHALL display the day's `avg_spot_p50` formatted to 2 decimal places below the day label (e.g., "0.45")

### Requirement: REMOVED — Mini bar chart below pills
The mini bar chart that was initially specified has been removed. The colored pills alone convey relative price levels; users who want detail use the Aurora Forecast Horizon chart. (Design Decision 7)

### Requirement: REMOVED — Model status indicator in card header
The green/pulsing status dot has been removed. The "Price" toggle button itself only appears when price forecasting is enabled, which already communicates availability. (Design Decision 8)
