## MODIFIED Requirements

### Requirement: Battery config preflight reads correct field names
The battery config preflight check (`check_battery_config()`) SHALL read charge and discharge power limits from `battery.max_charge_w` and `battery.max_discharge_w` (stored in watts), converting to kW by dividing by 1000 before comparison.

The check SHALL NOT reference `battery.max_charge_power_kw` or `battery.max_discharge_power_kw` — these keys do not exist in the v2 config schema.

Checks: `capacity_kwh > 0`, `max_charge_w / 1000 > 0`, `max_discharge_w / 1000 > 0`, `min_soc_percent < max_soc_percent`.

#### Scenario: Valid battery config passes preflight
- **WHEN** `battery.capacity_kwh = 29`, `max_charge_w = 5000`, `max_discharge_w = 5000`, `min_soc_percent = 12`, `max_soc_percent = 100`
- **THEN** `check_battery_config()` raises no error

#### Scenario: Zero watts triggers invalid config error
- **WHEN** `battery.max_charge_w = 0`
- **THEN** `check_battery_config()` raises `CONFIG_INVALID`

#### Scenario: Missing watts field defaults to zero and triggers error
- **WHEN** `battery.max_charge_w` is absent from config
- **THEN** the field defaults to `0.0` and `check_battery_config()` raises `CONFIG_INVALID`
