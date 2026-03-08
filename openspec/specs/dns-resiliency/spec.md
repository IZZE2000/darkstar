## Purpose

Ensure the Darkstar system remains responsive and avoids container restart loops caused by blocking I/O operations, particularly during DNS failures or network outages.

## Requirements

### Requirement: Non-Blocking Event Loop
The system MUST NOT execute long-running CPU-bound or I/O-bound synchronous operations on the main asyncio event loop, specifically the Kepler MILP solver execution.

#### Scenario: Kepler Solver Execution
- **WHEN** the planner pipeline runs `KeplerSolver.solve`
- **THEN** it executes in a background thread using `asyncio.to_thread`
- **THEN** the main event loop remains responsive to health checks and WebSocket pings

### Requirement: Concurrent Health Checks
The system SHALL verify Home Assistant entity states concurrently to minimize the overall health check duration, especially during network outages.

#### Scenario: Health Check Execution
- **WHEN** the `check_entities` method is invoked
- **THEN** it polls all required Home Assistant entities simultaneously using `asyncio.gather`
- **THEN** the total execution time is bounded by the longest single request timeout

### Requirement: Bounded Health Check Duration
The system MUST guarantee that the `/api/health` endpoint returns a response (either healthy or unhealthy) before the external Docker health check timeout kills the container.

#### Scenario: Health Check Timeout
- **WHEN** the `check_all` method is invoked
- **THEN** it is wrapped in an `asyncio.wait_for` with a timeout of 15 seconds
- **THEN** if the timeout is exceeded, the system immediately returns an unhealthy status

### Requirement: Fail-Fast Nordpool Fetching
The system SHALL limit the time spent attempting to fetch Nordpool prices to prevent thread starvation and planner stalling during prolonged DNS or network failures.

#### Scenario: DNS Failure During Nordpool Fetch
- **WHEN** the `prices_client.fetch` method is called and DNS resolution fails
- **THEN** the request times out after exactly 10 seconds
- **THEN** the system catches the `TimeoutError` and gracefully falls back to backup prices (or empty data) without hanging the thread
