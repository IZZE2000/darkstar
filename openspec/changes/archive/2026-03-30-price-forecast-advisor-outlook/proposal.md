## Why

Module 1 (price-forecasting-core) produces 7-day rolling spot price forecasts, but there is currently no way for users to see or act on these predictions. Without a visual validation layer, the system would be consuming forecasts for automated decisions (S-Index, EV deferral) before anyone has confirmed they look reasonable. The Weekly Outlook and Advisor give users immediate value — seeing that prices drop Thursday means they can defer heavy appliance use manually — and serve as the validation step before downstream automation modules are enabled.

## What Changes

- Add a **Weekly Outlook** widget to the React dashboard: 7-day price pill indicators showing relative daily price levels (green/yellow/red) with confidence fading for distant days.
- Add a **Price Advisor** rule-based engine to the existing analyst backend that consumes price forecasts and emits actionable text advice (e.g., "Prices drop ~40% on Thursday — consider deferring heavy loads").
- Add a new **price forecast API endpoint** for the frontend to fetch the 7-day outlook data (daily summaries suitable for UI consumption, distinct from Module 1's per-slot raw forecast endpoint).
- All new UI and advice is gated behind the existing `price_forecast.enabled` config toggle — hidden when disabled.
- Integrate price advice into the existing SmartAdvisor component alongside current risk/mode/battery recommendations.

## Capabilities

### New Capabilities

- `weekly-outlook-widget`: The React dashboard component showing 7-day price pills with color-coded price levels and confidence encoding. Includes the frontend data fetching logic.
- `price-advisor-engine`: The rule-based backend engine that analyzes price forecast trends and generates human-readable advice. Covers the rules, thresholds, and JSON output format.
- `price-outlook-api`: The backend API endpoint that serves daily price outlook summaries (aggregated from Module 1's per-slot forecasts) to the frontend widget and advisor.

### Modified Capabilities

- None. This change consumes Module 1's existing `GET /api/price-forecast` and config toggle without modifying their specs.

## Impact

- **Frontend** (`frontend/src/`): New `WeeklyOutlook` component, updated `Dashboard.tsx` layout, updated `api.ts` with new fetch method.
- **Backend** (`backend/api/routers/`): New or extended analyst endpoint for price outlook data.
- **Backend** (`backend/api/routers/analyst.py`): Extended with price-aware advice rules.
- **Config**: No new config keys — uses existing `price_forecast.enabled` from Module 1.
- **Dependencies**: No new external dependencies.
