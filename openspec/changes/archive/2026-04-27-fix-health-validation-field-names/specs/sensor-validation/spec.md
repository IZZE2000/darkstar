## ADDED Requirements

### Requirement: Solar health check reads array list
When `system.has_solar` is true, the health checker SHALL read `system.solar_arrays` (a list) and consider solar configured if any entry has `kwp > 0`. It SHALL NOT read `system.solar_array` (singular legacy key).

#### Scenario: Multi-array config passes health check
- **WHEN** `system.has_solar = true` and `system.solar_arrays` contains two entries each with `kwp > 0`
- **THEN** no "Solar enabled but panel size not configured" warning is emitted

#### Scenario: Empty arrays list triggers warning
- **WHEN** `system.has_solar = true` and `system.solar_arrays` is empty or absent
- **THEN** the warning "Solar enabled but panel size not configured" is emitted

#### Scenario: Legacy singular key is ignored
- **WHEN** `system.solar_array.kwp = 10.0` exists but `system.solar_arrays` is absent
- **THEN** the warning is still emitted (legacy key is not read)

### Requirement: Water heater health check reads heater list
When `system.has_water_heater` is true, the health checker SHALL read `water_heaters` (a list) and consider water heating configured if any enabled entry has `power_kw > 0`. It SHALL NOT read `water_heating.power_kw` (flat legacy field).

#### Scenario: Per-heater config passes health check
- **WHEN** `system.has_water_heater = true` and `water_heaters` contains an entry with `enabled = true` and `power_kw = 1`
- **THEN** no "Water heater enabled but power not configured" warning is emitted

#### Scenario: No heaters with power triggers warning
- **WHEN** `system.has_water_heater = true` and `water_heaters` is empty or all entries have `power_kw = 0`
- **THEN** the warning "Water heater enabled but power not configured" is emitted

#### Scenario: Legacy flat field is ignored
- **WHEN** `water_heating.power_kw = 3.0` exists but `water_heaters` list is empty
- **THEN** the warning is still emitted (legacy flat field is not read)
