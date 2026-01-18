# REV F14 Phase 1: Entity Categorization Matrix (CORRECTED)

**Investigation Complete** | 2026-01-15

---

## Summary

Traced all entities through:
- [actions.py](file:///home/s/sync/documents/projects/darkstar/executor/actions.py) — WRITE operations
- [engine.py](file:///home/s/sync/documents/projects/darkstar/executor/engine.py) — System state gathering & PV dump detection
- [inputs.py](file:///home/s/sync/documents/projects/darkstar/inputs.py) — Planner reads
- [recorder.py](file:///home/s/sync/documents/projects/darkstar/backend/recorder.py) — Historical data
- [ha_socket.py](file:///home/s/sync/documents/projects/darkstar/backend/ha_socket.py) — Live metrics
- [config.yaml](file:///home/s/sync/documents/projects/darkstar/config.yaml) — Documented purpose of each entity

---

## ✅ Entity Categories by Functional Purpose

### 🔴 REQUIRED INPUT SENSORS (Darkstar READS)

| Entity Key | Label | Direction | Used By | Purpose |
|:-----------|:------|:---------:|:--------|:--------|
| `input_sensors.battery_soc` | Battery SoC (%) | READ | Planner, Executor, System API | Core state — **planner fails if missing** ([inputs.py:702-705](file:///home/s/sync/documents/projects/darkstar/inputs.py#L702-L705)) |
| `input_sensors.pv_power` | PV Power (W/kW) | READ | Executor, Recorder, ha_socket, System API | PV dump detection ([engine.py:1084-1086](file:///home/s/sync/documents/projects/darkstar/executor/engine.py#L1084)), live metrics, historical recording |
| `input_sensors.load_power` | Load Power (W/kW) | READ | Executor, Recorder, ha_socket, System API | System state gathering ([engine.py:1089-1091](file:///home/s/sync/documents/projects/darkstar/executor/engine.py#L1089)), load baseline for Aurora |

### 🔴 REQUIRED CONTROL ENTITIES (Darkstar WRITES)

| Entity Key | Label | Direction | Used By | Purpose |
|:-----------|:------|:---------:|:--------|:--------|
| `executor.inverter.work_mode_entity` | Work Mode Selector | WRITE | Executor | Sets inverter mode (Battery First, Load First, Export First) ([actions.py:302](file:///home/s/sync/documents/projects/darkstar/executor/actions.py#L302)) |
| `executor.inverter.grid_charging_entity` | Grid Charging Switch | WRITE | Executor | Enables/disables grid→battery charging ([actions.py:358](file:///home/s/sync/documents/projects/darkstar/executor/actions.py#L358)) |
| `executor.inverter.max_charging_current_entity` | Max Charge Current | WRITE | Executor | Sets charge rate (A) for proper charge control ([actions.py:402](file:///home/s/sync/documents/projects/darkstar/executor/actions.py#L402)) |
| `executor.inverter.max_discharging_current_entity` | Max Discharge Current | WRITE | Executor | Sets discharge rate (A) for proper discharge control ([actions.py:438](file:///home/s/sync/documents/projects/darkstar/executor/actions.py#L438)) |
| `executor.inverter.grid_max_export_power_entity` | Max Grid Export (W) | WRITE | Executor | Limits grid export power ([actions.py:624](file:///home/s/sync/documents/projects/darkstar/executor/actions.py#L624)) |
| `executor.soc_target_entity` | Target SoC **Output** | WRITE | Executor | Publishes Darkstar's target SoC to HA ([actions.py:495](file:///home/s/sync/documents/projects/darkstar/executor/actions.py#L495)) |

> [!IMPORTANT]
> **Label Fix Required**: `"Target SoC Feedback"` → `"Target SoC Output"` — this is a WRITE (Darkstar publishes), not a READ.

---

### 🟢 OPTIONAL INPUT SENSORS (Darkstar READS)

#### Power Flow & Dashboard

| Entity Key | Label | Direction | Used By | Purpose |
|:-----------|:------|:---------:|:--------|:--------|
| `input_sensors.battery_power` | Battery Power (W/kW) | READ | Executor (live metrics), Recorder, ha_socket | Charge/discharge tracking for ChartCard history ([recorder.py:65](file:///home/s/sync/documents/projects/darkstar/backend/recorder.py#L65)) |
| `input_sensors.grid_power` | Grid Power (W/kW) | READ | ha_socket, System API | PowerFlow card display |
| `input_sensors.water_power` | Water Heater Power | READ | Executor (live metrics), Recorder, ha_socket | Water heating tracking ([recorder.py:66](file:///home/s/sync/documents/projects/darkstar/backend/recorder.py#L66)) |

#### Smart Home Integration

| Entity Key | Label | Direction | Used By | Purpose |
|:-----------|:------|:---------:|:--------|:--------|
| `input_sensors.vacation_mode` | Vacation Mode Toggle | READ | Planner context | Reduces water heating quota ([inputs.py:770](file:///home/s/sync/documents/projects/darkstar/inputs.py#L770)) |
| `input_sensors.alarm_state` | Alarm Control Panel | READ | Planner context | Enables emergency reserve boost ([inputs.py:771](file:///home/s/sync/documents/projects/darkstar/inputs.py#L771)) |

#### User Override Toggles (Darkstar READS from these)

| Entity Key | Label | Direction | Used By | Purpose |
|:-----------|:------|:---------:|:--------|:--------|
| `executor.automation_toggle_entity` | Automation Toggle | READ | Executor | When OFF, executor skips all actions ([engine.py:767](file:///home/s/sync/documents/projects/darkstar/executor/engine.py#L767)) |
| `executor.manual_override_entity` | Manual Override Toggle | READ | Executor | Triggers manual override mode ([engine.py:1126-1129](file:///home/s/sync/documents/projects/darkstar/executor/engine.py#L1126)) |

> [!NOTE]
> These two are currently in "Optional HA Entities" but are **READ** entities, not controls Darkstar writes. Suggest moving to Optional Input Sensors for clarity.

#### Water Heater Sensors

| Entity Key | Label | Direction | Used By | Purpose |
|:-----------|:------|:---------:|:--------|:--------|
| `input_sensors.water_heater_consumption` | Water Heater Daily Energy | READ | Planner | Tracks `water_heated_today_kwh` ([inputs.py:717-721](file:///home/s/sync/documents/projects/darkstar/inputs.py#L717)) |

#### Today's Energy Stats (Dashboard display only)

| Entity Key | Label | Direction | Used By | Purpose |
|:-----------|:------|:---------:|:--------|:--------|
| `input_sensors.today_battery_charge` | Today's Battery Charge (kWh) | READ | Dashboard | "Today's Stats" card |
| `input_sensors.today_pv_production` | Today's PV Production (kWh) | READ | Dashboard | "Today's Stats" card |
| `input_sensors.today_load_consumption` | Today's Load Consumption (kWh) | READ | Dashboard | "Today's Stats" card |
| `input_sensors.today_grid_import` | Today's Grid Import (kWh) | READ | Dashboard | "Today's Stats" card |
| `input_sensors.today_grid_export` | Today's Grid Export (kWh) | READ | Dashboard | "Today's Stats" card |
| `input_sensors.today_net_cost` | Today's Net Cost | READ | Dashboard | Daily cost tracking |

#### Lifetime Energy Totals (Dashboard display only)

| Entity Key | Label | Direction | Used By | Purpose |
|:-----------|:------|:---------:|:--------|:--------|
| `input_sensors.total_battery_charge` | Total Battery Charge (kWh) | READ | Dashboard | Lifetime stats |
| `input_sensors.total_battery_discharge` | Total Battery Discharge (kWh) | READ | Dashboard | Lifetime stats |
| `input_sensors.total_grid_export` | Total Grid Export (kWh) | READ | Dashboard | Lifetime stats |
| `input_sensors.total_grid_import` | Total Grid Import (kWh) | READ | Dashboard | Lifetime stats |
| `input_sensors.total_load_consumption` | Total Load Consumption (kWh) | READ | Dashboard | Lifetime stats |
| `input_sensors.total_pv_production` | Total PV Production (kWh) | READ | Dashboard | Lifetime stats |

---

### 🟢 OPTIONAL CONTROL ENTITIES (Darkstar WRITES)

#### Water Heater Controls (Required if `has_water_heater=true`)

| Entity Key | Label | Direction | Used By | Purpose |
|:-----------|:------|:---------:|:--------|:--------|
| `executor.water_heater.target_entity` | Water Heater Setpoint | WRITE | Executor | Sets water heater target temperature ([actions.py:558](file:///home/s/sync/documents/projects/darkstar/executor/actions.py#L558)) |

---

## Proposed UI Structure

```
┌─────────────────────────────────────────────────────────────┐
│  🔴 REQUIRED HA INPUT SENSORS                               │
│     • Battery SoC (%)          [CRITICAL - planner fails]   │
│     • PV Power (W/kW)          [executor, recorder]         │
│     • Load Power (W/kW)        [executor, recorder]         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🔴 REQUIRED HA CONTROL ENTITIES                            │
│     • Work Mode Selector       [inverter mode]              │
│     • Grid Charging Switch     [grid→battery]               │
│     • Max Charge Current       [charge rate control]        │
│     • Max Discharge Current    [discharge rate control]     │
│     • Max Grid Export (W)      [export limiting]            │
│     • Target SoC Output        [publishes target to HA]     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🟢 OPTIONAL HA INPUT SENSORS                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Power Flow & Dashboard                               │  │
│  │    • Battery Power, Grid Power, Water Heater Power    │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Smart Home Integration                               │  │
│  │    • Vacation Mode Toggle, Alarm Control Panel        │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  User Override Toggles                                │  │
│  │    • Automation Toggle (executor skip)                │  │
│  │    • Manual Override Toggle                           │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Water Heater Sensors                                 │  │
│  │    • Water Heater Daily Energy                        │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Today's Energy Stats                                 │  │
│  │    • Battery Charge, PV Production, Load, Grid I/O    │  │
│  │    • Today's Net Cost                                 │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Lifetime Energy Totals                               │  │
│  │    • Total Battery, Grid, PV, Load                    │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🟢 OPTIONAL HA CONTROL ENTITIES                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Water Heater Controls (required if has_water_heater) │  │
│  │    • Water Heater Setpoint                            │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Changes from Original types.ts

1. **Move to REQUIRED Input Sensors:**
   - `input_sensors.pv_power` — used by executor for PV dump, recorder for history
   - `input_sensors.load_power` — used by executor for system state, recorder for history

2. **Move to REQUIRED Control Entities:**
   - Already there: `work_mode_entity`, `grid_charging_entity`
   - Confirm REQUIRED: `max_charging_current_entity`, `max_discharging_current_entity`, `grid_max_export_power_entity`
   - Add as REQUIRED: `soc_target_entity` (per user confirmation)

3. **Rename label:**
   - `"Target SoC Feedback"` → `"Target SoC Output"` (it's a WRITE, not a sensor)

4. **Move to Optional Input Sensors:**
   - `automation_toggle_entity` — user can toggle in dashboard instead
   - `manual_override_entity` — user can toggle in dashboard instead

5. **Conditional Required:**
   - `water_heater.target_entity` — Required if `has_water_heater=true`
