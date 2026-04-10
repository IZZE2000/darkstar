## Why

The cumulative energy sensor delta approach for EV and water heater recording is fundamentally broken for sensors with long update intervals (20-60+ minutes). Two compounding bugs cause EV/water actual energy to silently disappear: (1) time-proportional scaling is neutralized because `sensor_timestamp` is overwritten even when the value hasn't changed, and (2) the resulting accumulated deltas exceed the spike detection threshold and get zeroed out. This was reported by beta tester Kristoffer with a 60-minute lifetime energy sensor. The power sensors already work correctly for real-time display — we should use them for recording too, via the HA History API which we already use for backfill.

## What Changes

- **New generic function** `get_energy_from_power_history(entity_id, start, end)` that fetches power sensor history from the HA History API and computes average power × time to produce energy in kWh
- **Replace EV energy recording**: Use HA History API power averaging instead of cumulative energy sensor deltas. Fallback to power snapshot × 0.25h if history API call fails
- **Replace water heater energy recording**: Same approach as EV
- **BREAKING**: Remove `energy_sensor` config field from `ev_chargers[]` and `water_heaters[]` arrays
- Remove cumulative energy sensor collection, delta calculation, and state tracking for EV and water heaters from the recorder
- Remove `energy_sensor` health check warnings for EV and water heaters
- Remove `energy_sensor` fields from frontend settings UI (EntityArrayEditor)
- Remove EV/water energy sensor handling from backfill engine
- Update config migration to handle removal of `energy_sensor` fields
- Update documentation (ARCHITECTURE.md section 5.5 diagram)
- Update or remove tests for cumulative EV/water energy recording; add tests for new history API approach
- **Note**: PV, load, and grid cumulative sensors are NOT changed in this phase. Phase 2 will migrate those separately after Phase 1 is validated.

## Capabilities

### New Capabilities
_(none — this modifies existing capabilities)_

### Modified Capabilities
- `energy-recording`: EV and water heater energy calculation changes from cumulative sensor deltas to HA History API power averaging. Snapshot fallback changes from "no cumulative sensor configured" to "history API call fails". Cumulative sensor requirements removed for EV/water. Load isolation logic updated to always apply (not conditional on cumulative sensor usage).
- `sensor-configuration`: Remove `energy_sensor` field from `ev_chargers[]` and `water_heaters[]` config arrays. Remove related health warnings.

## Impact

- **Config**: `config.default.yaml` — remove `energy_sensor` from water_heaters[] and ev_chargers[] items
- **Config migration**: Handle existing configs that have `energy_sensor` populated (silent removal)
- **Backend**: `recorder.py` — replace EV/water energy calculation sections; new history API helper function
- **Backend**: `backfill.py` — remove EV/water cumulative sensor handling
- **Backend**: `health.py` — remove energy_sensor missing warnings for EV/water
- **Backend**: `ha_client.py` — new `get_energy_from_power_history()` function (or in recorder.py)
- **Frontend**: `EntityArrayEditor.tsx` — remove energy_sensor field from WaterHeaterEntity and EVChargerEntity interfaces and UI
- **Tests**: `test_recorder_deltas.py` — replace EV/water cumulative tests with history API tests
- **Docs**: `ARCHITECTURE.md` section 5.5 — update diagram to show power history API instead of cumulative sensors for EV/water
- **State**: `recorder_state.json` — `ev_energy_*` and `water_energy_*` keys become orphaned (harmless, can be cleaned up)
