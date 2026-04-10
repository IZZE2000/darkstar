## Context

Module 1 (price-forecasting-core) adds a `price_forecasts` DB table and a `GET /api/price-forecast` endpoint returning per-slot spot price predictions (p10/p50/p90) for D+1 through D+7. The `price_forecast.enabled` config toggle gates downstream consumption.

The existing analyst backend (`backend/api/routers/analyst.py`) produces advice items with `category`, `message`, and `priority` fields consumed by `SmartAdvisor.tsx`.

The dashboard has two rows of 3-column grids:
- **Row 2**: `AdvisorCard` (PowerFlow energy visualization), `ControlParameters`, `QuickActions`
- **Row 3**: `GridDomain`, `ResourcesDomain`, `StrategyDomain` ("Battery & Strategy" card showing SoC, S-Index, Safety Floor, Cycles)

The `AdvisorCard` is the live power flow chart — it is not an advisor text card and must not be changed.

## Goals / Non-Goals

**Goals:**
- Provide a 7-day visual price outlook widget on the dashboard for manual decision-making
- Extend the existing advisor with price-aware rule-based advice
- Serve an aggregated daily price outlook via a new API endpoint (frontend-friendly daily summaries)
- Gate all new UI and advice behind `price_forecast.enabled`
- Serve as the visual validation step before enabling downstream automation (S-Index, EV deferral)

**Non-Goals:**
- Building or modifying the underlying price forecast model (Module 1)
- LLM-generated advice (existing LLM path unchanged, but price context could enrich it in future)
- Modifying the Kepler solver or S-Index (Modules 3/4)
- Historical price chart visualization (future enhancement)

## Decisions

### 1. New `GET /api/price-forecast/outlook` endpoint for daily summaries

**Choice:** Create a new endpoint in the existing `price_forecast.py` router (created by Module 1) that aggregates per-slot forecasts into daily summaries for the UI widget.

**Why over reusing `/api/price-forecast`:** The raw endpoint returns hundreds of 15-min slots. The widget needs 7 daily objects with: date, average spot p50, min/max prices, and a relative level (cheap/normal/expensive) compared to the trailing 14-day average. Aggregation belongs on the backend to keep the frontend thin.

**Response shape:**
```json
{
  "enabled": true,
  "days": [
    {
      "date": "2026-03-30",
      "day_label": "Mon",
      "days_ahead": 1,
      "avg_spot_p50": 0.45,
      "avg_spot_p10": 0.32,
      "avg_spot_p90": 0.58,
      "min_hour_p50": 0.22,
      "max_hour_p50": 0.78,
      "level": "cheap",
      "confidence": "high"
    }
  ],
  "reference_avg": 0.52,
  "status": "ok"
}
```

- `level`: "cheap" (< 85% of trailing avg), "normal" (85-115%), "expensive" (> 115%). Thresholds are reasonable defaults, not config-driven initially.
- `confidence`: "high" (D+1/D+2), "medium" (D+3/D+4), "low" (D+5-D+7). Based on `days_ahead`.
- `reference_avg`: the 14-day trailing average spot price from `slot_observations.export_price_sek_kwh`, giving the user context for what "cheap" means.

### 2. Extend existing analyst router with price advice rules

**Choice:** Add price-aware advice items to the existing `_get_strategy_advice()` function in `analyst.py`, using a new `category: "price"`.

**Why over a separate advisor endpoint:** The existing advice format is already consumed. Adding a new category means the new view in the StrategyDomain card can render price advice items directly from the same endpoint. No new advisor endpoint needed.

**Rules:**
1. **Cheapest day ahead**: If any day in D+1..D+7 is 30%+ cheaper than today → "Prices drop ~X% on {day}. Consider deferring heavy loads."
2. **Prices rising**: If every day D+1..D+3 is higher than today → "Prices rising all week — today is the cheapest day in the next 3 days."
3. **Cheap overnight window**: If tonight's 22:00-06:00 average is 25%+ below the daily average → "Tonight 22:00-06:00 has the lowest prices — ideal for heavy loads."

Rules only fire when `price_forecast.enabled` is true and forecast data is available.

### 3. Price Outlook and Advisor integrated into StrategyDomain via toggle — no new cards

**Choice:** Add a toggle to the existing `StrategyDomain` component ("Battery & Strategy" card) that switches between two views:
- **View A (default)**: Current battery/strategy content — SoC, S-Index, Safety Floor, Cycles
- **View B**: Price outlook — 7-day weekly pills + price advice text items from the analyst endpoint

**Why no new layout elements:** The dashboard already has many cards. The `StrategyDomain` card is semantically the right home — both battery strategy and price strategy inform the same decisions. A toggle inside the card keeps the layout identical and keeps related concerns together. The card height stays fixed; both views fit within the same space.

**Toggle behavior:** A small tab or icon button in the card header switches views. The toggle only appears when `price_forecast.enabled` is true and forecast data exists. When forecast is disabled, the card shows only View A (battery/strategy) with no toggle.

### 4. Color and confidence encoding

**Choice:**
- **Colors**: Green (cheap), amber/yellow (normal), red (expensive). Three levels only — simple.
- **Confidence**: Opacity fading. D+1/D+2 at 100% opacity, D+3/D+4 at 75%, D+5-D+7 at 50%. CSS opacity, not a separate visual element.
- Today's pill is highlighted with a border/ring to orient the user.

**Why opacity over icons/badges:** Minimal visual noise. Users intuitively read faded = less certain. No additional legend needed.

### 5. Frontend fetches outlook in Dashboard, passes as props to StrategyDomain

**Choice:** `Dashboard.tsx` fetches `GET /api/price-forecast/outlook` alongside its other deferred data fetches. The result is passed as props to `StrategyDomain`. The `StrategyDomain` component handles toggling and rendering both views.

**Why:** Keeps data fetching centralized in the Dashboard (existing pattern). `StrategyDomain` becomes a pure presentational component that receives outlook data and advice items as props, matching how it already receives `soc`, `sIndex`, etc.

## Risks / Trade-offs

- **[No forecasts available yet]** → New systems or systems with `price_forecast.enabled: false` see no widget and no price advice. Mitigation: the widget and advisor rules check for data availability and hide gracefully. The advisor continues to show non-price advice (risk, vacation, battery) as before.
- **[Trailing average cold start]** → The 14-day trailing average needs 14 days of price history. Mitigation: fall back to a 7-day or whatever is available. If less than 2 days of history, skip the relative level and show raw forecast values without color coding.
- **[Rule threshold sensitivity]** → The 30%/25% thresholds for advice rules may be too sensitive or too conservative for different price areas. Mitigation: start with reasonable defaults and tune based on user feedback. These are implementation constants, not config — easy to adjust.
