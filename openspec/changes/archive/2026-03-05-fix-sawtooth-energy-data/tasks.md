## 1. Recorder State Store - Time-Proportional Scaling

- [x] 1.1 Add `sensor_timestamp` parameter to `RecorderStateStore.get_delta()` method signature with default `None`
- [x] 1.2 Store `sensor_timestamp` in state file entries when provided (ISO format string)
- [x] 1.3 Implement time-proportional scaling logic when both current and previous sensor timestamps are available
- [x] 1.4 Add scaling window bounds check (5-60 minutes) with fallback to raw delta
- [x] 1.5 Handle missing `sensor_timestamp` gracefully (backward compatibility with old state files)

## 2. Recorder - Sensor Timestamp Extraction

- [x] 2.1 Modify `get_cumulative_kwh()` helper to return tuple `(kwh_value, sensor_timestamp)` instead of just `kwh_value`
- [x] 2.2 Extract `last_updated` or `last_changed` from HA entity state for sensor timestamp
- [x] 2.3 Update `calculate_energy_from_cumulative()` to pass `sensor_timestamp` to `get_delta()`
- [x] 2.4 Update all call sites of `get_cumulative_kwh()` to handle new return type

## 3. Learning Engine - Interpolation Fix

- [x] 3.1 Replace `reindex(..., method="ffill")` with `reindex()` to union of slots and sensor timestamps
- [x] 3.2 Add linear interpolation using `interpolate(method="index")` on the combined series
- [x] 3.3 Add `ffill().bfill()` to handle edge cases after interpolation
- [x] 3.4 Reindex to exact slot boundaries with `reindex(slots)`

## 4. Testing

- [x] 4.1 Add unit tests for `get_delta()` scaling behavior with various time spans
- [x] 4.2 Add unit tests for `get_delta()` backward compatibility (missing sensor_timestamp)
- [x] 4.3 Add unit tests for `get_delta()` window bounds (5-60 min range)
- [x] 4.4 Add unit tests for interpolation in `etl_cumulative_to_slots()`

## 5. Verification

- [x] 5.1 Run `./scripts/lint.sh` and fix all issues
- [x] 5.2 Verify backward compatibility by testing with old-format state file
