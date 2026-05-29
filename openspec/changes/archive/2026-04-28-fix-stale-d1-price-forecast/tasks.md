## 1. Filter stale slots in `get_d1_price_forecast_fallback`

- [x] 1.1 In `get_d1_price_forecast_fallback` (`ml/price_forecast.py`), after building `valid_forecasts`, add a filter that discards any entry whose `slot_start` date is on or before today's local date
- [x] 1.2 Add a `logger.debug` or `logger.info` line that logs how many slots were discarded as stale (date ≤ today), so the filter is observable in logs

## 2. Deduplicate by `start_time` in `_process_nordpool_data`

- [x] 2.1 In `_process_nordpool_data` (`backend/core/prices.py`), after sorting `result` by `start_time`, deduplicate by keeping the first occurrence of each `start_time` (real Nordpool entries are added before fallback entries, so first-wins = Nordpool wins)

## 3. Tests

- [x] 3.1 Add a unit test for `get_d1_price_forecast_fallback`: when DB contains `days_ahead=1` slots for today and yesterday, the function returns an empty list (all filtered as stale)
- [x] 3.2 Add a unit test for `get_d1_price_forecast_fallback`: when DB contains `days_ahead=1` slots for tomorrow, the function returns those slots unchanged
- [x] 3.3 Add a unit test for `_process_nordpool_data`: when `all_entries` contains duplicate `start_time` values (one Nordpool, one fallback), the returned list contains exactly one entry per timestamp and the Nordpool value is kept
