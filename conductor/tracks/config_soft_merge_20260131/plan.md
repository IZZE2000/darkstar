# Implementation Plan - DX14: Config Soft Merge Improvement

This plan follows the project workflow: 80% test coverage and task-based commits.

## Phase 1: Analysis & Design
- [x] Task: Analyze current soft merge implementation
    - [x] Locate merge logic (check `backend/config_migration.py` or `inputs.py`)
    - [x] Identify current limitations with `ruamel.yaml` usage
- [x] Task: Design structure-aware merge algorithm
    - [x] Define recursive merge logic that respects key ordering
    - [x] Create test scenarios (nested keys, multi-line comments)
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Analysis & Design' (Protocol in workflow.md)

## Phase 2: Implementation
- [x] Task: Implementation - Core Merge Logic
    - [x] Create unit tests in `tests/test_config_merge.py` covering:
        - [x] Template fill strategy (Default structure + User values)
        - [x] Comment preservation (Official defaults)
        - [x] Custom key preservation
    - [x] Implement `template_aware_merge` in `backend/config_migration.py`
    - [x] Ensure `backup_config` function exists and is used before write
    - [x] Verify tests pass
- [x] Task: Integration - Config Loading
    - [x] Update `migrate_config` to use the new logic
    - [x] Add integration test with mock `config.yaml` and `config.default.yaml`
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Implementation' (Protocol in workflow.md)

## Phase 3: Testing & Documentation
- [x] Task: Regression Testing
    - [x] Verify existing production `config.yaml` files merge correctly without data loss
- [x] Task: Documentation Update
    - [x] Update `docs/DEVELOPER.md` or `docs/SETUP_GUIDE.md` if config behavior has changed for users
- [x] Task: Conductor - User Manual Verification 'Phase 3: Testing & Documentation' (Protocol in workflow.md)
