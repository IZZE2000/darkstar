# Inverter Profile System v2 — Implementation Blueprint

> **REV ARC17** | Schema Version 2 | Clean Break from v1
>
> This document is the **single source of truth** for implementing the v2 profile system.
> It is written to be comprehensive enough for any AI or developer to implement without ambiguity.

---

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [Profile YAML Schema v2](#profile-yaml-schema-v2)
3. [Entity Registry](#entity-registry)
4. [Mode Definitions](#mode-definitions)
5. [Dynamic Value Templates](#dynamic-value-templates)
6. [Behavior Section](#behavior-section)
7. [Python Dataclass Schema](#python-dataclass-schema)
8. [Executor Rewrite](#executor-rewrite)
9. [Controller Simplification](#controller-simplification)
10. [Settings UI Integration](#settings-ui-integration)
11. [Execution History / Logging](#execution-history--logging)
12. [Complete Profile Examples](#complete-profile-examples)
13. [Files to Modify / Create / Delete](#files-to-modify--create--delete)
14. [Test Requirements](#test-requirements)

---

## Design Philosophy

### Core Principle

> **The profile defines EVERYTHING that happens for a mode. The executor is a generic loop that reads the profile and applies it.**

### What This Eliminates

- **No more `_set_work_mode`, `_set_grid_charging`, `_set_charge_limit`, `_set_discharge_limit`, `_set_soc_target`, `_set_max_export_power`** — these all become just another entity write in the mode's action list.
- **No more `if self.profile` branching** — the profile is always required. No legacy fallback.
- **No more skip flags** (`skip_discharge_limit`, `skip_export_power`) — if an entity isn't in the mode's action list, it's not touched.
- **No more `_apply_composite_entities`** (ARC16) — every entity is explicit per mode. No disambiguation needed.
- **No more `forced_power` syncing** — just another action in the mode definition.
- **No more `_get_mode_def_for_value` iteration** — direct key lookup by `mode_intent`.

### The 4 Modes from the Planner

The planner and controller deal with exactly **4 mode intents**:

| Mode Intent | Triggered By | Meaning |
|-------------|-------------|---------|
| `charge` | `slot.charge_kw > 0` | Charge battery from AC grid |
| `export` | `slot.export_kw > 0` | Discharge battery to grid for arbitrage |
| `idle` | `SoC ≤ target`, no charge/export | Block discharge, preserve battery |
| `self_consumption` | Everything else | Normal PV→battery→house |

> [!IMPORTANT]
> `zero_export` and `force_discharge` are **REMOVED** as mode intents. They were inverter-specific concepts that belong inside the profile, not in the planner/controller contract.
> - Old `zero_export` → each profile defines its `self_consumption` mode with the correct HA value (e.g., Deye uses `"Zero Export To CT"`)
> - Old `force_discharge` → the override system uses `export` with max discharge value

---

## Profile YAML Schema v2

### Top-Level Structure

```yaml
# ============================================================
# Inverter Profile: [Brand Name]
# Schema Version: 2
# ============================================================

metadata:
  name: "brand_name"           # Lowercase identifier, matches filename
  version: "2.0.0"             # Profile version
  schema_version: 2            # MUST be 2 for v2 profiles
  description: "Human-readable description"
  supported_brands:            # List of brand names for UI display
    - "Brand A"
    - "Brand B"

entities:
  # ... entity registry (see below)

modes:
  # ... mode definitions (see below)

behavior:
  # ... executor behavior parameters (see below)
```

---

## Entity Registry

The entity registry defines **ALL Home Assistant entities** this inverter profile uses. Each entry provides:

- **`default_entity`** — The default HA entity ID (what most users will have)
- **`domain`** — The HA domain (`select`, `number`, `switch`, `input_number`) — tells the executor which HA service to call
- **`description`** — Human-readable text shown in the Settings UI
- **`required`** — Whether Darkstar CANNOT function without this entity
- **`category`** — Which Settings tab to display this entity under

### Valid Categories

These map directly to the existing Settings UI tabs:

| Category | Settings Tab | Used For |
|----------|-------------|----------|
| `system` | System | Inverter control entities (work_mode, SoC target) |
| `battery` | Battery | Battery-specific entities (charge/discharge power/current) |

> [!NOTE]
> Only `system` and `battery` are used. Grid export entities, water heater entities, and EV entities are handled by their own existing sections in the Settings UI and are NOT part of the inverter profile.

### Entity Registry Example

```yaml
entities:
  work_mode:
    default_entity: "select.inverter_work_mode"
    domain: "select"
    category: "system"
    description: "Inverter operating mode selector"
    required: true

  grid_charging_enable:
    default_entity: "switch.grid_charging"
    domain: "switch"
    category: "system"
    description: "Grid charging on/off switch"
    required: true

  soc_target:
    default_entity: "number.battery_soc_target"
    domain: "number"
    category: "battery"
    description: "Battery SoC target percentage"
    required: false

  max_charge_current:
    default_entity: "number.battery_max_charge_current"
    domain: "number"
    category: "battery"
    description: "Maximum battery charging current (Amps)"
    required: true

  max_discharge_current:
    default_entity: "number.battery_max_discharge_current"
    domain: "number"
    category: "battery"
    description: "Maximum battery discharge current (Amps)"
    required: true
```

### Entity Resolution Order

When the executor needs to resolve an entity key to an actual HA entity ID:

1. **User override** — Check `executor.inverter.custom_entities[key]` in config
2. **Standard config** — Check `executor.inverter[key]` (for standard entities like `work_mode`, `soc_target`)
3. **Profile default** — Use `entities[key].default_entity` from the profile

This allows users to override any entity without editing the profile.

---

## Mode Definitions

Each mode contains an **ordered list** of actions. Actions execute **top-to-bottom**. This is critical for inverters like Fronius that require mode changes before power writes.

### Mode Definition Structure

```yaml
modes:
  charge:
    description: "Force charge battery from AC grid"
    actions:
      - entity: "work_mode"            # References entity registry key
        value: "Forced mode"           # Static value to write
      - entity: "forced_charge_cmd"
        value: "Forced charge"
      - entity: "max_charge_power"
        value: "{{charge_value}}"      # Dynamic: resolved from ControllerDecision
      - entity: "max_discharge_power"
        value: "{{max_discharge}}"     # Dynamic: user's configured max
      - entity: "grid_charging_enable"
        value: true
```

### Action Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `entity` | string | ✅ | Key from the entity registry |
| `value` | string/number/boolean | ✅ | Value to write (static or dynamic template) |
| `settle_ms` | integer | ❌ | Milliseconds to wait AFTER this action completes |

### What Happens if an Entity is NOT in a Mode

**Nothing.** If `self_consumption` mode doesn't list `grid_charging_enable`, then the grid charging switch is **not touched** during that mode. This replaces all `skip_*` flags.

> [!IMPORTANT]
> Each mode's action list must be a **complete recipe**. If entering `self_consumption` mode should turn off grid charging, the mode must explicitly include `grid_charging_enable: false`. Do not rely on "resetting" from a previous mode.

---

## Dynamic Value Templates

Actions can use template strings that are resolved from `ControllerDecision` at runtime:

| Template | Source Field | Description |
|----------|-------------|-------------|
| `{{charge_value}}` | `decision.charge_value` | Planned charge current/power (A or W) |
| `{{discharge_value}}` | `decision.discharge_value` | Planned discharge current/power (A or W) |
| `{{soc_target}}` | `decision.soc_target` | Battery SoC target percentage |
| `{{export_power_w}}` | `decision.export_power_w` | Grid export power limit in Watts |
| `{{max_charge}}` | `decision.max_charge` | User's configured max charge (A or W from battery config) |
| `{{max_discharge}}` | `decision.max_discharge` | User's configured max discharge (A or W from battery config) |

### Resolution Rules

1. Templates are strings matching the regex `\{\{(\w+)\}\}`
2. The template name maps to a field on `ControllerDecision`
3. If the field value is `0` or `0.0`, it is written as `0` (not skipped)
4. If the template name doesn't exist on `ControllerDecision`, raise a `ProfileError` at profile load time (validation)

---

## Behavior Section

The behavior section defines executor-level parameters. These are NOT profile-specific modes but operational tuning:

```yaml
behavior:
  control_unit: "W"              # "A" (Amps) or "W" (Watts)
  min_charge_a: 1.0              # Minimum charge command (Amps mode)
  min_charge_w: 10.0             # Minimum charge command (Watts mode)
  round_step_a: 1.0              # Rounding step for charge/discharge (Amps)
  round_step_w: 100.0            # Rounding step for charge/discharge (Watts)
  grid_charge_round_step_w: null # Optional: different rounding for grid charge
  write_threshold_w: 100.0       # Min delta before writing a new value
  mode_settling_ms: 100          # Default delay after mode changes
```

---

## Python Dataclass Schema

### New Dataclasses (replace current `profiles.py`)

```python
@dataclass
class EntityDefinition:
    """A single entity in the profile's entity registry."""
    default_entity: str          # Default HA entity ID
    domain: str                  # "select", "number", "switch", "input_number"
    category: str                # "system" or "battery"
    description: str             # Human-readable description for UI
    required: bool = True        # Whether Darkstar requires this entity

@dataclass
class ModeAction:
    """A single action within a mode definition."""
    entity: str                  # Entity registry key
    value: str | int | float | bool  # Value to set (or template string)
    settle_ms: int | None = None     # Optional delay after this action

@dataclass
class ModeDefinition:
    """A complete mode definition with ordered actions."""
    description: str             # Human-readable mode description
    actions: list[ModeAction]    # Ordered list of actions

@dataclass
class ProfileBehavior:
    """Executor behavior parameters."""
    control_unit: str = "A"
    min_charge_a: float = 1.0
    min_charge_w: float = 10.0
    round_step_a: float = 1.0
    round_step_w: float = 100.0
    grid_charge_round_step_w: float | None = None
    write_threshold_w: float = 100.0
    mode_settling_ms: int = 100

@dataclass
class ProfileMetadata:
    """Profile metadata."""
    name: str
    version: str
    schema_version: int
    description: str = ""
    supported_brands: list[str] = field(default_factory=list)

@dataclass
class InverterProfile:
    """Complete v2 inverter profile."""
    metadata: ProfileMetadata
    entities: dict[str, EntityDefinition]        # entity_key -> definition
    modes: dict[str, ModeDefinition]             # mode_intent -> definition
    behavior: ProfileBehavior

    def get_mode(self, mode_intent: str) -> ModeDefinition:
        """Get mode definition by intent key. Raises ProfileError if not found."""
        if mode_intent not in self.modes:
            raise ProfileError(f"Mode '{mode_intent}' not defined in profile '{self.metadata.name}'")
        return self.modes[mode_intent]

    def get_entity(self, key: str) -> EntityDefinition:
        """Get entity definition by key. Raises ProfileError if not found."""
        if key not in self.entities:
            raise ProfileError(f"Entity '{key}' not defined in profile '{self.metadata.name}'")
        return self.entities[key]

    def get_required_entities(self) -> dict[str, EntityDefinition]:
        """Return all required entities."""
        return {k: v for k, v in self.entities.items() if v.required}

    def get_missing_entities(self, config: dict) -> list[str]:
        """Check config for missing required entities. Returns list of missing keys."""
        # ... resolution logic using entity resolution order ...
```

---

## Executor Rewrite

### The Generic Action Loop

The core executor method becomes a simple loop:

```python
async def execute_mode(self, decision: ControllerDecision) -> list[ActionResult]:
    """Execute all actions for the decided mode."""
    mode_def = self.profile.get_mode(decision.mode_intent)
    results = []

    for action in mode_def.actions:
        # 1. Resolve entity ID
        entity_def = self.profile.get_entity(action.entity)
        entity_id = self._resolve_entity_id(action.entity, entity_def)

        if not entity_id:
            logger.warning("Entity '%s' not configured, skipping", action.entity)
            results.append(ActionResult(
                action=action.entity, success=False,
                reason=f"Entity not configured: {action.entity}"
            ))
            continue

        # 2. Resolve value (handle templates)
        value = self._resolve_value(action.value, decision)

        # 3. Idempotent check: skip if already at target
        current = self._get_current_value(entity_id)
        if current is not None and self._values_match(current, value):
            results.append(ActionResult(
                action=action.entity, success=True,
                reason="Already at target", skipped=True
            ))
            continue

        # 4. Shadow mode check
        if self.shadow_mode:
            logger.info("[SHADOW] Would set %s → %s", entity_id, value)
            results.append(ActionResult(
                action=action.entity, success=True,
                reason="Shadow mode", skipped=True
            ))
            continue

        # 5. Execute the write using domain-appropriate HA service
        success = await self._write_entity(entity_id, value, entity_def.domain)
        results.append(ActionResult(
            action=action.entity, success=success,
            entity_id=entity_id, value=value
        ))

        # 6. Settle delay if specified
        if action.settle_ms:
            await asyncio.sleep(action.settle_ms / 1000.0)

    return results

def _resolve_entity_id(self, key: str, entity_def: EntityDefinition) -> str | None:
    """Resolve entity key to actual HA entity ID using resolution order."""
    # 1. User override in custom_entities
    override = self.config.inverter.custom_entities.get(key)
    if override:
        return override
    # 2. Standard config location
    standard = getattr(self.config.inverter, key, None)
    if standard:
        return standard
    # 3. Profile default
    return entity_def.default_entity

def _resolve_value(self, value: Any, decision: ControllerDecision) -> Any:
    """Resolve dynamic template values from ControllerDecision."""
    if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
        field_name = value[2:-2]  # Strip {{ and }}
        if not hasattr(decision, field_name):
            raise ProfileError(f"Unknown template variable: {value}")
        return getattr(decision, field_name)
    return value

async def _write_entity(self, entity_id: str, value: Any, domain: str) -> bool:
    """Write value to HA entity using appropriate service call."""
    if domain == "number" or domain == "input_number":
        return self.ha.set_number(entity_id, float(value))
    elif domain == "select":
        return self.ha.set_select_option(entity_id, str(value))
    elif domain == "switch":
        return self.ha.set_switch(entity_id, bool(value))
    else:
        raise ProfileError(f"Unknown entity domain: {domain}")
```

### What Stays in `actions.py`

1. **Safety guards** — Universal max current/power limits
2. **Notification logic** — `_maybe_notify()` stays
3. **Action verification** — `_verify_action()` stays
4. **ActionResult / ActionType dataclasses** — Stay (may need minor updates)

### What Gets DELETED from `actions.py`

- `_set_work_mode()` (~80 lines)
- `_apply_composite_entities()` (~220 lines)
- `_set_grid_charging()` (~70 lines)
- `_set_charge_limit()` (~120 lines)
- `_set_discharge_limit()` (~100 lines)
- `_set_soc_target()` (~40 lines)
- `_set_max_export_power()` (~80 lines)
- `_get_mode_def_for_value()` (~20 lines)
- All `STANDARD_ENTITY_KEYS` constant and related lookups

**Estimated removal: ~730 lines. Net result: ~400-500 lines.**

---

## Controller Simplification

### New `_follow_plan` (replaces current 90-line version)

```python
def _follow_plan(self, slot: SlotPlan, state: SystemState) -> ControllerDecision:
    """Follow the slot plan for normal operation."""
    # Determine mode intent — 4 modes only
    if slot.export_kw > 0:
        mode_intent = "export"
    elif slot.charge_kw > 0:
        mode_intent = "charge"
    elif state.current_soc_percent <= slot.soc_target:
        mode_intent = "idle"
    else:
        mode_intent = "self_consumption"

    # Calculate charge/discharge values (stays the same)
    charge_value, write_charge = self._calculate_charge_limit(slot, state)
    discharge_value, write_discharge = self._calculate_discharge_limit(slot, state)

    # Populate max_charge / max_discharge from battery config for templates
    unit = self.profile.behavior.control_unit
    max_charge = self.config.max_charge_w if unit == "W" else self.config.max_charge_a
    max_discharge = self.config.max_discharge_w if unit == "W" else self.config.max_discharge_a

    return ControllerDecision(
        mode_intent=mode_intent,
        charge_value=charge_value,
        discharge_value=discharge_value,
        export_power_w=slot.export_kw * 1000.0,
        soc_target=slot.soc_target,
        max_charge=max_charge,
        max_discharge=max_discharge,
        water_temp=self._determine_water_temp(slot),
        write_charge_current=write_charge,
        write_discharge_current=write_discharge,
        control_unit=self.profile.behavior.control_unit,
        source="plan",
        reason=self._generate_reason(slot, mode_intent),
    )
```

### What Changes in `ControllerDecision`

```diff
@dataclass
class ControllerDecision:
-   work_mode: str                    # REMOVED — executor resolves this from profile
-   grid_charging: bool               # REMOVED — just another action in the mode
+   mode_intent: str                  # "charge", "export", "idle", "self_consumption"
    charge_value: float
    discharge_value: float
    soc_target: int
    water_temp: int
    export_power_w: float = 0.0
+   max_charge: float = 0.0           # NEW — user's max charge (A or W) for templates
+   max_discharge: float = 0.0        # NEW — user's max discharge (A or W) for templates
    write_charge_current: bool = False
    write_discharge_current: bool = False
    control_unit: str = "A"
    source: str = "plan"
    reason: str = ""
-   mode_intent: str | None = None    # REMOVED as optional — now required primary field
```

### What Gets DELETED from `controller.py`

- `_get_mode_def_for_value()` method
- All `self.inverter_config.work_mode_export` / `work_mode_zero_export` references
- Legacy Deye hardcoded fallback (the `else` branch in `_follow_plan`)
- `grid_charging` logic in controller (moved to profile actions)

---

## Settings UI Integration

### How It Works

The frontend's "Required HA Control Entities" section in the System tab (and Battery tab) becomes **dynamically driven** by the profile's entity registry.

### Backend API

Add a new endpoint or extend the existing profile endpoint:

```
GET /api/profile/entities
```

Response:
```json
{
  "entities": {
    "work_mode": {
      "default_entity": "select.inverter_work_mode",
      "domain": "select",
      "category": "system",
      "description": "Inverter operating mode selector",
      "required": true,
      "current_value": "select.my_custom_work_mode"
    },
    "max_charge_power": {
      "default_entity": "number.battery_max_charge_power",
      "domain": "number",
      "category": "battery",
      "description": "Battery max charge power",
      "required": true,
      "current_value": null
    }
  }
}
```

### Frontend Changes

Replace the hardcoded fields in `systemSections` and `batterySections` ("Required HA Control Entities" section) with **dynamically-generated fields** from the profile API response:

1. When the user selects a profile (or on page load), fetch the profile's entity registry from the API.
2. Group entities by `category` (`system` → System tab, `battery` → Battery tab).
3. Render a field for each entity with:
   - Label = entity `description`
   - Type = `entity`
   - Default/placeholder = `default_entity` from profile
   - Current value = user's configured value (from config)
4. Mark `required` entities as required in the UI.

### What Gets REMOVED from `types.ts`

All the hardcoded entity fields with `showIf: { configKey: 'system.inverter_profile', value: 'fronius' }` etc. in the "Required HA Control Entities" section. These are replaced by dynamic rendering.

### What STAYS in `types.ts`

- All non-inverter-profile fields (pricing, sensors, notifications, etc.)
- Battery specifications (capacity, SoC limits, voltage) — these are user config, not profile entities
- The profile selector dropdown (`system.inverter_profile`)

---

## Execution History / Logging

### What History Shows

Each execution tick produces a record like:

```json
{
  "mode_intent": "charge",
  "mode_description": "Force charge battery from AC grid",
  "actions": [
    {
      "entity_key": "work_mode",
      "entity_id": "select.ems_mode",
      "value": "Forced mode",
      "success": true,
      "skipped": false
    },
    {
      "entity_key": "forced_charge_cmd",
      "entity_id": "select.battery_forced_charge_discharge",
      "value": "Forced charge",
      "success": true,
      "skipped": false
    },
    {
      "entity_key": "max_charge_power",
      "entity_id": "number.battery_max_charge_power",
      "value": 3000,
      "success": true,
      "skipped": false
    },
    {
      "entity_key": "max_discharge_power",
      "entity_id": "number.battery_max_discharge_power",
      "value": 5000,
      "success": true,
      "skipped": true,
      "reason": "Already at target"
    }
  ]
}
```

The frontend execution history panel reads this directly — no special per-inverter formatting needed.

---

## Complete Profile Examples

### Deye / SunSynk Profile (v2)

```yaml
# ============================================================
# Inverter Profile: Deye / SunSynk
# Schema Version: 2
# ============================================================

metadata:
  name: "deye"
  version: "2.0.0"
  schema_version: 2
  description: "Deye and SunSynk hybrid inverters using Amps-based control"
  supported_brands:
    - "Deye"
    - "SunSynk"

entities:
  work_mode:
    default_entity: "select.sunsynk_work_mode"
    domain: "select"
    category: "system"
    description: "Inverter work mode selector"
    required: true

  grid_charging_enable:
    default_entity: "switch.sunsynk_grid_charging"
    domain: "switch"
    category: "system"
    description: "Grid charging on/off switch"
    required: true

  soc_target:
    default_entity: "number.sunsynk_battery_soc_target"
    domain: "number"
    category: "battery"
    description: "Battery SoC target percentage"
    required: true

  max_charge_current:
    default_entity: "number.sunsynk_battery_max_charge_current"
    domain: "number"
    category: "battery"
    description: "Maximum battery charging current (Amps)"
    required: true

  max_discharge_current:
    default_entity: "number.sunsynk_battery_max_discharge_current"
    domain: "number"
    category: "battery"
    description: "Maximum battery discharge current (Amps)"
    required: true

modes:
  charge:
    description: "Grid charge — Force charge battery from AC grid"
    actions:
      - entity: "work_mode"
        value: "Zero Export To CT"
      - entity: "grid_charging_enable"
        value: true
      - entity: "max_charge_current"
        value: "{{charge_value}}"
      - entity: "soc_target"
        value: "{{soc_target}}"

  export:
    description: "Grid export — Discharge battery to grid for profit"
    actions:
      - entity: "work_mode"
        value: "Export First"
      - entity: "grid_charging_enable"
        value: false
      - entity: "max_discharge_current"
        value: "{{discharge_value}}"

  self_consumption:
    description: "Self consumption — PV to battery and house, no grid export"
    actions:
      - entity: "work_mode"
        value: "Zero Export To CT"
      - entity: "grid_charging_enable"
        value: false
      - entity: "soc_target"
        value: "{{soc_target}}"

  idle:
    description: "Idle / Hold — Block discharge, preserve battery"
    actions:
      - entity: "work_mode"
        value: "Zero Export To CT"
      - entity: "grid_charging_enable"
        value: false
      - entity: "max_discharge_current"
        value: 0
      - entity: "soc_target"
        value: "{{soc_target}}"

behavior:
  control_unit: "A"
  min_charge_a: 1.0
  round_step_a: 1.0
  mode_settling_ms: 100
```

### Sungrow Profile (v2)

```yaml
# ============================================================
# Inverter Profile: Sungrow
# Schema Version: 2
# ============================================================

metadata:
  name: "sungrow"
  version: "2.0.0"
  schema_version: 2
  description: "Sungrow hybrid inverters using Watts-based control with composite modes"
  supported_brands:
    - "Sungrow"

entities:
  work_mode:
    default_entity: "select.ems_mode"
    domain: "select"
    category: "system"
    description: "EMS Mode selector (primary operating mode)"
    required: true

  forced_charge_discharge_cmd:
    default_entity: "select.battery_forced_charge_discharge"
    domain: "select"
    category: "system"
    description: "Forced charge/discharge command selector"
    required: true

  max_charge_power:
    default_entity: "number.battery_max_charge_power"
    domain: "number"
    category: "battery"
    description: "Maximum battery charging power (Watts)"
    required: true

  max_discharge_power:
    default_entity: "number.battery_max_discharge_power"
    domain: "number"
    category: "battery"
    description: "Maximum battery discharge power (Watts)"
    required: true

  export_power_limit:
    default_entity: "number.export_power_limit"
    domain: "number"
    category: "battery"
    description: "Grid export power limit (Watts)"
    required: false

modes:
  charge:
    description: "Grid charge — Force charge battery from AC grid"
    actions:
      - entity: "work_mode"
        value: "Forced mode"
      - entity: "forced_charge_discharge_cmd"
        value: "Forced charge"
      - entity: "max_charge_power"
        value: "{{charge_value}}"
      - entity: "max_discharge_power"
        value: "{{max_discharge}}"

  export:
    description: "Grid export — Force discharge battery to grid"
    actions:
      - entity: "work_mode"
        value: "Forced mode"
      - entity: "forced_charge_discharge_cmd"
        value: "Forced discharge"
      - entity: "max_discharge_power"
        value: "{{discharge_value}}"

  self_consumption:
    description: "Self consumption — Normal PV to battery and house"
    actions:
      - entity: "work_mode"
        value: "Self-consumption mode (default)"
      - entity: "forced_charge_discharge_cmd"
        value: "Stop (default)"
      - entity: "max_discharge_power"
        value: "{{max_discharge}}"

  idle:
    description: "Idle / Hold — Block discharge, preserve battery"
    actions:
      - entity: "work_mode"
        value: "Self-consumption mode (default)"
      - entity: "forced_charge_discharge_cmd"
        value: "Stop (default)"
      - entity: "max_discharge_power"
        value: 10

behavior:
  control_unit: "W"
  min_charge_w: 10.0
  round_step_w: 100.0
  write_threshold_w: 100.0
  mode_settling_ms: 100
```

### Fronius Profile (v2)

```yaml
# ============================================================
# Inverter Profile: Fronius
# Schema Version: 2
# ============================================================

metadata:
  name: "fronius"
  version: "2.0.0"
  schema_version: 2
  description: "Fronius GEN24 hybrid inverters using Watts-based control"
  supported_brands:
    - "Fronius"

entities:
  work_mode:
    default_entity: "select.storage_control_mode"
    domain: "select"
    category: "system"
    description: "Storage control mode selector"
    required: true

  minimum_reserve:
    default_entity: "number.minimum_reserve"
    domain: "number"
    category: "system"
    description: "Minimum battery reserve percentage (used as SoC floor)"
    required: true

  grid_charge_power:
    default_entity: "number.grid_charge_power"
    domain: "number"
    category: "battery"
    description: "Grid charging power (Watts) — only active in Charge from Grid mode"
    required: true

  max_charge_power:
    default_entity: "number.battery_max_charge_power"
    domain: "number"
    category: "battery"
    description: "Maximum battery charging power (Watts)"
    required: true

  max_discharge_power:
    default_entity: "number.battery_max_discharge_power"
    domain: "number"
    category: "battery"
    description: "Maximum battery discharge power (Watts)"
    required: true

modes:
  charge:
    description: "Grid charge — Force charge from AC grid"
    actions:
      - entity: "work_mode"
        value: "Charge from Grid"
        settle_ms: 500
      - entity: "grid_charge_power"
        value: "{{charge_value}}"
      - entity: "minimum_reserve"
        value: "{{soc_target}}"

  export:
    description: "Grid export — Maximize battery discharge to grid"
    actions:
      - entity: "work_mode"
        value: "Auto"
        settle_ms: 500
      - entity: "max_discharge_power"
        value: "{{discharge_value}}"
      - entity: "minimum_reserve"
        value: 5

  self_consumption:
    description: "Self consumption — Normal automatic operation"
    actions:
      - entity: "work_mode"
        value: "Auto"
        settle_ms: 500
      - entity: "minimum_reserve"
        value: "{{soc_target}}"

  idle:
    description: "Idle / Hold — Block battery discharge"
    actions:
      - entity: "work_mode"
        value: "Block Discharging"
        settle_ms: 500
      - entity: "minimum_reserve"
        value: "{{soc_target}}"

behavior:
  control_unit: "W"
  min_charge_w: 100.0
  round_step_w: 100.0
  grid_charge_round_step_w: 100.0
  write_threshold_w: 100.0
  mode_settling_ms: 500
```

### Generic Profile (v2)

```yaml
# ============================================================
# Inverter Profile: Generic
# Schema Version: 2
# ============================================================

metadata:
  name: "generic"
  version: "2.0.0"
  schema_version: 2
  description: "Generic inverter profile — configure entities manually"
  supported_brands:
    - "Generic"
    - "Other"

entities:
  work_mode:
    default_entity: null
    domain: "select"
    category: "system"
    description: "Inverter work mode selector"
    required: true

  grid_charging_enable:
    default_entity: null
    domain: "switch"
    category: "system"
    description: "Grid charging on/off switch"
    required: true

  soc_target:
    default_entity: null
    domain: "number"
    category: "battery"
    description: "Battery SoC target percentage"
    required: true

  max_charge_current:
    default_entity: null
    domain: "number"
    category: "battery"
    description: "Maximum battery charging current"
    required: true

  max_discharge_current:
    default_entity: null
    domain: "number"
    category: "battery"
    description: "Maximum battery discharge current"
    required: true

modes:
  charge:
    description: "Grid charge — charge battery from AC grid"
    actions:
      - entity: "work_mode"
        value: "CONFIGURE_ME"
      - entity: "grid_charging_enable"
        value: true
      - entity: "max_charge_current"
        value: "{{charge_value}}"
      - entity: "soc_target"
        value: "{{soc_target}}"

  export:
    description: "Grid export — discharge battery to grid"
    actions:
      - entity: "work_mode"
        value: "CONFIGURE_ME"
      - entity: "grid_charging_enable"
        value: false
      - entity: "max_discharge_current"
        value: "{{discharge_value}}"

  self_consumption:
    description: "Self consumption — normal operation"
    actions:
      - entity: "work_mode"
        value: "CONFIGURE_ME"
      - entity: "grid_charging_enable"
        value: false
      - entity: "soc_target"
        value: "{{soc_target}}"

  idle:
    description: "Idle / Hold — block discharge, preserve battery"
    actions:
      - entity: "work_mode"
        value: "CONFIGURE_ME"
      - entity: "grid_charging_enable"
        value: false
      - entity: "max_discharge_current"
        value: 0
      - entity: "soc_target"
        value: "{{soc_target}}"

behavior:
  control_unit: "A"
  min_charge_a: 1.0
  round_step_a: 1.0
  mode_settling_ms: 100
```

---

## Files to Modify / Create / Delete

### New Files

| File | Purpose |
|------|---------|
| `profiles/deye.yaml` | Rewritten v2 profile (replaces v1) |
| `profiles/sungrow.yaml` | Rewritten v2 profile (replaces v1) |
| `profiles/fronius.yaml` | Rewritten v2 profile (replaces v1) |
| `profiles/generic.yaml` | Rewritten v2 profile (replaces v1) |
| `profiles/schema.yaml` | Rewritten v2 schema documentation |
| `tests/test_profiles_v2.py` | Comprehensive tests for profile v2 system |
| `tests/test_executor_v2.py` | Tests for the new generic action loop |

### Modified Files

| File | Changes |
|------|---------|
| `executor/profiles.py` | Complete rewrite: new dataclasses, v2 parser, entity resolution |
| `executor/actions.py` | Major reduction: remove per-action methods, add generic action loop |
| `executor/controller.py` | Simplify: 4 modes, remove legacy fallback, remove `work_mode` from decision |
| `executor/config.py` | Simplify entity loading — remove `custom_entities` special cases |
| `executor/engine.py` | Update to use new `ControllerDecision` (no `work_mode` field) |
| `executor/override.py` | Update override actions to use 4 mode intents |
| `backend/api/routers/config.py` | Update validation to use v2 profile entity registry |
| `backend/api/routers/executor.py` | Update execution history format |
| `frontend/src/pages/settings/types.ts` | Remove hardcoded entity fields, add dynamic rendering |
| `frontend/src/pages/settings/SettingsPage.tsx` | Fetch profile entities API, render dynamically |
| `frontend/src/components/ChartCard.tsx` (or history component) | Update to render new action log format |

### Deleted Files

| File | Reason |
|------|--------|
| `profiles/victron.yaml` | Never implemented, placeholder only — can be recreated when needed |
| `profiles/sungrow_logic.md` | Logic now lives in the profile YAML itself |
| `profiles/fronius_logic.md` | Logic now lives in the profile YAML itself |

### Test Files to Update/Delete

| File | Action |
|------|--------|
| `tests/test_executor_profiles.py` | DELETE — replaced by `test_profiles_v2.py` |
| `tests/test_profile_validation.py` | DELETE — replaced by `test_profiles_v2.py` |
| `tests/test_executor_fronius_profile.py` | DELETE — replaced by `test_profiles_v2.py` |
| `tests/test_executor_composite_mode.py` | DELETE — composite modes no longer exist |
| `tests/test_executor_actions.py` | REWRITE — test new generic action loop |
| `tests/test_executor_controller.py` | UPDATE — test new 4-mode controller |
| `tests/test_executor_watt_control.py` | UPDATE — ensure compatibility with new system |

---

## Test Requirements

### Profile Schema Tests (`test_profiles_v2.py`)

> [!IMPORTANT]
> All profile tests must be **permanent** and work with any future profiles added to the `profiles/` directory.

#### Test: All Profiles Load Successfully
```python
@pytest.mark.parametrize("profile_name", get_all_profile_names())
def test_profile_loads(profile_name):
    """Every .yaml in profiles/ must load without error."""
    profile = load_profile(profile_name)
    assert profile.metadata.schema_version == 2
    assert profile.metadata.name == profile_name
```

#### Test: All Profiles Have Required Modes
```python
REQUIRED_MODES = {"charge", "export", "self_consumption", "idle"}

@pytest.mark.parametrize("profile_name", get_all_profile_names())
def test_profile_has_required_modes(profile_name):
    """Every profile must define all 4 required modes."""
    profile = load_profile(profile_name)
    for mode in REQUIRED_MODES:
        assert mode in profile.modes, f"Profile '{profile_name}' missing mode: {mode}"
        assert len(profile.modes[mode].actions) > 0, f"Mode '{mode}' has no actions"
```

#### Test: All Mode Actions Reference Valid Entities
```python
@pytest.mark.parametrize("profile_name", get_all_profile_names())
def test_mode_actions_reference_valid_entities(profile_name):
    """Every action's entity key must exist in the entity registry."""
    profile = load_profile(profile_name)
    for mode_key, mode_def in profile.modes.items():
        for action in mode_def.actions:
            assert action.entity in profile.entities, (
                f"Profile '{profile_name}', mode '{mode_key}': "
                f"action references unknown entity '{action.entity}'"
            )
```

#### Test: Dynamic Templates Are Valid
```python
VALID_TEMPLATES = {"charge_value", "discharge_value", "soc_target", "export_power_w", "max_charge", "max_discharge"}

@pytest.mark.parametrize("profile_name", get_all_profile_names())
def test_dynamic_templates_valid(profile_name):
    """All {{template}} values must reference valid ControllerDecision fields."""
    profile = load_profile(profile_name)
    for mode_key, mode_def in profile.modes.items():
        for action in mode_def.actions:
            if isinstance(action.value, str) and action.value.startswith("{{"):
                template = action.value[2:-2]
                assert template in VALID_TEMPLATES, (
                    f"Profile '{profile_name}', mode '{mode_key}': "
                    f"unknown template '{{{{template}}}}'"
                )
```

#### Test: Entity Domains Are Valid
```python
VALID_DOMAINS = {"select", "number", "switch", "input_number"}

@pytest.mark.parametrize("profile_name", get_all_profile_names())
def test_entity_domains_valid(profile_name):
    """All entity domains must be supported HA domains."""
    profile = load_profile(profile_name)
    for key, entity in profile.entities.items():
        assert entity.domain in VALID_DOMAINS, (
            f"Profile '{profile_name}': entity '{key}' has invalid domain '{entity.domain}'"
        )
```

#### Test: Entity Categories Are Valid
```python
VALID_CATEGORIES = {"system", "battery"}

@pytest.mark.parametrize("profile_name", get_all_profile_names())
def test_entity_categories_valid(profile_name):
    """All entity categories must map to existing Settings tabs."""
    profile = load_profile(profile_name)
    for key, entity in profile.entities.items():
        assert entity.category in VALID_CATEGORIES, (
            f"Profile '{profile_name}': entity '{key}' has invalid category '{entity.category}'"
        )
```

#### Test: Profile Roundtrip (YAML → Dataclass → Validation)
```python
@pytest.mark.parametrize("profile_name", get_all_profile_names())
def test_profile_roundtrip(profile_name):
    """Load, parse, validate without error — catches schema drift."""
    profile = load_profile(profile_name)
    # Validate all required entities are defined
    required = profile.get_required_entities()
    assert len(required) > 0, f"Profile '{profile_name}' has no required entities"
    # Validate behavior
    assert profile.behavior.control_unit in ("A", "W")
```

### Executor Action Loop Tests (`test_executor_v2.py`)

#### Test: Execute Mode Writes All Actions
```python
async def test_execute_mode_writes_all_actions():
    """Executor writes every action in the mode's action list."""
    # Mock HA client, load Sungrow profile, execute "charge" mode
    # Assert: 4 HA service calls made in order
```

#### Test: Idempotent Skip
```python
async def test_idempotent_skip():
    """Actions are skipped when entity is already at target value."""
    # Set current state to match target, execute
    # Assert: action marked as skipped=True
```

#### Test: Dynamic Template Resolution
```python
async def test_dynamic_template_resolution():
    """{{charge_value}} resolves to ControllerDecision.charge_value."""
    # Create decision with charge_value=3000, execute "charge" mode
    # Assert: HA service called with value 3000
```

#### Test: Action Ordering Preserved
```python
async def test_action_ordering():
    """Actions execute in YAML order (top to bottom)."""
    # Use Fronius profile where work_mode must be set before power values
    # Assert: calls are in correct order
```

#### Test: Settle Delay Applied
```python
async def test_settle_delay():
    """settle_ms on an action causes a delay before next action."""
    # Use Fronius profile with settle_ms on work_mode
    # Assert: asyncio.sleep called with correct duration
```

#### Test: Shadow Mode Logs Without Writing
```python
async def test_shadow_mode():
    """In shadow mode, actions are logged but not written to HA."""
    # Enable shadow mode, execute
    # Assert: no HA service calls, all results marked shadow
```

#### Test: Entity Resolution Order
```python
def test_entity_resolution_order():
    """User override > standard config > profile default."""
    # Configure custom_entities override for work_mode
    # Assert: override is used instead of profile default
```

### Controller Tests

#### Test: 4 Mode Selection
```python
@pytest.mark.parametrize("charge_kw,export_kw,soc,target,expected", [
    (2.0, 0, 50, 30, "charge"),
    (0, 3.0, 80, 30, "export"),
    (0, 0, 25, 30, "idle"),
    (0, 0, 50, 30, "self_consumption"),
])
def test_mode_selection(charge_kw, export_kw, soc, target, expected):
    """Controller selects correct mode intent."""
```

### How to Run All Tests

```bash
# Run ALL profile and executor tests
uv run python -m pytest tests/test_profiles_v2.py tests/test_executor_v2.py tests/test_executor_controller.py -v

# Run ONLY profile schema tests (quick sanity check after editing profiles)
uv run python -m pytest tests/test_profiles_v2.py -v

# Run full test suite
uv run python -m pytest -q

# Lint
uv run ruff check .
cd frontend && pnpm lint
```
