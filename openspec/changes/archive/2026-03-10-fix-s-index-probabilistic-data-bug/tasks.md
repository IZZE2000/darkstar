## 1. Fix Data Access Pattern

- [x] 1.1 Fix probabilistic data access in `_get_forecast_data_aurora()` **extended records loop only** (lines 610-625 — the loop over `extended_records`, NOT the `forecast_data` loop over `db_slots` above it)
  - Change `rec.get("pv_p10")` to `rec.get("probabilistic", {}).get("pv_p10")`
  - Change `rec.get("pv_p90")` to `rec.get("probabilistic", {}).get("pv_p90")`
  - Change `rec.get("load_p10")` to `rec.get("probabilistic", {}).get("load_p10")`
  - Change `rec.get("load_p90")` to `rec.get("probabilistic", {}).get("load_p90")`
  - **Do NOT change** the slot-level `db_slot.get("pv_p10")` lines in the `forecast_data` loop (lines ~525-528) — those read from `build_db_forecast_for_slots()` which already returns a flat structure and work correctly

## 2. Fix Return Value Structure

- [x] 2.1 Add `daily_probabilistic` key to return dictionary (lines 627-631)
  - Include `pv_p10`, `pv_p90`, `load_p10`, `load_p90` dictionaries
  - Ensure structure matches what pipeline.py expects

## 3. Verification

- [x] 3.1 Run planner and verify probabilistic S-Index no longer fails with "insufficient_data_or_zero_load"
- [x] 3.2 Verify logs show successful probabilistic mode calculation with actual factor values
- [x] 3.3 Run lint and tests to ensure no regressions
