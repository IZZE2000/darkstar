## 1. Backend: Preserve S-Index decomposition data

- [x] 1.1 Modify `planner/pipeline.py` line 478 to include `avg_deficit`, `temp_adjustment`, and `mean_temperature_c` in the `s_index_debug` dict instead of overwriting entirely

## 2. Frontend: CSS components

- [x] 2.1 Add `.price-sparkline` container class to `frontend/src/index.css` under `@layer components` with `position: relative`, fixed height, `bg-surface2 rounded-ds-sm`
- [x] 2.2 Add `.price-sparkline-block` class for individual day squares (10px × 10px, `rounded-ds-sm`, `absolute`, color variants via data attributes)
- [x] 2.3 Add `.price-sparkline-ref` class for the dashed reference average line (`border-t border-dashed border-line/40 absolute`, top controlled by inline style)
- [x] 2.4 Add showcase entries for pixel sparkline variants to `frontend/src/pages/DesignSystem.tsx`

## 3. Frontend: Rewrite BatteryStrategyCard

- [x] 3.1 Extract pixel sparkline rendering logic into a helper or inline computation: calculate min/max from 7-day prices, compute each square's vertical position, derive colors from `level`
- [x] 3.2 Replace the 7 stacked horizontal bars with the pixel sparkline (7 squares + ref_avg line + day labels + price values)
- [x] 3.3 Add S-Index decomposition line below the aggregate value, reading `avg_deficit`, `temp_adjustment`, `base_factor` from `plannerMeta.s_index`, with fallback when data is missing
- [x] 3.4 Add Safety Floor breakdown line, reading `min_soc_kwh`, `base_reserve_kwh`, `weather_buffer_kwh` from `plannerMeta.s_index.safety_floor`, with fallback
- [x] 3.5 Add SOC context line derived from schedule action and price outlook, displayed below the kWh display
- [x] 3.6 Replace the 2×2 metrics grid with a vertical stack (S-Index, Safety Floor, Cycles+Tradable inline row)
- [x] 3.7 Adjust section divider styling to match the new vertical stack layout

## 4. Verify

- [x] 4.1 Run `./scripts/lint.sh` and fix any failures
- [x] 4.2 Manual visual check: card renders correctly with all data present, with partial data (no S-index decomposition), and with no planner data (dashes shown)

## 5. Fixes & Improvements (post-review)

- [x] 5.1 Fix sparkline overflow: clamp `top` to ~80% (52px container - 10px block = 42px max) and add `overflow-hidden` safety net
- [x] 5.2 Add tooltips to sparkline blocks showing day name, avg price, min (p10) and max (p90) values
- [x] 5.3 Make SOC context line dynamic: scan price outlook for cheap/peak windows → "charging ahead of cheap D1→D3"
- [x] 5.4 Remove "ref X¢" text display (user request)
- [x] 5.5 Fix currency display: change from ¢ (cents) to öre (Swedish currency)
