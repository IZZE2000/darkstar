## Why

The S-Index probabilistic calculation consistently fails with "insufficient_data_or_zero_load" even though ML models are trained and producing probabilistic forecasts. This causes the system to fall back to less optimal `physical_deficit` mode instead of using the sophisticated sigma-scaling risk assessment that probabilistic mode provides.

## What Changes

- Fix `inputs.py` `_get_forecast_data_aurora()` function to correctly access nested probabilistic data from `get_forecast_slots()` API response
- Add missing `daily_probabilistic` key to the return value containing aggregated daily P10/P90 values for PV and Load
- The probabilistic S-Index will then have access to the uncertainty bounds it needs to calculate risk-adjusted safety margins

**Files modified:**
- `inputs.py` - `_get_forecast_data_aurora()` function (lines 610-631)

## Capabilities

### New Capabilities
- None (this is a bug fix)

### Modified Capabilities
- `s-index-probabilistic`: Fix data retrieval so probabilistic mode can actually use the uncertainty bounds from ML forecasts. The capability already exists but cannot function due to bugs in data access patterns.

## Impact

- **S-Index Calculation**: Will properly use probabilistic mode when configured, enabling sigma-scaling risk assessment
- **Planner**: More accurate safety margins based on actual forecast uncertainty
- **No API changes** - purely internal bug fix
- **No breaking changes** - the fallback to physical_deficit mode still works during the transition
