# Blueprint: Multi-Day Energy Price Forecasting

**Objective:** Implement a 7-day rolling price forecast to enable strategic multi-day planning for deferrable loads (EVs, heavy appliances) and to power a new "Weekly Outlook" dashboard widget and local advisor.

**Constraints:**
- 100% Local processing (no LLM API for the advisor).
- No new external API keys required (use Open-Meteo and existing Nordpool library).
- The Kepler MILP solver must safely remain on D0/D1 exact Nordpool prices.
- A global `price_forecast.enabled` toggle (disabled by default) controls whether downstream modules consume forecasts. This serves as a kill-switch during validation and prevents new systems with insufficient data from using unreliable forecasts.

---

## Implementation Order

The 4 modules are implemented as separate OpenSpec changes for manageability, but they form one logical initiative. The order reflects dependencies and validation needs:

1. **Forecasting Core** — The engine (weather extension, model, DB schema)
2. **Advisor & Weekly Outlook** — The eyes (visual validation that forecasts look sane)
3. **S-Index Enhancement** — Light strategic integration (influence battery decisions)
4. **EV Deferral Controller** — Heavy integration (automated multi-day charging)

Modules 2-4 all depend on Module 1. The Advisor/Outlook lands before the EV controller because users (and developers) need to *see* and validate forecasts before trusting them for automated decisions.

---

## The 4-Module Architecture

### Module 1: The Forecasting Pipeline (Aurora Extension)
**Purpose:** Generate daily directional price forecasts and hourly quantiles for D+1 (before 13:00 auction) through D+7.

- **Weather Extension:**
  - Extend `ml/weather.py` to fetch a 16-day Open-Meteo forecast (currently 2 days).
  - Add new parameters: `wind_speed_10m` (or `wind_speed_100m`), and any other relevant params. Wind is the primary marginal price driver in the Nordics.
  - Fetch weather for multiple coordinates per price area to build a **regional wind index** — an averaged wind metric that captures cross-border generation influence (e.g., for SE4: local + Denmark East + Northern Germany).

- **Regional Weather Coordinates:**
  - Stored in a dedicated file (e.g., `data/regions.json` or similar), keyed by Nordpool price area.
  - Initially populated for SE1-SE4 only. Future expansion to other Nordpool areas (NO1-NO5, DK1-DK2, FI, etc.) requires only adding entries to this file — no code changes.
  - Each entry maps a price area to a list of named coordinate sets with lat/lon.
  - The ML pipeline reads this file, fetches weather for all coordinates of the user's configured `price_area`, and computes an averaged regional wind index as a single feature (not raw multi-point values).

  Example structure:
  ```json
  {
    "SE4": {
      "local": {"lat": 55.6, "lon": 13.0, "label": "Malmö area"},
      "denmark_east": {"lat": 55.7, "lon": 12.5, "label": "Copenhagen area"},
      "germany_north": {"lat": 54.1, "lon": 12.1, "label": "Rostock area"}
    },
    "SE3": {
      "local": {"lat": 59.3, "lon": 18.1, "label": "Stockholm area"},
      "...": "..."
    }
  }
  ```

- **Price Data for Training:**
  - **Training target:** The model predicts **raw Nordpool spot price**, using existing `slot_observations.export_price_sek_kwh` (which is the raw spot price, no fees/taxes). At inference time, forecasted import/export prices are derived by applying the same fee/VAT/tax logic from `backend/core/prices.py`. This ensures the model is immune to tax policy changes.
  - **Honest training (no future data leakage):** Each forecast record stores the weather inputs used at issue time alongside the prediction. When training, the model learns from (weather_forecast_at_prediction_time → actual_spot_price) pairs, not from actual realized weather. Since `days_ahead` is a model feature, it naturally learns that D+3 weather forecasts are noisier than D+1. No separate weather snapshot system needed — the forecast record itself is the training sample.
  - Follow the existing learning-tier pattern: the price model activates only after sufficient paired (price + weather) data has accumulated. New systems get no price forecasts until the data threshold is met. This mirrors how load/PV models already handle cold-start.
  - No backfill required as a hard dependency. (Vattenfall API + Open-Meteo historical archive exist as future options if faster cold-start proves valuable.)

- **D+1 Coverage:**
  - The model generates forecasts for D+1 through D+7.
  - D+1 forecasts are used as a fallback before ~13:00 CET when Nordpool day-ahead auction results aren't available yet.
  - Once real Nordpool D+1 prices arrive, they replace the forecast automatically.

- **Model:**
  - LightGBM quantile regression (p10/p50/p90), consistent with existing Aurora models.
  - Features: calendar (hour, day_of_week, month, is_weekend, is_holiday), regional wind index, local temperature, cloud cover, solar radiation, price lags (same hour yesterday, same hour last week, trailing daily average).
  - `days_ahead` as a feature (single model, not per-horizon-day models) for simplicity.

- **Output:** Save price forecast records to `planner_learning.db` (new table or extension of `slot_forecasts`).

### Module 2: The Local Advisor & Weekly Outlook UI
**Purpose:** Translate raw ML forecasts into human-readable advice and a dashboard widget so users can validate forecasts and make informed manual decisions.

- **Weekly Outlook Widget:**
  - A 7-day pill indicator in the React dashboard.
  - Each pill uses color (green/yellow/red) to indicate the relative daily price level compared to the trailing 14-day average.
  - Confidence encoding: solid pills for near-term (D+1/D+2, high confidence), progressively faded for D+6/D+7 (lower confidence).
  - Only visible when `price_forecast.enabled` is true.

- **Advisor Engine:**
  - A rule-based engine integrated into the existing SmartAdvisor/analyst infrastructure (which already supports rule-based mode when `enable_llm: false`).
  - Consumes PV, Load, and Price forecasts to emit JSON-formatted advice.
  - Example rules:
    - "Prices drop ~40% on Thursday. Consider delaying heavy appliances."
    - "Prices rising all week — today is the cheapest day."
    - "Tonight 22:00-06:00 has the lowest prices this week."
  - Respects the `price_forecast.enabled` toggle.

### Module 3: The Strategic Pipeline (S-Index Enhancement)
**Purpose:** Allow the price forecast to influence daily battery hold/discharge decisions.

- **Update:** Enhance `planner/strategy/s_index.py`.
- **Logic:** If the 7-day price trend indicates a significant price drop ahead, the S-Index can slightly reduce the safety floor (via deficit ratio or base reserve inflation) to allow Kepler to drain the battery in anticipation of cheap recharge. If prices are rising, it inflates the deficit ratio to force Kepler to stockpile energy. Note: Darkstar uses Physical Deficit Logic, not a Terminal Value System — all adjustments flow through the existing S-Index mechanisms.
- Gated behind `price_forecast.enabled`.

### Module 4: The Multi-Day Deferral Controller
**Purpose:** Sit above the Kepler solver to distribute energy requirements across multiple days based on forecast trends.

- **Concept:** A reusable `MultiDayPlanner` class. It takes an energy target (e.g., 60 kWh), a deadline (e.g., Friday 07:00), and the 7-day price forecast.
- **Logic:** It calculates a daily quota (e.g., "0 kWh today, 10 kWh tomorrow, 50 kWh Thursday").
- **Kepler Integration:** The daily Kepler solver only sees the quota assigned to *today*. It then optimizes those specific kWh using exact Nordpool prices. If Thursday's forecast was wrong when Thursday arrives, the actual Nordpool prices that day dictate the exact charge schedule, ensuring safety.
- **EV Integration:** Extends the existing `departure_time` concept with an optional multi-day deadline mode. The existing single-day departure behavior remains the default.
- Gated behind `price_forecast.enabled`.

---

## Future Expansion Considerations
- **New Nordpool Areas:** Adding support for NO1-NO5, DK1-DK2, FI, etc. requires only populating `regions.json` with appropriate coordinate sets — no model or pipeline changes.
- **ENTSO-E Integration:** If the regional wind index approach struggles to predict extreme nuclear/hydro outages, a future module can add ENTSO-E data ingestion without affecting Modules 2, 3, or 4.
- **Vattenfall Price Backfill:** If faster cold-start is desired, historical price data could be backfilled via the Vattenfall API, paired with historical Open-Meteo weather data (available via their archive API).
