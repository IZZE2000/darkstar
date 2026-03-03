# Capability: Async HTTP Client

## Purpose

Provides non-blocking HTTP communication between the Darkstar executor and Home Assistant API, preventing system freezes when HA becomes unresponsive.

## Requirements

### Requirement: Async HTTP client for Home Assistant API

The async HTTP client SHALL provide non-blocking HTTP communication with Home Assistant API.

#### Scenario: Successful async request
- **WHEN** the executor requests an entity state from Home Assistant
- **THEN** the request SHALL be made asynchronously without blocking the event loop
- **AND** the response SHALL be returned within 5 seconds

#### Scenario: Timeout handling
- **WHEN** Home Assistant does not respond within 5 seconds
- **THEN** the client SHALL raise a timeout exception
- **AND** the executor SHALL continue processing the next tick

#### Scenario: Connection pooling
- **WHEN** multiple requests are made to the same Home Assistant instance
- **THEN** the client SHALL reuse connections from a connection pool
- **AND** connection overhead SHALL be minimized

### Requirement: Backward compatibility with configuration

The async HTTP client SHALL use the same configuration as the existing sync client.

#### Scenario: Existing configuration works
- **WHEN** the executor starts with existing `config.yaml`
- **THEN** the async client SHALL connect to the same Home Assistant URL
- **AND** use the same authentication token
- **AND** require no configuration changes

### Requirement: Proper exception handling

The async HTTP client SHALL handle exceptions gracefully and provide meaningful error messages.

#### Scenario: Network error handling
- **WHEN** a network error occurs during the request
- **THEN** the client SHALL raise an appropriate exception
- **AND** the error message SHALL include the entity ID and error type

#### Scenario: HTTP error handling
- **WHEN** Home Assistant returns a 4xx or 5xx status code
- **THEN** the client SHALL raise an exception with the status code
- **AND** the error details SHALL be available for logging

### Requirement: Timeout configuration

The async HTTP client SHALL support configurable timeouts with sensible defaults.

#### Scenario: Default timeout
- **WHEN** no timeout is configured
- **THEN** the client SHALL use a 5-second timeout for all requests

#### Scenario: Custom timeout
- **WHEN** a custom timeout is configured in config.yaml
- **THEN** the client SHALL use the configured timeout value
- **AND** timeout SHALL be applied to all HTTP operations

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
