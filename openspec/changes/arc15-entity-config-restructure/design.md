# ARC15 Phase 1: Design & Migration Strategy

## Configuration Schema Design

### New Structure Overview

```yaml
# Root-level entity categories (alphabetical order)
ev_chargers: []       # Array of EV charger entities
heat_pumps: []        # Future: Array of heat pump entities
pool_heaters: []      # Future: Array of pool heater entities
water_heaters: []     # Array of water heater entities

# Deprecated (removed after migration period)
# deferrable_loads: []  # REMOVED - replaced by entity arrays
```

### Water Heater Schema

```yaml
water_heaters:
  - id: string                    # Required. Unique identifier (slug format)
    name: string                  # Required. Display name
    enabled: boolean              # Required. Master toggle for this heater
    power_kw: number              # Required. Rated power in kW
    min_kwh_per_day: number       # Required. Minimum daily energy requirement
    max_hours_between_heating: number    # Optional. Max hours without heating
    water_min_spacing_hours: number      # Optional. Min gap between cycles
    sensor: string                # Required. Home Assistant sensor entity_id
    type: string                  # Required. Load type: "binary" | "modulating"
    nominal_power_kw: number      # Required. Nominal power for calculations
```

### EV Charger Schema

```yaml
ev_chargers:
  - id: string                    # Required. Unique identifier (slug format)
    name: string                  # Required. Display name
    enabled: boolean              # Required. Master toggle for this charger
    max_power_kw: number          # Required. Max charging power in kW
    battery_capacity_kwh: number  # Required. Battery capacity in kWh
    min_soc_percent: number       # Optional. Minimum SoC (default: 20)
    target_soc_percent: number    # Optional. Target SoC (default: 80)
    sensor: string                # Required. Home Assistant sensor entity_id
    type: string                  # Required. Load type: "variable" | "constant"
    nominal_power_kw: number      # Required. Nominal power for calculations
```

## Migration Strategy

### Detection Logic

Migration needed when:
1. Config has `deferrable_loads` key (old format indicator)
2. OR config lacks `water_heaters` and `ev_chargers` keys
3. OR explicit `config_version < 2`

### Migration Steps

1. **Extract from old format:**
   - Read `system.has_water_heater` → Check if any water heaters exist
   - Read `input_sensors.water_power` → Get water heater sensor
   - Read `deferrable_loads[]` → Get load characteristics

2. **Build new format:**
   - Create `water_heaters[]` array with single item (existing behavior)
   - Create `ev_chargers[]` array if EV data exists
   - Map old sensor keys to new embedded `sensor` fields

3. **Remove old keys:**
   - Delete `deferrable_loads` array
   - Keep `system.has_*` for global toggles (derived from array items)
   - Keep `input_sensors` for non-deferrable sensors

4. **Update version:**
   - Set `config_version: 2`

### Backward Compatibility

During transition period (1-2 releases):
- Read functions support BOTH old and new formats
- New code uses helper functions to abstract format differences
- Migration script runs automatically on startup if old format detected

### Migration Script Location

```
backend/config/migrate_arc15.py
```

Functions:
- `detect_old_format(config: dict) -> bool`
- `migrate_to_arc15(config: dict) -> dict`
- `migrate_water_heater(old_config: dict) -> list`
- `migrate_ev_charger(old_config: dict) -> list`

## Implementation Plan (Phase 1)

### Step 1: Schema Design ✓
Define exact YAML structure with all fields and defaults.

### Step 2: Migration Script
Create `backend/config/migrate_arc15.py` with:
- Old format detection
- Automatic migration logic
- Idempotent operations (safe to run multiple times)
- Comprehensive logging

### Step 3: Integration
- Add migration call to config loading pipeline
- Add `config_version` tracking
- Ensure backup before migration

### Step 4: Validation & Testing
- Test migration with various old configs
- Verify data integrity after migration
- Test idempotency
