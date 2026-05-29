## Why

The Battery & Strategy card currently shows raw numbers without context — users see "S-Index x1.18" but don't know why, "Safety Floor 2.4 kWh" but not what drives it. The 7-day price outlook uses stacked horizontal bars that waste vertical space and convey little visual meaning. This card should tell the story of the strategy, not just dump data.

## What Changes

- Replace 7-day price outlook horizontal bars with a compact pixel sparkline (one colored square per day, positioned vertically by relative price, with a reference-average baseline)
- Add inline S-Index decomposition showing base factor, deficit contribution, and temperature contribution
- Add inline Safety Floor breakdown showing min-SOC reserve, temporal deficit, and weather buffer components
- Add a derived SOC context line (e.g., "charging ahead of cheap D1") under the SOC→Target display
- Preserve the SOC→Target display exactly as-is
- Preserve the planner's S-Index calculator debug fields in the schedule output (currently overwritten at pipeline.py:478)

## Capabilities

### New Capabilities

None — all changes are modifications to existing capabilities.

### Modified Capabilities

- `battery-strategy-card`: Price outlook rendering changes from horizontal bars to a pixel sparkline; S-Index and Safety Floor gain inline decomposition displays; SOC section gains a derived context line

## Impact

- **Frontend**: `BatteryStrategyCard.tsx` — significant rewrite of the price section, new decomposition logic for metrics
- **Backend**: `planner/pipeline.py:478` — preserve `avg_deficit`, `temp_adjustment`, `mean_temperature_c`, `pv_deficit_weight` in `s_index_debug` instead of overwriting
- **API**: No new endpoints; `PriceOutlookResponse` and `StatusResponse` data shapes unchanged
- **Design system**: New CSS classes in `index.css` for pixel sparkline, context line; showcase entries in `DesignSystem.tsx`
