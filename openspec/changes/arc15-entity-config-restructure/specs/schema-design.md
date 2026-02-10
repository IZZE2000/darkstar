# Spec: Entity-Centric Schema Design

## Requirements

### REQ-SCHEMA-01: Root-Level Entity Arrays
The configuration MUST support root-level arrays for each entity category:
- `water_heaters`: Array of water heater configurations
- `ev_chargers`: Array of EV charger configurations
- Future expansion: `heat_pumps[]`, `pool_heaters[]`, etc.

### REQ-SCHEMA-02: Water Heater Structure
Each water heater entry MUST contain:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| id | string | Yes | - | Unique slug identifier |
| name | string | Yes | - | Display name |
| enabled | boolean | Yes | true | Individual toggle |
| power_kw | number | Yes | - | Rated power in kW |
| min_kwh_per_day | number | Yes | 5.0 | Min daily energy requirement |
| max_hours_between_heating | number | No | 8 | Max comfort gap |
| water_min_spacing_hours | number | No | 4 | Min gap between cycles |
| sensor | string | Yes | - | HA entity_id for power reading |
| type | string | Yes | "binary" | Load type: binary/modulating |
| nominal_power_kw | number | Yes | - | Nominal power for calcs |

### REQ-SCHEMA-03: EV Charger Structure
Each EV charger entry MUST contain:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| id | string | Yes | - | Unique slug identifier |
| name | string | Yes | - | Display name |
| enabled | boolean | Yes | true | Individual toggle |
| max_power_kw | number | Yes | - | Max charging power in kW |
| battery_capacity_kwh | number | Yes | - | Battery capacity in kWh |
| min_soc_percent | number | No | 20 | Minimum SoC constraint |
| target_soc_percent | number | No | 80 | Target SoC for charging |
| sensor | string | Yes | - | HA entity_id for power reading |
| type | string | Yes | "variable" | Load type: variable/constant |
| nominal_power_kw | number | Yes | - | Nominal power for calcs |

### REQ-SCHEMA-04: Config Version Tracking
Configuration MUST include `config_version: 2` to enable migration detection.

### REQ-SCHEMA-05: ID Uniqueness
All `id` fields within an array MUST be unique. Duplicates MUST trigger validation error.

### REQ-SCHEMA-06: Array Ordering
Arrays MUST preserve user-defined order (not alphabetical) to maintain UI presentation order.
