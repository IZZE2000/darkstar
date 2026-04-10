## ADDED Requirements

### Requirement: Batch sensor reading with parallel execution
The system SHALL provide a mechanism to read multiple Home Assistant sensor values in parallel using `asyncio.gather()` to minimize latency.

#### Scenario: Multiple independent sensors
- **WHEN** the system needs to read 5 or more independent sensor values from Home Assistant
- **THEN** the system SHALL execute all reads concurrently
- **AND** the total latency SHALL not exceed 200ms (vs 500-1000ms sequential)

#### Scenario: Mixed sensor availability
- **WHEN** reading 10 sensors in parallel and 2 return errors or "unavailable"
- **THEN** the system SHALL return values for the 8 successful reads
- **AND** the system SHALL log warnings for the 2 failed sensors with their entity IDs
- **AND** the calling code SHALL receive partial results without exception

### Requirement: Graceful error handling in batch operations
The system SHALL handle individual sensor read failures without failing the entire batch operation.

#### Scenario: Single sensor timeout
- **WHEN** batch reading 8 sensors and one sensor times out after 10 seconds
- **THEN** the other 7 sensors SHALL complete successfully
- **AND** the timed-out sensor SHALL return `None` in results
- **AND** the calling function SHALL continue execution normally

#### Scenario: All sensors unavailable
- **WHEN** batch reading sensors and ALL sensors return errors
- **THEN** the system SHALL return a dictionary with all values as `None`
- **AND** the system SHALL log a single summary warning (not 10 individual warnings)

### Requirement: Consistent API across all sensor reading locations
All locations that read multiple independent HA sensors SHALL use the centralized batch reading helper function.

#### Scenario: Executor state gathering
- **WHEN** the executor gathers system state (~9 sensors) in `executor/engine.py:_gather_system_state()`
- **THEN** it SHALL call the batch helper function
- **AND** latency SHALL be under 200ms

#### Scenario: Recorder power sensor reads
- **WHEN** the recorder reads power sensors (~6+) in `backend/recorder.py:record_observation_from_current_state()`
- **THEN** it SHALL call the batch helper function for the power sensor reads
- **AND** cumulative energy reads MAY remain separate (they have stateful logic)

#### Scenario: Initial state gathering
- **WHEN** planning gathers initial state (~4 sensors) in `backend/core/ha_client.py:get_initial_state()`
- **THEN** it SHALL call the batch helper function
- **AND** critical SoC failure SHALL still raise an error (safety invariant)

### Requirement: Context-aware logging
The batch reading function SHALL include context information in logs to aid debugging.

#### Scenario: Debugging sensor failures
- **WHEN** a sensor read fails in the executor context
- **THEN** the log SHALL include the context label "executor_state"
- **AND** the entity ID of the failed sensor
- **AND** the specific error message

#### Scenario: Debugging in recorder context
- **WHEN** a sensor read fails in the recorder context
- **THEN** the log SHALL include the context label "recorder_observation"
- **AND** distinguish between power sensors and cumulative sensors
