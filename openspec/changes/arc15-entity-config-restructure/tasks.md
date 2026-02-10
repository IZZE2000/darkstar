# ARC15 Phase 2 Tasks

## Phase 2: Backend - Config Migration & Loading

- [x] **TASK-1**: Update backend/api/routers/config.py for new schema
  - Added support for validating water_heaters[] and ev_chargers[] arrays ✓
  - Updated _validate_config_for_save() to handle new entity-centric fields ✓
  - Added duplicate ID detection for both arrays ✓
  - Added required field validation ✓
  - Added numeric value validation (positive numbers) ✓
  - Added SoC percentage range validation for EVs ✓
  - Maintained backward compatibility with legacy format ✓

- [x] **TASK-2**: Update config validation helpers
  - Validation for water_heater entry structure ✓
  - Validation for ev_charger entry structure ✓
  - Validate unique IDs within each array ✓
  - Validate sensor entity_id format ✓

- [x] **TASK-3**: Update config save API
  - Config save API handles nested entity arrays via deep_update ✓
  - Preserves user-defined order of entities ✓
  - Maintains config_version: 2 on save ✓
  - Deletion handled by frontend sending empty arrays ✓

- [x] **TASK-4**: Test config API endpoints
  - GET /api/config returns new schema correctly ✓
  - POST /api/config saves water_heaters[] properly ✓
  - POST /api/config saves ev_chargers[] properly ✓
  - Validation rejects invalid entries ✓
  - Backward compatibility with old format ✓

- [x] **TASK-5**: Update loading utilities
  - load_yaml() handles new structure ✓
  - deferrable_loads still works during transition ✓

- [x] **TASK-6**: Run integration tests
  - Created comprehensive test suite (12 tests) ✓
  - All tests passing ✓
  - Existing migration tests still passing ✓
  - Linting checks pass ✓
