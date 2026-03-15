## Context

Multiple components make sequential HTTP calls to Home Assistant to fetch sensor values:

- **executor/engine.py:_gather_system_state()**: 9 sequential calls every 60s (~900ms)
- **backend/recorder.py:record_observation_from_current_state()**: 6+ sequential power sensor reads every 15m (~600ms+)
- **backend/core/ha_client.py:get_initial_state()**: 4 sequential calls during planning (~400ms)

Note: `get_energy_range()` and `get_energy_today()` were converted to database queries during the services.py refactoring and no longer perform sensor reads.

The existing pattern in `backend/health.py` already demonstrates the approach: `asyncio.gather()` with `return_exceptions=True` for concurrent entity checks. We need to apply this same pattern to sensor reading.

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

Instead of inline `asyncio.gather()` calls, create `gather_sensor_reads()` in `backend/core/ha_client.py`.

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

**3. Place Helper in `backend/core/ha_client.py`**

The helper should live alongside existing sensor reading functions.

Rationale:
- `inputs.py` was split during the inputs refactoring; sensor reading functions now live in `backend/core/ha_client.py`
- `get_initial_state()`, `get_ha_sensor_float()`, and `get_ha_entity_state()` are already here
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

1. Create `gather_sensor_reads()` helper in `backend/core/ha_client.py`
2. Refactor `executor/engine.py:_gather_system_state()` to use helper
3. Refactor `backend/recorder.py:record_observation_from_current_state()` to batch power sensor reads
4. Refactor `backend/core/ha_client.py:get_initial_state()` to use helper
5. Add regression tests
6. Verify performance improvement in logs

Note: `get_energy_today()` and `get_energy_range()` were converted to database queries during the services/inputs refactoring and are no longer in scope.

Rollback: Revert single commit - no data migration needed.

## Open Questions

None - approach is clear and proven by existing `asyncio.gather()` usage in `backend/health.py`.
