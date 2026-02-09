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

## Verification Questions

1.  **Idle Behavior:**
    *   **Confirmed:** We will use **`Self-consumption mode (default)` + `number.battery_max_discharge_power` = 0** for Idle.
    *   *Behavior:* Allows PV to charge battery (passive), but prevents battery discharge. Home runs on PV only.

2.  **Export Limiting:**
    *   **Confirmed:** Darkstar can use `switch.export_power_limit` + `number.export_power_limit` for emergency zero-export scenarios.
    *   *Note:* When `switch.export_power_limit` is `on`, the inverter enforces the value set in `number.export_power_limit`.

3.  **Entity Strings:**
    *   Please confirm the exact option strings in Home Assistant dropdowns match the table above (e.g. "Stop (default)" vs "Stop").

4.  **Power Entity:**
    *   **Confirmed:** Only `number.battery_forced_charge_discharge_power` is used for Grid Charge/Export power levels.

## Integration Source Notes
Based on the provided `modbus_sungrow.yaml`:

```yaml
  ###################
  # template: switch
  ###################
  - switch:
      # this enables/disables the inverter state & EMS settings in the dashboard
      # hopefully this prevents accidentally setting values while browsing on the phone :)
      - name: Sungrow dashboard enable danger mode
        unique_id: uid_sungrow_dashboard_enable_danger_mode

  ###################
  # template: button
  ###################
  - button:
      - name: Start inverter
        unique_id: uid_start_inverter
        variables:
          sg_start: 0xCF
        press:
          - action: modbus.write_register
            data:
              hub: *sg_hub_name
              slave: !secret sungrow_modbus_device_address
              address: *sg_reg_running_state
              value: "{{ sg_start }}"

      - name: Stop inverter
        unique_id: uid_stop_inverter
        variables:
          sg_stop: 0xCE
        press:
          - action: modbus.write_register
            data:
              hub: *sg_hub_name
              slave: !secret sungrow_modbus_device_address
              address: *sg_reg_running_state
              value: "{{ sg_stop }}"

  ###################
  # template: select
  ###################
  - select:
      - name: EMS mode
        unique_id: uid_ems_mode
        variables:
          # map: option name to raw value
          map:
            "Self-consumption mode (default)": 0
            "Forced mode": 2 # datasheet now calls it "compulsory mode"
            "External EMS": 3
            "VPP": 4
            # rarely used and commented for simplicity
            # "Microgid" :8
          fallback: "Self-consumption mode (default)"
        options: "{{ map.keys() | list | tojson }}" # get option names from map keys
        availability: "{{ states('sensor.ems_mode_selection_raw') | is_number }}"
        # modbus --> UI (raw value --> option)
        state: >-
          {# workaround for limited jinja python skills to reverse-search the map #}
          {# create a mutable namespace with default fallback #}
          {% set ns = namespace(result=fallback) %}
          {% set regVal = states('sensor.ems_mode_selection_raw') | int %}
          {# search in map inverted #}
          {% for key, value in map.items() %}
            {% if value == regVal %}
              {% set ns.result = key %}
            {% endif %}
          {% endfor %}
          {# save as result and output variable#}
          {% set result = ns.result %}
          {{ result }}
        # UI --> modbus
        select_option:
          - action: modbus.write_register
            data_template:
              hub: *sg_hub_name
              slave: !secret sungrow_modbus_device_address
              address: *sg_reg_ems_mode_selection
              value: "{{ map.get(option, map.get('Self-consumption mode (default)', 0)) | int }}"

      - name: Battery forced charge discharge
        unique_id: uid_battery_forced_charge_discharge
        variables:
          # map: option name to raw value
          map:
            "Stop (default)": 0xCC
            "Forced charge": 0xAA
            "Forced discharge": 0xBB
          fallback: "Stop (default)"
        options: "{{ map.keys() | list | tojson }}" # get option names from map keys
        availability: "{{ states('sensor.battery_forced_charge_discharge_cmd_raw') | is_number }}"
        # modbus --> UI (raw value --> option)
        state: >-
          {# workaround for limited jinja python skills to reverse-search the map #}
          {# create a mutable namespace with default fallback #}
          {% set ns = namespace(result=fallback) %}
          {% set regVal = states('sensor.battery_forced_charge_discharge_cmd_raw') | int %}
          {# search in map inverted #}
          {% for key, value in map.items() %}
            {% if value == regVal %}
              {% set ns.result = key %}
            {% endif %}
          {% endfor %}
          {# save as result and output variable#}
          {% set result = ns.result %}
          {{ result }}
        # UI --> modbus
        select_option:
          - action: modbus.write_register
            data_template:
              hub: *sg_hub_name
              slave: !secret sungrow_modbus_device_address
              address: *sg_reg_forced_charge_discharge_cmd_raw
              value: "{{ map.get(option, map.get('Stop (default)', 0)) }}"

      - name: Load adjustment mode
        unique_id: uid_load_adjustment_mode
        variables:
          # map: option name to raw value
          map:
            "Timing": 0
            "ON/OFF": 1
            "Power optimization": 2
            "Disabled": 3
          fallback: "Disabled"
        options: "{{ map.keys() | list | tojson }}" # get option names from map keys
        availability: "{{ states('sensor.load_adjustment_mode_selection_raw') | is_number }}"
        # modbus --> UI (raw value --> option)
        state: >-
          {# workaround for limited jinja python skills to reverse-search the map #}
          {# create a mutable namespace with default fallback #}
          {% set ns = namespace(result=fallback) %}
          {% set regVal = states('sensor.load_adjustment_mode_selection_raw') | int %}
          {# search in map inverted #}
          {% for key, value in map.items() %}
            {% if value == regVal %}
              {% set ns.result = key %}
            {% endif %}
          {% endfor %}
          {# save as result and output variable#}
          {% set result = ns.result %}
          {{ result }}
        # UI --> modbus
        select_option:
          - action: modbus.write_register
            data_template:
              hub: *sg_hub_name
              slave: !secret sungrow_modbus_device_address
              address: *sg_reg_load_adjustment_mode_selection
              value: "{{ map.get(option, map.get('Disabled', 3)) }}"

automation:
  - id: "automation_sungrow_enable_danger_mode_auto_reset"
    alias: "sungrow dashboard enable danger mode auto reset"
    description: "Auto resets the dashboard danger mode after some seconds"
    triggers:
      - platform: state
        entity_id:
          - switch.sungrow_dashboard_enable_danger_mode
    conditions: []
    # if the switch is enabled, disable it automatically after 60 seconds
    action:
      - choose:
          - conditions:
              - condition: state
                entity_id: switch.sungrow_dashboard_enable_danger_mode
                state: "on"
            sequence:
              - delay: "00:01:00" # delay 60 seconds
              - service: switch.turn_off
                target:
                  entity_id: switch.sungrow_dashboard_enable_danger_mode
    mode: restart # use restart to avoid warnings, when GUI is updated too often and the delay causes this automation to not finish before the next call

  - id: "automation_sungrow_max_export_scene_sets_rated_limit"
    alias: "sungrow max export scene sets rated limit"
    description: "When 'Sungrow Set Max Export' scene is activated, set export limit to inverter rated output"
    triggers:
      - platform: event
        event_type: call_service
        event_data:
          domain: scene
          service: turn_on
          service_data:
            entity_id: scene.sungrow_set_max_export_power
    conditions: []
    action:
      - service: number.set_value
        target:
          entity_id: number.export_power_limit
        data:
          value: "{{ states('sensor.inverter_rated_output') | float(0) }}"
    mode: single

scene:
  - name: Sungrow Self-Consumption Mode
    entities:
      select.ems_mode: "Self-consumption mode (default)"
      select.battery_forced_charge_discharge: "Stop (default)"

  - name: Sungrow Set Zero Export Power
    entities:
      switch.export_power_limit: "on"
      number.export_power_limit: "0"

  - name: Sungrow Set Max Export Power
    entities:
      # cannot use sensor.inverter_rated_output, because scripts don't render templates :/
      # for this, the automation "automation_sungrow_max_export_scene_sets_rated_limit" is used
      # number.export_power_limit: "5000"
      switch.export_power_limit: "off"

  - name: Sungrow Set Battery Bypass Mode
    entities:
      select.ems_mode: "Forced mode"
      select.battery_forced_charge_discharge: "Stop (default)"

  - name: Sungrow Set Battery Forced Discharge
    entities:
      select.ems_mode: "Forced mode"
      select.battery_forced_charge_discharge: "Forced discharge"

  - name: Sungrow Set Battery Forced Charge
    entities:
      select.ems_mode: "Forced mode"
      select.battery_forced_charge_discharge: "Forced charge"
      # BUG: 2026-01-10. Deactivated for now, see issue #643
      # https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/643
      # switch.forced_startup_under_low_soc_standby: "on" # in case inverter is in standby due to low soc

  - name: Sungrow Set Self-Consumption Limited Discharge
    entities:
      select.ems_mode: "Self-consumption mode (default)"
      select.battery_forced_charge_discharge: "Stop (default)"
      number.battery_max_discharge_power: "10" # set to minimum to disable discharging
```
