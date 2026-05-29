## Context

The BatteryStrategyCard occupies a tall, narrow column (col 3, row-span-2) in the dashboard grid at `lg` breakpoint. It currently shows:
1. SOC → Target with color coding (keep as-is)
2. A 2×2 metrics grid: S-Index, Cycles, Safety Floor, Tradable
3. A 7-day price outlook as 7 stacked horizontal bars

The card receives data from multiple sources:
- `soc`, `batteryCapacity`: live executor status (WebSocket)
- `socTarget` (= `currentSlotTarget`): derived from the planner's current schedule slot
- `plannerMeta`: from schedule.json `meta` field, includes S-index and safety floor debug data
- `batteryCycles`: from today's aggregated stats
- `priceOutlook`: from `GET /api/price-forecast/outlook`

**Data gap**: The planner's `pipeline.py:478` overwrites `s_index_debug` with a simplified dict, discarding the calculator's decomposition fields (`avg_deficit`, `temp_adjustment`, `mean_temperature_c`, `pv_deficit_weight`). These are computed at lines 423/437 via `s_index_debug.update(s_debug)` but then replaced.

**Reference average**: `PriceOutlookResponse.reference_avg` is available but not displayed. It's the 14-day trailing average spot price used to classify cheap/normal/expensive tiers. Showing it gives users context for what "cheap" means.

## Goals / Non-Goals

**Goals:**
- Replace horizontal price bars with a compact pixel sparkline (one square per day, vertically positioned by relative price, color-coded by tier)
- Show S-Index as `xN.NN` with an inline decomposition: `base N.NN · deficit +N.NN · temp +N.NN`
- Show Safety Floor as `N.N kWh` with an inline breakdown: `min N.N · deficit N.N · weather N.N`
- Add a derived one-line context message under SOC→Target (e.g., "charging ahead of cheap D1→D3")
- Show the `reference_avg` value as a subtle dashed line across the sparkline
- Preserve S-Index calculator debug fields through the planner pipeline

**Non-Goals:**
- Change the SOC→Target display or color logic
- Change the Cycles or Tradable metric computations
- Change the dashboard grid layout or card position
- Modify the `PriceOutlookResponse` API shape
- Add user interaction (tooltips, expand/collapse) — all content is always visible per existing spec requirement

## Decisions

### Decision 1: Pixel sparkline layout

**Chosen**: One colored square per day, vertically positioned continuously (not snapped to discrete rows), relative to the 7-day price range. No connecting lines. A dashed horizontal line at the `reference_avg` level. Day labels and price values below.

**Rationale**: This compresses the price section from ~150px (7 stacked bars + labels + spacing) to ~55px. The continuous vertical position preserves the exact price shape within the week. No connecting lines keeps the pixel-art aesthetic clean. Relative scaling ensures the shape is visible even when spot prices vary within a narrow band.

**Alternatives considered**:
- Absolute price scale (each Y-px = N cents): Rejected — narrow price ranges would all sit at similar heights, making the chart uninformative
- Snapped to discrete rows (e.g., 5 levels): Rejected — loses granularity; continuous positioning is easy with CSS `top` percentages
- With connecting lines: Rejected — adds visual noise without improving readability
- Keep horizontal bars but compact: Rejected — still wastes vertical space; pixel sparkline is more distinctive

**Implementation**: Each day column (7 columns in a flex row) contains a single square `<div>` positioned via `style={{ top: `${(1 - normalizedPrice) * containerHeight}px` }}`. The container has `position: relative; height: 100px`. Squares are 10px × 10px, `rounded-ds-sm`, colored by tier. The ref_avg line is a `position: absolute` horizontal border across the container.

### Decision 2: S-Index decomposition display

**Chosen**: Two-line display: first line shows the aggregate value (`xN.NN`), second line shows inline breakdown with small labels.

Format: `<value>` on one line, then `base N.NN · D1 def +N.NN · cold +N.NN` on the next.

The decomposition components come from the S-Index calculator debug fields (once preserved):
- `base_factor`: the configured/learned base factor
- `avg_deficit`: average D1 load deficit ratio, already weighted by `pv_deficit_weight` when first displayed? No — the contribution is `pv_deficit_weight * avg_deficit`. Show this as `deficit +X.XX`
- `temp_adjustment`: the temperature penalty fraction, already weighted by `temp_weight`. Show as `cold +X.XX` (or `temp +X.XX`)

The card reads these from `plannerMeta.s_index.avg_deficit`, `plannerMeta.s_index.temp_adjustment`, `plannerMeta.s_index.base_factor`. Falls back to just showing the aggregate if decomposition data is unavailable.

**Rationale**: Two lines keep the display compact while providing the "why" context. Inline format uses minimal vertical space (2 lines vs. a panel with bullet points).

### Decision 3: Safety Floor breakdown display

**Chosen**: Single-line inline breakdown: `min N.N · deficit N.N · weather N.N`.

Components from `plannerMeta.s_index.safety_floor`:
- `min_soc_kwh`: the configured minimum SOC reserve (already in the debug output)
- `base_reserve_kwh`: the temporal deficit reserve (already in the debug output, key `base_reserve_kwh`)
- `weather_buffer_kwh`: the weather-driven extra buffer (already in the debug output)

**Rationale**: Safety floor data is already fully available in the API — no backend changes needed. The single-line format is more compact than the two-line S-Index format because the components are simpler to label.

### Decision 4: SOC context line

**Chosen**: Derive from the current schedule slot's action type and the price outlook. Pure frontend logic — no new data needed.

Mapping:
- `action = charge`, `SOC < Target`: "charging ahead of cheap D1→D3" (find the next cheap window)
- `action = export/discharge`, `SOC > Target`: "exporting into evening peak"
- `action = discharge`, `SOC > Target`: "discharging — next charge D2"
- `action = hold`: "holding — price neutral"
- `action = charge`, `SOC already > Target` or large gap: "recovering — deep discharge"

The `currentSlotTarget` (already passed as `socTarget`) and the `priceOutlook.days` can be used to determine which upcoming days are cheap/expensive.

The context line uses `text-[10px] text-muted` styling, placed below the kWh display.

### Decision 5: Backend S-index debug preservation

**Chosen**: Modify `planner/pipeline.py` line 478 to merge the calculator debug fields into the simplified `s_index_debug` dict instead of overwriting.

Current (line 478-484):
```python
s_index_debug = {
    "mode": "physical_deficit",
    "base_factor": base_factor,
    "effective_load_margin": effective_load_margin,
    "raw_factor": raw_factor,
    "safety_floor": soc_debug,
}
```

Changed to:
```python
s_index_debug = {
    "mode": "physical_deficit",
    "base_factor": base_factor,
    "effective_load_margin": effective_load_margin,
    "raw_factor": raw_factor,
    "avg_deficit": s_index_debug.get("avg_deficit"),
    "temp_adjustment": s_index_debug.get("temp_adjustment"),
    "mean_temperature_c": s_index_debug.get("mean_temperature_c"),
    "safety_floor": soc_debug,
}
```

The existing `s_index_debug.update(s_debug)` at lines 423/437 already populated these fields. We just stop overwriting them.

**Rationale**: Minimal change (5 lines), zero risk of breaking existing consumers. The `meta.s_index` object is consumed by the frontend's `StatusResponse.local.s_index` which has a `[key: string]: unknown` catch-all — new fields are silently accepted.

### Decision 6: Card section order and dividers

**Chosen**: Keep the top-down flow with thin dividers between sections. The price sparkline stays at the bottom (user request).

```
Header line
══════════════════ (border-b border-line/30, slightly heavier)
SOC → Target + kWh + context line
────────────────── (divider)
S-Index (value + decomposition)
Safety Floor (value + breakdown)
Cycles · Tradable (inline row)
══════════════════
Price sparkline + labels
```

The 2×2 metrics grid is replaced with a vertical stack of metric rows, each showing the main value and decomposition.

### Decision 7: Design system compliance

All new visual elements follow the design system:
- **Spacing**: `p-ds-4` (16px) card padding, `gap-ds-1` (4px) for tight internal gaps, `gap-ds-3` (12px) between sections
- **Colors**: `text-accent`/`text-good`/`text-warn`/`text-bad` for semantic indicators, `text-muted` for labels, `text-text` for values
- **Typography**: `text-[9px] text-muted uppercase tracking-wider` for micro labels, `text-base font-semibold` for metric values, `text-[10px]` for decomposition lines
- **Borders**: `border-b border-line/30` for section dividers
- **Radius**: `rounded-ds-sm` (8px) for pixel blocks, `rounded-ds-lg` (16px) for the card itself
- **Surface**: `bg-surface` for card background, `bg-surface2` for pixel sparkline container background

New CSS classes defined in `index.css` under `@layer components`:
- `.price-sparkline` — container with relative positioning for the pixel chart
- `.price-sparkline-block` — individual day square (size, border-radius, transition)
- `.price-sparkline-ref` — dashed reference average line

## Risks / Trade-offs

- **S-Index decomposition unavailable**: If the user's S-index config uses `mode: "probabilistic"` instead of `"dynamic"`, the decomposition fields (`avg_deficit`, `temp_adjustment`) won't exist. The frontend falls back to showing just the aggregate value without decomposition. **Mitigation**: Type-safe optional chaining; conditionally render the decomposition line only when data exists.
- **Relative price scaling hides absolute price levels**: A week where all prices are within 12-15¢ will look the same as a week where prices range 5-20¢. **Trade-off accepted** — the sparkline is about intra-week shape, not cross-week comparison. The price values are shown as text below each day.
- **Pipeline change backward compatibility**: The new fields in `s_index_debug` are additive. Old schedule.json files won't have them, and the frontend handles missing keys gracefully. **No risk**.
