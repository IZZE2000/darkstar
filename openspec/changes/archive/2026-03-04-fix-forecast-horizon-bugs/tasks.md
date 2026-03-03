## 1. Backend API Fix - History Series Location

- [x] 1.1 Open `backend/api/routers/forecast.py` and locate the dashboard response construction (~line 388)
- [x] 1.2 Move `history_series` from root level into the `stats` dictionary (which becomes `horizon` in the response)
- [x] 1.3 Verify the response structure matches the TypeScript AuroraDashboard type

## 2. Backend ML Fix - Timestamp Format

- [x] 2.1 Open `ml/api.py` and locate the Open-Meteo data enrichment code (~line 73)
- [x] 2.2 Change `ts_str = str(ts_idx)` to `ts_str = ts_idx.isoformat()`
- [x] 2.3 Verify the timestamp format now matches the slot lookup format (~line 99)

## 3. Backend - Expand to 72h Window (3 Days)

- [x] 3.1 Open `backend/api/routers/forecast.py` and locate horizon window calculation
- [x] 3.2 Change `horizon_start` from `start_of_today` to `start_of_yesterday` (today - 1 day)
- [x] 3.3 Update `horizon_hours` from 48 to 72
- [x] 3.4 Update any labels or descriptions that reference "48h"

## 4. Backend - Always Use Forecast API for Open-Meteo

- [x] 4.1 Open `ml/weather.py` and locate the conditional archive/forecast API logic
- [x] 4.2 Remove the conditional `if end_date_obj <= today_local` block
- [x] 4.3 Always use forecast API URL with `past_days=1` and `forecast_days=2` parameters
- [x] 4.4 Remove archive API URL and related logic

## 5. Verification and Testing

- [x] 5.1 Run `./scripts/lint.sh` and fix any issues
- [ ] 5.2 Start the dev environment (`pnpm run dev`) and verify Aurora dashboard loads *(User verification)*
- [ ] 5.3 Verify "Actual" data line appears with historical values (yesterday + today) *(User verification)*
- [ ] 5.4 Verify Open-Meteo forecast line appears for all 3 days (yesterday+today+tomorrow) *(User verification)*
- [ ] 5.5 Verify per-array breakdown lines appear when multiple arrays configured *(User verification)*
- [ ] 5.6 Verify the 72h window is displayed correctly (3 days visible) *(User verification)*
- [ ] 5.7 Verify no regressions in Load tab or Strategy tab *(User verification)*

## 6. Documentation

- [x] 6.1 Updated Aurora page label from "Forecast Horizon (48h)" to "Forecast Horizon (3 Days)"

---
**Note**: Archive and sync tasks (4.1-4.3) removed - to be run by user when ready
