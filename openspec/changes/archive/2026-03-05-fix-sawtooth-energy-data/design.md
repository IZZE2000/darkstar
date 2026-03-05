## Context

The Darkstar energy recorder stores 15-minute slot observations for ML forecasting. It uses cumulative meter sensors (total lifetime energy) and calculates deltas between readings to determine energy per slot.

**Current State**:
- Cumulative sensors update every 10 min (`:03, :13, :23, :33, :43, :53`)
- Recorder runs every 15 min (`:00, :15, :30, :45`)
- Deltas alternate between capturing ~10 min and ~20 min of production
- Result: sawtooth pattern in `slot_observations` table (HIGH/LOW/HIGH/LOW)

**Constraints**:
- Cannot change sensor update frequency (HA-controlled)
- User will not switch away from cumulative sensors (just migrated)
- Solution must work in live recorder flow (not just backfill)
- Must preserve total energy (no loss/gain across scaling)

## Goals / Non-Goals

**Goals:**
- Normalize all energy deltas to represent exactly 15 minutes
- Work for all cumulative sensors (PV, load, import, export)
- Maintain backward compatibility with existing state files
- Correct both live recording and backfill ETL

**Non-Goals:**
- Changing sensor update timing
- Modifying Home Assistant integration
- Requiring user action or configuration changes
- Correcting historical data automatically (optional manual backfill)

## Decisions

### 1. Time-Proportional Scaling vs. Interpolation

**Decision**: Use time-proportional scaling for live recording, linear interpolation for backfill.

**Rationale**:
- Live recording: We have exact sensor timestamps (`last_updated`), so we know the actual time span each delta covers. Scaling is mathematically correct.
- Backfill: We have irregular historical data points. Interpolation estimates values at exact slot boundaries.

**Alternatives considered**:
- Query HA for exact slot-boundary readings: Would require storing all historical data or querying on-demand, impractical for backfill.
- Resample at query time: Would require changing all analytical pipelines, high risk.
- Accept the artifact: Would degrade ML model accuracy indefinitely.

### 2. Storage of Sensor Timestamp in State File

**Decision**: Add optional `sensor_timestamp` field to `data/recorder_state.json`.

**Rationale**:
- Enables scaling on subsequent recordings
- Optional field maintains backward compatibility
- First recording after deploy uses raw delta, then scaling activates

**Format**:
```json
{
  "pv_total_kwh": {
    "value": 1234.5,
    "timestamp": "2026-03-05T11:15:05.123456",
    "sensor_timestamp": "2026-03-05T11:13:00.000000"
  }
}
```

### 3. Scaling Window Bounds

**Decision**: Only scale when actual time span is between 5-60 minutes.

**Rationale**:
- < 5 min: Likely sensor glitch or rapid updates, raw delta safer
- 5-60 min: Normal operational range, scaling appropriate
- > 60 min: Likely restart or long gap, raw delta safer (represents accumulated energy)

## Risks / Trade-offs

**Risk**: Sensor timestamp missing or unreliable
→ **Mitigation**: Fallback to raw delta if `sensor_timestamp` is None or parsing fails

**Risk**: Sensor timestamp drift (clock skew between HA and recorder)
→ **Mitigation**: Window bounds (5-60 min) prevent scaling on extreme cases

**Risk**: Total energy appears different in scaled vs raw view
→ **Mitigation**: Scaling conserves energy (same total, different distribution)

**Risk**: Backfill interpolation produces different values than live recording
→ **Mitigation**: Both methods normalize to 15 minutes; small differences acceptable

## Migration Plan

**Deployment** (zero-downtime):
1. Deploy code changes
2. First recording cycle: raw delta (no `sensor_timestamp` in state file yet)
3. Second recording cycle onwards: time-proportional scaling active

**Optional Historical Correction**:
1. Run backfill after deploy to correct historical data
2. Interpolation fix applies to all historical slots

**Rollback**:
1. Revert code changes
2. State file with `sensor_timestamp` is harmless (field ignored)
3. Data recorded during changed period has correct totals but wrong distribution
