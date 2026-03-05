## Why

Historical data in ChartCard incorrectly displays actual values as both the main chart elements (bars/lines) AND overlay lines. The planned/forecasted values are lost when slots transition from future to history. Users cannot compare what was planned vs what actually happened, making it impossible to evaluate forecast accuracy and planner performance.

## What Changes

- Main chart bars/lines will display **planned/forecasted values** for ALL slots (both historical and future)
- Overlay lines (dotted) will display **actual values** for historical slots only
- This applies to all metrics: charge, discharge, PV, load, water heating, EV charging, export, SOC
- The backend already provides both `battery_charge_kw` (planned) and `actual_charge_kw` correctly
- Fix is purely frontend display logic in `ChartCard.tsx`

## Capabilities

### New Capabilities

- `chart-planned-actual-display`: ChartCard displays planned/forecasted values as solid lines/bars through entire 48h window, with actual values shown as dotted overlay lines for historical slots

### Modified Capabilities

<!-- No existing specs modified - this is a frontend display fix -->

## Impact

- **Frontend**: `frontend/src/components/ChartCard.tsx` - data array population logic
- **No backend changes required** - backend correctly provides both planned and actual values
- **No API changes** - existing response fields are sufficient
- **No database changes** - `slot_plans` and `slot_observations` tables already contain correct data
