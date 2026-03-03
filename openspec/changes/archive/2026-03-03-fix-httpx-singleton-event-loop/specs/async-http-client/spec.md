## ADDED Requirements

### Requirement: Event loop isolation for async HTTP clients

Async HTTP clients SHALL NOT be shared across different event loops to prevent event loop corruption.

#### Scenario: Cross-thread event loop safety
- **WHEN** an async HTTP client is created in one event loop (e.g., FastAPI main thread)
- **AND** the same client instance is used from a different event loop (e.g., executor background thread)
- **THEN** the client SHALL either be created fresh for each event loop
- **OR** use thread-safe mechanisms that prevent event loop binding issues

#### Scenario: Executor thread isolation
- **WHEN** the executor runs in a background thread with its own event loop
- **AND** the executor makes HTTP requests to Home Assistant
- **THEN** the HTTP client SHALL NOT share internal asyncio state with clients from other threads
- **AND** requests SHALL complete without "bound to a different event loop" errors

#### Scenario: FastAPI and executor coexistence
- **WHEN** both FastAPI API handlers and the executor make concurrent HTTP requests
- **THEN** each SHALL use independent HTTP client instances
- **AND** neither SHALL interfere with the other's event loop
- **AND** both SHALL receive correct responses from Home Assistant

### Requirement: Resource management for async HTTP clients

Async HTTP clients SHALL use context managers (`async with`) to ensure proper resource cleanup and prevent connection pool leaks.

#### Scenario: Proper resource cleanup on success
- **WHEN** an async HTTP request completes successfully
- **THEN** the client SHALL be properly closed via context manager (`async with`)
- **AND** all sockets and connection pool resources SHALL be released

#### Scenario: Proper resource cleanup on exception
- **WHEN** an async HTTP request raises an exception
- **THEN** the client SHALL still be properly closed via context manager
- **AND** no resource leaks SHALL occur even in error conditions

#### Scenario: No singleton pattern for clients
- **WHEN** async HTTP clients are created
- **THEN** they SHALL NOT use singleton pattern that prevents proper cleanup
- **AND** each request SHALL create a fresh client with guaranteed cleanup
