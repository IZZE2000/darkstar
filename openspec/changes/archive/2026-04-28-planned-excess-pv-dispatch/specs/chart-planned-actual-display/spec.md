## ADDED Requirements

### Requirement: Water heating boost bars use separate dataset with distinct style

The ChartCard SHALL render water heating boost bars as a separate bar dataset with teal color and sharp glow, visually distinct from normal water heating bars.

#### Scenario: Boost water bar renders with teal color
- **WHEN** a slot has water heating in boost mode
- **THEN** a bar SHALL appear using `rgba(0, 255, 200, 0.91)` for background color
- **AND** the bar SHALL use `#00ffc8ff` for border color
- **AND** the bar shape (width, border radius) SHALL be identical to normal water heating bars

#### Scenario: Boost water bar renders with sharp glow
- **WHEN** a slot has water heating in boost mode
- **THEN** the bar SHALL render with `shadowBlur: 20` and `shadowColor` opacity at 1.0
- **AND** the glow SHALL be sharp and bright

#### Scenario: Normal water bar renders without glow
- **WHEN** a slot has water heating in normal mode (not boost)
- **THEN** the water heating bar SHALL use the existing color scheme (`rgba(78, 168, 222, 0.25)`)
- **AND** the bar SHALL NOT have glow (`glow: false`)

#### Scenario: Both datasets toggle together
- **WHEN** user toggles the "Water Heating" overlay
- **THEN** both normal and boost water heating datasets SHALL show/hide together

### Requirement: Custom entity sink bar displayed in chart

The ChartCard SHALL render a bar dataset for the custom entity sink, visible in slots where the entity is toggled on.

#### Scenario: Custom entity bar displayed during excess PV slot
- **WHEN** the schedule has a custom entity active in slot 14
- **THEN** a bar SHALL appear at slot 14 using color `rgba(255, 182, 64, 0.81)` / `#FF9F40` border
- **AND** the bar height SHALL reflect the configured `power_kw` (from `executor.excess_pv.custom_entity.power_kw`)
- **AND** the bar SHALL have sharp glow (`shadowBlur: 20`, opacity 1.0)
- **AND** the bar SHALL be toggleable from the Overlays menu

#### Scenario: Custom entity bar toggleable from overlays
- **WHEN** the user opens the chart Overlays menu
- **THEN** an "Excess PV Sink" toggle SHALL appear
- **AND** toggling it off SHALL hide the custom entity sink bars
- **AND** toggling it on SHALL show them again

### Requirement: PV forecast overlay renders behind all bars

The PV forecast area/line dataset SHALL have `order: 20` so it renders behind all bar datasets (`order: 0`).

### Requirement: Only boost and custom entity bars have glow

All bar datasets except water heating boost and custom entity sink SHALL have `glow: false`. Only these two excess PV sink datasets SHALL have glow enabled.
