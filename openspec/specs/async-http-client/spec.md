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
