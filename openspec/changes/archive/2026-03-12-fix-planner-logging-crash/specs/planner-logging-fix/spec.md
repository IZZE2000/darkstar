## ADDED Requirements

### Requirement: Planner Handles Formatting Safely
The planner logging logic SHALL correctly escape standard percent-formatting characters.

#### Scenario: Logging EV SoC fallback
- **WHEN** EV SoC sensor returns no data
- **THEN** the system logs a warning with the literal "0%" without crashing

### Requirement: Meaningful Planner Error Notifications
The planner error handler SHALL emit a string containing the error type for generic exceptions.

#### Scenario: Exception Caught in Planner
- **WHEN** a `ValueError` is raised during planner execution
- **THEN** the WebSocket notification includes "ValueError: incomplete format" instead of just "incomplete format"
