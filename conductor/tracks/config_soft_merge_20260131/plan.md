# Implementation Plan - DX14: Config Soft Merge Improvement

This plan follows the project workflow: 80% test coverage and task-based commits.

## Phase 1: Analysis & Design
- [ ] Task: Analyze current soft merge implementation
    - [ ] Locate merge logic (check `backend/config_migration.py` or `inputs.py`)
    - [ ] Identify current limitations with `ruamel.yaml` usage
- [ ] Task: Design structure-aware merge algorithm
    - [ ] Define recursive merge logic that respects key ordering
    - [ ] Create test scenarios (nested keys, multi-line comments)
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Analysis & Design' (Protocol in workflow.md)

## Phase 2: Implementation
- [ ] Task: Implementation - Core Merge Logic
    - [ ] Write unit tests for the new merge function in `tests/test_config_merge.py`
    - [ ] Implement `structure_aware_merge` in `backend/config_migration.py` (or appropriate module)
    - [ ] Verify tests pass with 80%+ coverage
- [ ] Task: Integration - Config Loading
    - [ ] Update `backend/main.py` or wherever config is initialized to use the new merge logic
    - [ ] Add integration test with mock `config.yaml` and `config.default.yaml`
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Implementation' (Protocol in workflow.md)

## Phase 3: Testing & Documentation
- [ ] Task: Regression Testing
    - [ ] Verify existing production `config.yaml` files merge correctly without data loss
- [ ] Task: Documentation Update
    - [ ] Update `docs/DEVELOPER.md` or `docs/SETUP_GUIDE.md` if config behavior has changed for users
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Testing & Documentation' (Protocol in workflow.md)
