## ADDED Requirements

### Requirement: BatteryStrategyCard displays current SoC and target with color coding
The `BatteryStrategyCard` component (`frontend/src/components/BatteryStrategyCard.tsx`) SHALL display the current battery SoC (from `soc` prop) and the current slot target SoC (from `socTarget` prop) prominently. SoC SHALL be color-coded: green (`text-good`) when > 50%, amber (`text-warn`) when > 20%, red (`text-bad`) when ≤ 20%. An arrow SHALL separate current from target. When `batteryCapacity` > 0, the actual kWh value SHALL be shown below (e.g., "7.2 of 10.0 kWh").

#### Scenario: SoC shown in green when above 50%
- **WHEN** `soc` is 75
- **THEN** the SoC value is displayed in the `text-good` color

#### Scenario: SoC shown in amber when between 20% and 50%
- **WHEN** `soc` is 35
- **THEN** the SoC value is displayed in the `text-warn` color

#### Scenario: SoC shown in red when at or below 20%
- **WHEN** `soc` is 15
- **THEN** the SoC value is displayed in the `text-bad` color

#### Scenario: kWh display shown when battery capacity is known
- **WHEN** `batteryCapacity` is 10.0 and `soc` is 72
- **THEN** the card shows "7.2 of 10.0 kWh" below the SoC

---

### Requirement: BatteryStrategyCard displays strategy metrics in a 2×2 grid
The card SHALL display four strategy metrics below the SoC section: S-Index, Cycles, Safety Floor, and Tradable energy. These SHALL be derived from `plannerMeta` and `batteryCycles`. When a value is unavailable, it SHALL display "—".

S-Index is derived from `plannerMeta.s_index.effective_load_margin` (preferred) or `plannerMeta.s_index.risk_factor`, formatted as `x{value}` (e.g., "x1.42").
Safety Floor is `plannerMeta.s_index.safety_floor.calculated_floor_kwh`, shown in kWh.
Tradable is `batteryCapacity - safetyFloor`, shown in kWh.

#### Scenario: All metrics show when data is available
- **WHEN** plannerMeta and batteryCycles are populated
- **THEN** S-Index, Cycles, Safety Floor, and Tradable all display numeric values

#### Scenario: Metrics show dash when data is unavailable
- **WHEN** plannerMeta is null
- **THEN** S-Index, Safety Floor, and Tradable all display "—"

---

### Requirement: BatteryStrategyCard displays 7-day price outlook bars
When `priceOutlook` is available, the card SHALL display up to 7 days of price outlook as horizontal bars below the metrics. Each bar SHALL:
- Use color to indicate price level: green (`bg-green-500/80`) for cheap, amber (`bg-amber-500/80`) for normal, red (`bg-red-500/80`) for expensive, gray (`bg-gray-500/50`) for unknown
- Use bar width proportional to `(avg_spot_p50 / 2) * 100`, clamped between 5% and 100%
- Use opacity to reflect confidence: high = 1.0, medium = 0.7, low = 0.4
- Show the day label (first 3 characters) and the `avg_spot_p50` value to 2 decimal places

When `priceOutlook` is not yet available, the card SHALL show a "Price data loading..." placeholder.

#### Scenario: Price bars rendered for each available day
- **WHEN** `priceOutlook.days` contains 7 entries
- **THEN** 7 horizontal bars are rendered, each with day label, colored bar, and price value

#### Scenario: High-confidence day has full opacity bar
- **WHEN** a day has `confidence: 'high'`
- **THEN** its bar is rendered at opacity 1.0

#### Scenario: Low-confidence day has faded bar
- **WHEN** a day has `confidence: 'low'`
- **THEN** its bar is rendered at opacity 0.4

---

### Requirement: BatteryStrategyCard shows all content without tab interaction
The card SHALL display SoC, metrics, and price outlook all in a single scrollable view. There SHALL be no tab toggle, no hidden sections, and no click required to see any content.

#### Scenario: All content visible on load
- **WHEN** the user views the BatteryStrategyCard
- **THEN** SoC, metrics grid, and price outlook are all visible without any click or tab selection
