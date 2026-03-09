## MODIFIED Requirements

### Requirement: Guaranteed Thread Safety in Tests
The system SHALL ensure that no `AsyncEngine` instance is created in session-scoped fixtures. Per-test fixtures that create engines SHALL explicitly await `engine.dispose()` before the test event loop is closed.

#### Scenario: Database test cleanup
- **WHEN** a per-test fixture creates a database engine
- **THEN** it explicitly awaits `engine.dispose()` to ensure background threads are terminated before the test event loop closes.

### Requirement: Test Isolation from Production Config
The system SHALL NOT read from or write to `config.yaml` during any test session. Test config SHALL be injected via a monkey-patch of `inputs.load_yaml` in the session fixture.

#### Scenario: Test session does not corrupt config.yaml
- **WHEN** `uv run python -m pytest` is executed (or aborted mid-run)
- **THEN** `config.yaml` on disk is identical before and after the run.

#### Scenario: All callers of `inputs.load_yaml("config.yaml")` receive test config
- **WHEN** any module calls `inputs.load_yaml("config.yaml")` during a test session
- **THEN** it receives the in-memory test config dict without reading the filesystem.

## MODIFIED Requirements

### Requirement: Clean Test Suite Baseline
The full test suite SHALL execute with zero `DeprecationWarning` and zero `PytestUnhandledThreadExceptionWarning` messages. The lint script SHALL exit non-zero if any check (including frontend linting) fails.

#### Scenario: Full suite execution
- **WHEN** `uv run python -m pytest` is executed
- **THEN** the output contains the current passing count and zero warnings.

#### Scenario: lint.sh propagates frontend lint failures
- **WHEN** `./scripts/lint.sh` is executed and `pnpm lint` exits non-zero
- **THEN** `lint.sh` exits non-zero and does NOT print "✅ All checks passed!".
