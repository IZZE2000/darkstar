## Context

Currently, multiple components make sequential HTTP calls to Home Assistant to fetch sensor values:

- **executor/engine.py:_gather_system_state()**: 8-10 sequential calls every 60s (600-1000ms)
- **backend/recorder.py:record_observation_from_current_state()**: 10+ sequential calls every 15m (1000ms+)
- **inputs.py:get_initial_state()**: 4 sequential calls during planning (~400ms)
- **backend/api/routers/services.py:get_energy_range()**: 7 sequential calls (~700ms)

This pattern was already optimized in ARC5 for `/api/energy/today`, reducing latency from 600ms to 150ms using `asyncio.gather()`. We need to apply the same pattern consistently across all remaining locations.

The key insight: these sensor reads are **independent read operations** - no data dependencies between them, and HA handles concurrent connections well.

## Goals / Non-Goals

**Goals:**
- Reduce sensor read latency by ~75% (600-1000ms → 150ms)
- Create reusable abstraction for batch sensor operations
- Maintain graceful degradation when individual sensors fail
- Ensure consistent error handling across all call sites

**Non-Goals:**
- No changes to sensor entity IDs or configuration
- No changes to error handling semantics (just more efficient)
- No caching layer (pure parallelization)
- No changes to HA API itself

## Decisions

**1. Create Centralized Helper Function**

Instead of inline `asyncio.gather()` calls, create `gather_sensor_reads()` in a shared location (likely `inputs.py` or new `backend/utils/sensors.py`).

Rationale:
- Single source of truth for batch reading logic
- Consistent error handling pattern
- Easier to test and maintain
- Future-proof for adding metrics/circuit breakers

**2. Use `return_exceptions=True`**

Individual sensors can be unavailable. We must not fail the entire batch when one sensor errors.

Rationale:
- Matches current behavior (sequential reads with try/continue)
- Provides partial results - better than complete failure
- Allows caller to decide how to handle missing values

**3. Place Helper in `inputs.py`**

The helper should live alongside existing sensor reading functions.

Rationale:
- Most sensor reading code is already in `inputs.py`
- Avoids creating a new module for a single function
- Natural location for sensor-related utilities

**4. Keep Existing Function Signatures**

Refactor internals to use batching, but don't change public APIs.

Rationale:
- Zero breaking changes
- Minimal test updates needed
- Easy to verify no behavioral changes

## Risks / Trade-offs

**[Risk] Connection Pool Exhaustion**
- Currently: 1 connection at a time
- After: ~10 concurrent connections
- **Mitigation**: HA handles concurrent reads well. 10 connections is modest. If issues arise, can add connection limiting later.

**[Risk] Timing Inconsistency**
- Sequential: Reads spread over ~1s (slight time drift)
- Parallel: All reads at same moment
- **Mitigation**: Actually better - more consistent system state snapshot

**[Risk] Debugging Complexity**
- Harder to trace which specific sensor failed in batch
- **Mitigation**: Helper logs individual sensor failures with context

**[Trade-off] Code Complexity**
- Slightly more complex than simple sequential awaits
- **Acceptance**: Performance gain justifies small complexity increase

## Migration Plan

1. Create `gather_sensor_reads()` helper
2. Refactor `get_energy_today()` to use helper (already uses gather, just standardize)
3. Refactor `_gather_system_state()`
4. Refactor `record_observation_from_current_state()`
5. Refactor `get_initial_state()`
6. Refactor `get_energy_range()`
7. Add regression tests
8. Verify performance improvement in logs

Rollback: Revert single commit - no data migration needed.

## Open Questions

None - approach is clear and proven by existing implementation in ARC5.
