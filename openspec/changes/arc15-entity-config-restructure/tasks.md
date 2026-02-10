# ARC15 Phase 2 Tasks

## Phase 2: Backend - Config Migration & Loading

- [ ] **TASK-1**: Update backend/api/routers/config.py for new schema
  - Add support for reading/writing water_heaters[] and ev_chargers[] arrays
  - Update unified validation in _validate_config_for_save()
  - Add validation for new entity-centric fields
  - Ensure backward compatibility during transition

- [ ] **TASK-2**: Update config validation helpers
  - Add validation for water_heater entry structure
  - Add validation for ev_charger entry structure
  - Validate unique IDs within each array
  - Validate sensor entity_id format

- [ ] **TASK-3**: Update config save API
  - Handle saving of nested entity arrays
  - Preserve user-defined order of entities
  - Handle deletion of entities from arrays
  - Maintain config_version: 2 on save

- [ ] **TASK-4**: Test config API endpoints
  - Test GET /api/config returns new schema correctly
  - Test POST /api/config saves water_heaters[] properly
  - Test POST /api/config saves ev_chargers[] properly
  - Test validation rejects invalid entries
  - Test backward compatibility with old format

- [ ] **TASK-5**: Update loading utilities
  - Ensure load_yaml() handles new structure
  - Add helper functions to access water_heaters/ev_chargers
  - Ensure deferrable_loads still works during transition

- [ ] **TASK-6**: Run integration tests
  - Test full config save/load cycle
  - Test migration followed by API save
  - Verify LoadDisaggregator can read new format
  - All existing tests still pass
