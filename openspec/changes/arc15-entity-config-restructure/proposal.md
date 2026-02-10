# ARC15: Entity-Centric Config Restructure

## Problem Statement

Current configuration duplicates the same information in 3 locations:
1. `system.has_water_heater` / `system.has_ev_charger` (toggles)
2. `input_sensors.water_power` / `input_sensors.ev_power` (sensors)
3. `deferrable_loads[]` array (for LoadDisaggregator)

When users enable water heating in the UI, load disaggregation fails silently because the `deferrable_loads` array is never auto-populated. This causes the ML model to train on "dirty" total load (including deferrable loads) instead of "clean" base load, resulting in inaccurate forecasts.

## Proposed Solution

Restructure configuration to entity-centric sections where each physical device has ONE config location containing all its settings, sensors, and load characteristics.

### Key Principles

1. **Single Source of Truth**: One config section per entity type
2. **Plural Arrays**: Support multiple instances (water_heaters[], ev_chargers[])
3. **Category-Based**: Room for future expansion (pool_heaters[], heat_pumps[])
4. **Automatic Migration**: Old config converts automatically on startup
5. **Backward Compatibility**: Support both formats during transition

## New Schema (Phase 1 Target)

```yaml
water_heaters:                     # Array for multiple water heaters
  - id: main_tank                  # Unique identifier
    name: "Main Water Heater"      # Display name
    enabled: true                  # Individual toggle
    power_kw: 3.0                  # Rated power
    min_kwh_per_day: 6.0           # Daily energy requirement
    max_hours_between_heating: 8   # Comfort constraint
    water_min_spacing_hours: 4     # Minimum gap between cycles
    sensor: sensor.vvb_power       # Power sensor
    type: binary                   # Load type
    nominal_power_kw: 3.0          # Nominal power

ev_chargers:                       # Array for multiple EVs
  - id: tesla_model_3              # Unique identifier
    name: "Tesla Model 3"          # Display name
    enabled: true                  # Individual toggle
    max_power_kw: 11.0             # Max charging power
    battery_capacity_kwh: 82.0     # Battery size
    min_soc_percent: 20.0          # Minimum charge
    target_soc_percent: 80.0       # Target charge
    sensor: sensor.tesla_power     # Power sensor
    type: variable                 # Load type
    nominal_power_kw: 11.0         # Nominal power
```

## Success Criteria

- [ ] New schema designed with multiple device support
- [ ] Migration path defined (old → new format)
- [ ] Migration script created and tested
- [ ] Phase 1 implementation complete and validated
