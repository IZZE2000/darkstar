# Battery Strategy Card

## Purpose

TBD - Defines the BatteryStrategyCard component that displays battery state of charge, strategy metrics (S-Index, Cycles, Safety Floor, Tradable energy), and 7-day price outlook.

## Requirements

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

### Requirement: BatteryStrategyCard displays strategy metrics in a vertical stack
The card SHALL display strategy metrics below the SoC section in a vertical stack: S-Index (with optional decomposition line), Safety Floor (with optional breakdown line), and a compact inline row for Cycles and Tradable energy. These SHALL be derived from `plannerMeta`, `batteryCycles`, and `batteryCapacity`. When a value is unavailable, it SHALL display "—".

S-Index is derived from `plannerMeta.s_index.effective_load_margin` (preferred) or `plannerMeta.s_index.risk_factor`, formatted as `x{value}` (e.g., "x1.42"). When decomposition data is present, a second line SHALL show contributing factors.

Safety Floor is `plannerMeta.s_index.safety_floor.calculated_floor_kwh`, shown in kWh. When breakdown data is present, a second line SHALL show reserve components.

Tradable is `batteryCapacity - safetyFloor`, shown in kWh.

#### Scenario: All metrics show when data is available
- **WHEN** plannerMeta and batteryCycles are populated
- **THEN** S-Index (with decomposition if available), Safety Floor (with breakdown if available), Cycles, and Tradable all display numeric values

#### Scenario: Metrics show dash when data is unavailable
- **WHEN** plannerMeta is null
- **THEN** S-Index, Safety Floor, and Tradable all display "—"

---

### Requirement: BatteryStrategyCard displays price outlook as a pixel sparkline
When `priceOutlook` is available, the card SHALL display up to 7 days of price outlook as a pixel sparkline below the metrics. The sparkline SHALL consist of one colored square per day, vertically positioned by relative price within the 7-day range. Color SHALL indicate price level: `bg-good` for cheap, `bg-warn` for normal, `bg-bad` for expensive, `bg-muted` for unknown. Positions SHALL be continuous (CSS `top` percentage) based on `(avg_spot_p50 - min) / (max - min)`. Squares SHALL have `rounded-ds-sm` radius and SHALL NOT be connected by lines. A `reference_avg` dashed line SHALL be shown when available. Day labels and `avg_spot_p50` values SHALL be displayed below the chart.

Confidence SHALL be indicated by the `reference_avg` line's presence (gives context for level classification) rather than by individual bar opacity.

When `priceOutlook` is not yet available, the card SHALL show a "Price data loading..." placeholder.

#### Scenario: Sparkline renders one colored square per day
- **WHEN** `priceOutlook.days` contains 7 entries
- **THEN** 7 colored squares are rendered, each at a vertical position proportional to its price relative to the 7-day range, with day label and price value below

#### Scenario: Squares positioned by relative price
- **WHEN** a day has the highest `avg_spot_p50` in the 7-day range
- **THEN** its square is at or near the top of the chart; the lowest-priced day sits at or near the bottom

#### Scenario: Loading placeholder when no data
- **WHEN** `priceOutlook` is undefined or has zero days
- **THEN** the card displays "Price data loading..." centered in the price section

---

### Requirement: BatteryStrategyCard displays S-Index with inline decomposition
The card SHALL display the S-Index value alongside a compact decomposition line showing the contributing factors. When `plannerMeta.s_index` contains `avg_deficit`, `temp_adjustment`, and `base_factor`, a second line SHALL show: `base {base_factor} · deficit +{contribution} · cold +{contribution}`. When decomposition data is unavailable, only the aggregate `x{effective_load_margin}` value SHALL be shown.

#### Scenario: S-Index shown with full decomposition
- **WHEN** `plannerMeta.s_index.effective_load_margin` is 1.18 and `plannerMeta.s_index` contains `avg_deficit: 0.05`, `temp_adjustment: 0.03`, and `base_factor: 1.10`
- **THEN** the card displays "x1.18" on one line and "base 1.10 · deficit +0.05 · cold +0.03" on the next

#### Scenario: S-Index shown without decomposition when data missing
- **WHEN** `plannerMeta.s_index.effective_load_margin` is 1.18 but `avg_deficit` and `temp_adjustment` are not present
- **THEN** the card displays "x1.18" without a decomposition line

#### Scenario: S-Index shows dash when unavailable
- **WHEN** `plannerMeta` is null or `plannerMeta.s_index` has no `effective_load_margin` or `risk_factor`
- **THEN** the card displays "—" for S-Index

---

### Requirement: BatteryStrategyCard displays Safety Floor with inline breakdown
The card SHALL display the Safety Floor value in kWh alongside a compact breakdown line showing the contributing reserves. When `plannerMeta.s_index.safety_floor` contains component values, a second line (or inline suffix) SHALL show: `min {min_soc_kwh} · deficit {base_reserve_kwh} · weather {weather_buffer_kwh}`. When breakdown data is unavailable, only the `calculated_floor_kwh` value SHALL be shown.

#### Scenario: Safety Floor shown with full breakdown
- **WHEN** `plannerMeta.s_index.safety_floor.calculated_floor_kwh` is 2.4 and `min_soc_kwh` is 0.8, `base_reserve_kwh` is 1.2, `weather_buffer_kwh` is 0.6
- **THEN** the card displays "2.4 kWh" and "min 0.8 · deficit 1.2 · weather 0.6"

#### Scenario: Safety Floor shown without breakdown when data missing
- **WHEN** `plannerMeta.s_index.safety_floor.calculated_floor_kwh` is 2.4 but component values are not present
- **THEN** the card displays "2.4 kWh" without a breakdown line

---

### Requirement: BatteryStrategyCard displays a SOC context line
The card SHALL display a single-line context message below the SoC→Target display describing the current strategy intent. The message SHALL be derived from the schedule slot action and price outlook context. When insufficient data is available to derive a message, no context line SHALL be displayed.

#### Scenario: Context line shows charging intent
- **WHEN** the current slot action is `charge` and upcoming days have cheap prices
- **THEN** the context line reads "charging ahead of cheap D1→D3" or similar

#### Scenario: Context line shows discharge intent
- **WHEN** the current slot action involves export or discharge and prices are high
- **THEN** the context line indicates exporting or discharging

#### Scenario: No context line when data insufficient
- **WHEN** price outlook data is unavailable
- **THEN** no context line is displayed

---

### Requirement: BatteryStrategyCard displays reference average in the sparkline
When `priceOutlook.reference_avg` is present and non-null, the sparkline SHALL display a dashed horizontal line at the vertical position corresponding to `reference_avg` within the 7-day price range. The line SHALL use `border-line/40` styling and span the full width of the chart container. The `reference_avg` value SHALL NOT be shown as a text label (removed per user request).

#### Scenario: Reference line shown when reference_avg is available
- **WHEN** `priceOutlook.reference_avg` is 13.2 and the 7-day range is 5-17
- **THEN** a dashed line is positioned within the chart at the level corresponding to 13.2 (68% from bottom)
- **AND** no text label for the reference value is displayed

#### Scenario: No reference line when reference_avg is null
- **WHEN** `priceOutlook.reference_avg` is null
- **THEN** no reference line is displayed

---

### Requirement: BatteryStrategyCard shows all content without tab interaction
The card SHALL display SoC, metrics, and price outlook all in a single scrollable view. There SHALL be no tab toggle, no hidden sections, and no click required to see any content.

#### Scenario: All content visible on load
- **WHEN** the user views the BatteryStrategyCard
- **THEN** SoC, metrics grid, and price outlook are all visible without any click or tab selection
