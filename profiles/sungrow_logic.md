# Sungrow Logic & Verification

**Objective:** Validate entity mappings and behavior for the new Sungrow integration (mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant).

## New Entities
*   `select.ems_mode`
*   `select.battery_forced_charge_discharge`
*   `number.battery_forced_charge_discharge_power`
*   `number.battery_max_discharge_power`
*   `switch.export_power_limit`
*   `number.export_power_limit`

## Logic Mapping

| Darkstar Action | EMS Mode (`select.ems_mode`) | Forced Cmd (`select.battery_forced_charge_discharge`) | Forced Power | Max Charge | Max Discharge | Export Limit Switch | Export Limit Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Self-Consumption** (Default) | `Self-consumption mode (default)` | `Stop (default)` | - | - | `number.battery_max_discharge_power` = 9000 | `off` | - |
| **Grid Charge** (Force Charge) | `Forced mode` | `Forced charge` | `number.battery_forced_charge_discharge_power` | `number.battery_max_charge_power` | `number.battery_max_discharge_power` = 9000 | `off` | - |
| **Grid Export** (Force Discharge) | `Forced mode` | `Forced discharge` | `number.battery_forced_charge_discharge_power` | - | `number.battery_max_discharge_power` = 9000 | `off` | - |
| **Idle / Hold** (PV charge OK, no discharge) | `Self-consumption mode (default)` | `Stop (default)` | - | - | `number.battery_max_discharge_power` = 10 | `off` | - |
| **Zero Export** (Emergency stop) | `Self-consumption mode (default)` | `Stop (default)` | - | - | `number.battery_max_discharge_power` = 9000 | `on` | `0` |

**Notes:**
- In forced modes, always set the corresponding `max_*_power` to ensure it doesn't cap the forced power
- Minimum power value is **10W** (inverter enforces this as lowest valid setting)
- Idle mode uses max_discharge=10W (minimum) instead of 0W to prevent discharge while allowing PV charging
- All other modes set max_discharge_power to 9000W (inverter max) to allow full discharge when needed
- Export is controlled via `export_power_limit` entity, not `max_discharge_power`

## Storage Control Modes

| Mode | Description |
| :--- | :--- |
| `Self-consumption mode (default)` | Battery charges from excess PV and discharges to meet home load demand. Forced charge/discharge commands are ignored. |
| `Forced mode` | Battery responds to forced_charge_discharge_cmd and forced_charge_discharge_power settings. Used for grid charge and grid export actions. |

## Controls Used by Modes

| Mode | Forced Charge/Discharge Cmd | Forced Power | Max Charge Power | Max Discharge Power | Export Limit Switch | Export Limit Value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Self-consumption mode (default) | Ignored (treated as Stop) | Ignored | Used | Used | Used | Used (if switch on) |
| Forced mode | Used | Used | Used | Used | Used | Used (if switch on) |

**Notes:**
- In Self-consumption mode, the forced_charge_discharge_cmd is ignored regardless of its current value
- Max Charge/Discharge Power always act as caps on battery power in both Self-consumption and Forced modes
- Export limit works independently of EMS mode - active in all modes when switch is on
- Forced Power must be set in multiples of 10W (inverter enforces minimum 10W)
