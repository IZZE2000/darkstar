# Fronius Logic & Verification

**Objective:** Validate entity mappings and behavior for the Fronius Gen24 Modbus integration (callifo/fronius_modbus).

## New Entities (BYD / Gen24)
*   `select.byd_battery_box_premium_hv_storage_control_mode` (Storage Control Mode selector)
*   `number.byd_battery_box_premium_hv_grid_charge_power` (Grid Charge Power / Limit)
*   `number.byd_battery_box_premium_hv_discharge_limit` (Discharge Limit Indicator)
*   `number.byd_battery_box_premium_hv_minimum_reserve` (Minimum Reserve/SoC Target)
*   `number.fronius_symo_gen24_10_0_export_limit_rate` (Export Limit Rate in Watts)
*   `switch.fronius_symo_gen24_10_0_export_limit_enable` (Export Limit Enable)

## Logic Mapping

| Darkstar Action | Storage Mode (`select...storage_control_mode`) | Grid Charge Power | Discharge Limit | Minimum Reserve | Export Limit Rate |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Self-Consumption** (Default) | `Auto` | 0 | Max | User Config | - |
| **Grid Charge** (Force Charge) | `Charge from Grid` | `number...grid_charge_power` | Max | User Config | - |
| **Grid Export** (Force Discharge) | `Discharge to Grid` | 0 | Max | User Config | - |
| **Idle / Hold** (PV OK, no discharge) | `Block discharging` | 0 | 0 | User Config | - |
| **Zero Export** (Emergency stop) | `Auto` | 0 | Max | User Config | `0` |

## Verification Questions

1.  **Export Limiting:**
    *   **Confirmed:** Darkstar can use `switch.fronius_gen24_export_limit_enable` + `number.fronius_gen24_export_limit_rate` for emergency zero-export scenarios.
    *   *Note:* When `switch.fronius_gen24_export_limit_enable` is `on`, the inverter enforces the value set in `number.fronius_gen24_export_limit_rate`.

2.  **Power Control Granularity:**
    *   The integration documentation states grid charge power must be in multiples of 10W.
    *   *Question:* Does Darkstar need to round to 10W increments, or does the integration handle this?
    *   **Confirmed:** Darkstar have to round to 10W increments.

3.  **Auto Mode Behavior:**
    *   **Proposed:** Darkstar will use `Auto` mode as the default/self-consumption state.
    *   *Question:* Is this correct, or should we use a different mode for normal operation?
    *   **Confirmed:** We will use **`Auto` mode** as the default/self-consumption state.

## Integration Source Notes

Based on the provided documentation from callifo/fronius_modbus:

### Storage Control Modes

| Mode | Description |
| :--- | :--- |
| `Auto` | The storage will allow charging and discharging up to the minimum reserve. |
| `PV Charge Limit` | The storage can be charged with PV power at a limited rate. |
| `Discharge Limit` | The storage can be charged with PV power and discharged at a limited rate. |
| `PV Charge and Discharge Limit` | Allows setting both PV charge and discharge limits. |
| `Charge from Grid` | The storage will be charged from the grid using 'Grid Charge Power'. |
| `Discharge to Grid` | The storage will discharge to the grid using 'Grid Discharge Power'. |
| `Block discharging` | The storage can only be charged with PV power. |
| `Block charging` | The storage can only be discharged and won't be charged with PV power. |

### Controls Used by Modes

| Mode | Charge Limit | Discharge Limit | Grid Charge Power | Grid Discharge Power | Minimum Reserve |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Auto | Ignored (100%) | Ignored (100%) | Ignored (0%) | Ignored (0%) | Used |
| PV Charge Limit | Used | Ignored (100%) | Ignored (0%) | Ignored (0%) | Used |
| Discharge Limit | Ignored (100%) | Used | Ignored (0%) | Ignored (0%) | Used |
| PV Charge and Discharge Limit | Used | Used | Ignored (0%) | Ignored (0%) | Used |
| Charge from Grid | Ignored | Ignored | Used | Ignored (0%) | Used |
| Discharge to Grid | Ignored | Ignored | Ignored (0%) | Used | Used |
| Block discharging | Used | Ignored (0%) | Ignored (0%) | Ignored (0%) | Used |
| Block charging | Ignored (0%) | Used | Ignored (0%) | Ignored (0%) | Used |

### Important Notes from Integration

1. **Grid Charging Efficiency:** Grid charging efficiency is approximately 50-60% at low power levels (< 1000W). It improves at higher power levels.

2. **Power Rounding:** Grid Charge Power must be set in multiples of 10W. If not rounded to 10, it may cause odd behavior (e.g., charging at 500W instead of requested value).

3. **Power Reset:** After changing modes, power values are automatically set to 0. You must set the power value AFTER selecting the mode.

4. **Firmware:** Update GEN24 inverter firmware to 1.34.6-1 or higher otherwise battery charging might be limited.

5. **Scheduled Charging:** Turn off scheduled (dis)charging in the Fronius Web UI to avoid unexpected behavior.

6. **Mode Ordering:** Always change the mode FIRST, then set controls active in that mode.
