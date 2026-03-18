## Context

The recorder currently uses cumulative energy sensor deltas to measure EV and water heater energy per 15-minute slot. This approach fails for sensors with update intervals longer than the recording interval (e.g., 60-minute lifetime energy sensors), causing accumulated deltas that either get incorrectly scaled or exceed spike detection thresholds.

Meanwhile, power sensors for EV chargers and water heaters already work correctly and update frequently (~1 minute). The HA History API (`/api/history/period/`) is already used in the codebase for backfill and load profile fetching. By fetching power sensor history over the slot window and computing average power, we get accurate energy measurements without any state tracking.

## Goals / Non-Goals

**Goals:**
- Replace EV and water heater energy recording with HA History API power averaging
- Single generic function usable for any power sensor (foundation for Phase 2)
- Remove `energy_sensor` config fields and all related code for EV/water
- Maintain load isolation (subtracting EV/water from total load)

**Non-Goals:**
- Migrating PV, load, or grid sensors (Phase 2)
- Changing the 15-minute recording interval
- Modifying the RecorderStateStore or time-proportional scaling (those stay for PV/load/grid)
- Changing real-time power display or disaggregation

## Decisions

### D1: Use HA History API for power-to-energy conversion

**Choice**: Fetch `/api/history/period/{start}?filter_entity_id={entity}&end_time={end}` for each power sensor and compute `mean(power_values) × slot_hours`.

**Alternatives considered**:
- Fix the delta timestamp bug only → still produces lumpy single-slot energy dumps for slow sensors
- WebSocket accumulation → more accurate but significantly more complex, fragile on reconnect
- Tighter recorder interval → doesn't fix the fundamental delta issue with slow sensors

**Rationale**: The History API is proven infrastructure (backfill already uses it), requires no state tracking, and handles any sensor update frequency. One HTTP call per sensor per 15-minute cycle is negligible overhead.

### D2: Generic function signature

```python
async def get_energy_from_power_history(
    entity_id: str,
    start: datetime,
    end: datetime,
) -> float | None:
    """Fetch power sensor history and compute energy via average power × time.

    Returns energy in kWh, or None if history unavailable.
    """
```

Place in `backend/core/ha_client.py` alongside existing HA API functions. This keeps all HA API interactions in one module and makes it available for Phase 2.

### D3: Fallback to power snapshot

**Choice**: If the History API call fails (timeout, HA unavailable, empty response), fall back to `current_power_kw × 0.25h` using the already-fetched point-in-time power reading.

**Rationale**: The power snapshot was the original approach and works adequately for constant-power loads. It's already fetched in the recorder's batch sensor reads, so no additional cost.

### D4: Load isolation always applies

Currently, load isolation (subtracting EV/water from total load) is conditional on `used_cumulative_load`. With this change, EV and water energy always come from history API (or snapshot fallback), so isolation should always apply when those values are non-zero.

### D5: Config migration for energy_sensor removal

**Choice**: Add a migration step that silently removes `energy_sensor` fields from `ev_chargers[]` and `water_heaters[]` arrays. No user action required — the field simply disappears on next config load.

### D6: Backfill — remove EV/water, don't replace

The backfill engine currently fetches water heater `energy_sensor` history for gap-filling (EV was never backfilled). Backfill only runs on reboot to fill gaps while the recorder was offline. The primary value of backfill is PV, load, and grid data — those are what ML models train on. EV/water backfill is low value and not worth the complexity of adding power-history-based backfill.

**Choice**: Remove the water heater `energy_sensor` lookup from backfill. Do not replace with power-based backfill for EV/water.

### D7: No retry in the generic function — rely on existing retry layers

The recorder service already wraps observation recording in `_record_with_retry()` (2 attempts, 3s delay). If HA is briefly unavailable, the history API call returns `None`, the snapshot fallback also fails, the whole recording fails, and the retry fires. On retry, both succeed if HA is back.

**Choice**: The generic function does not retry internally. It uses a reasonable timeout (10-15s), returns `None` on any failure, and logs at warning level. Retry is handled at the recorder service layer where it already exists.

## Risks / Trade-offs

**[Risk] HA History API may return empty data for very new sensors** → Fallback to power snapshot handles this gracefully. First slot after sensor creation might use snapshot, subsequent slots use history.

**[Risk] HA History API adds latency to recording cycle** → One HTTP call per sensor, HA is local (supervisor). Backfill already makes many such calls without issues. Expected <500ms per call.

**[Risk] Power sensor history may have gaps** → `mean()` of available data points is still representative. A sensor reporting every 30s gives ~30 data points per 15-min window — more than enough for a reliable average.

**[Trade-off] Less precise than cumulative energy meters for variable loads** → For EV chargers (constant power) and water heaters (on/off), power averaging is equally accurate. For truly variable loads in Phase 2, cumulative sensors may still be preferred — but that's a Phase 2 decision.

**[Trade-off] Breaking change for users who configured energy_sensor** → The field is removed silently via migration. Users don't need to do anything. The system works better without it.
