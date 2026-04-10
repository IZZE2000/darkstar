## Context

The price-forecasting-core change was implemented and archived, but post-review identified a bootstrap bug: `generate_price_forecasts()` in `ml/price_forecast.py` returns `[]` at lines 102-111 if any of the three quantile model files are missing. This function is only called from `ml/training_orchestrator.py` inside the `if price_success:` block (line 244). On a fresh install, no model → no rows → no training pairs → no model, indefinitely.

The DB schema already supports null spot columns (`spot_p10`, `spot_p50`, `spot_p90` are nullable floats). The training query in `ml/price_train.py` selects only `wind_index`, `temperature_c`, `cloud_cover`, `radiation_wm2` from `price_forecasts` — it never reads the spot columns. So writing rows with null predictions is safe for training.

## Goals / Non-Goals

**Goals:**
- Allow weather snapshot rows to accumulate in `price_forecasts` from day one on a fresh install
- Ensure the D+1 fallback never serves null-prediction rows to the planner
- Reach the 500-pair training threshold within ~1 week of install rather than indefinitely
- Stay aligned with the original spec intent (task 8.1 said "runs daily regardless of enabled")

**Non-Goals:**
- Schema changes (nullable columns already exist)
- Changes to training logic or model architecture
- Backfilling historical weather data

## Decisions

### Decision: Null predictions in weather-only rows (vs. splitting into two functions)

Keep a single `generate_price_forecasts()` function. When no model exists, still fetch weather, build feature rows, and persist with `spot_p10 = spot_p50 = spot_p90 = None`. Splitting into a separate "weather recorder" function was considered but adds complexity for no benefit — the nullable columns were designed for exactly this case, and the training query ignores the spot columns entirely.

### Decision: Guard the D+1 fallback with `WHERE spot_p50 IS NOT NULL`

`get_d1_price_forecast_fallback()` currently calls `get_price_forecasts_from_db()` with no filter on spot values. On a fresh install with only weather-only rows present, this would return rows with `spot_p50 = None`, which then get passed to `derive_consumer_prices()` where `forecast.get("spot_p50", 0)` substitutes `0` — telling the planner electricity is free. The fix is a targeted filter in the fallback query, not in `get_price_forecasts_from_db()` itself (that function serves other use cases).

### Decision: Daily tick for weather accumulation (not planner-coupled)

Options considered:
- **Every 30 min with planner**: 48 runs/day × 3 coordinates × 7 days = 1,008 Open-Meteo calls/day, and 32K rows/day. Redundant — weather doesn't change meaningfully sub-hourly.
- **Weekly with training only**: Only 2 runs/week. Too slow to bootstrap — would take many weeks.
- **Daily dedicated tick**: 672 rows/day (7 days × 24h × 4 slots), ~21 API calls/day. Reaches 500 training pairs in ~5 days once actual prices exist. Clean separation from planner.

Daily tick is the right balance. Implement as a separate scheduler entry (e.g., 06:00 daily) in the same orchestrator that runs training. This is separate from the training schedule (Tue/Fri 03:00).

### Decision: Move forecast call outside `if price_success:` in orchestrator

On training days, `generate_price_forecasts()` should run regardless of whether training succeeded. This gives an additional weekly snapshot even for the training-day slots, and matches the original spec intent.

## Risks / Trade-offs

- **Null rows served as forecasts**: Mitigated by the `spot_p50 IS NOT NULL` guard in the fallback. Any other consumer of `get_price_forecasts_from_db()` (e.g., the API endpoint) should similarly handle null spots gracefully — review API endpoint response serialization.
- **DB growth from daily ticks**: 672 rows/day × 365 = ~245K rows/year. Trivial for SQLite in a home system. No pruning needed.
- **Duplicate rows on same slot_start**: Multiple `issue_timestamp` values per `slot_start` are intentional — they represent different forecast snapshots and all become valid training pairs.
- **Open-Meteo rate limit**: 21 calls/day is well within the 10K/day free tier.
