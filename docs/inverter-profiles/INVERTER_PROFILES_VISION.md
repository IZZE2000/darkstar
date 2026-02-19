# Inverter Profiles - Vision & Design

> [!WARNING]
> **This document describes the v1 profile schema which has been superseded by v2.**
>
> For current profile creation, see:
> - **[CREATING_INVERTER_PROFILES.md](CREATING_INVERTER_PROFILES.md)** — v2 profile creation guide
> - **[profiles_v2_blueprint.md](profiles_v2_blueprint.md)** — Complete v2 implementation blueprint
>
> v2 changes include:
> - 4 mode intents only: `charge`, `export`, `idle`, `self_consumption` (removed `zero_export`, `charge_from_grid`)
> - Entity registry with `domain`/`category`/`description`
> - Ordered action lists instead of `value`/`set_entities`
> - Dynamic templates like `{{charge_value}}`

**Status**: Superseded by v2 (REV ARC17)
**Last Updated**: 2026-02-06 (v1), 2026-02-19 (v2 migration)
**Purpose**: Historical reference for v1 profile design

---

## Problem Statement

Darkstar currently supports Deye/SunSynk, Fronius, Sungrow and Generic inverters. To support these diverse hardware types, we implemented a flexible profile system that:

1. **Maintains planner logic** - The optimization engine stays brand-agnostic
2. **Adapts executor behavior** - Different inverters use different HA entities and control patterns
3. **Enables easy expansion** - Adding new brands should not require core code changes
4. **Preserves backward compatibility** - Existing Deye users continue working without changes

---

## Core Principles

### 1. Separation of Concerns

**Planner (Brand-Agnostic)**
- Decides WHAT to do: "Charge 3kW from grid at 02:00"
- Outputs: `schedule.json` with charge/discharge/export plans
- **Never changes** between inverter brands

**Executor (Brand-Specific)**
- Decides HOW to achieve it: "Set select.fronius_battery_mode to 'Charge from grid'"
- Translates Darkstar decisions → Inverter-specific HA entity commands
- **Adapts** based on inverter profile

### 2. Home Assistant as Abstraction Layer

- Darkstar controls **HA entities only** (select, switch, number)
- Users configure their inverter integration in HA (Modbus, official integration, etc.)
- Profiles define which HA entities to use and what values to send

### 3. YAML Configuration + Python Logic

- **YAML profiles**: Define entity mappings, mode values, capabilities
- **Python strategies**: Implement control logic using profile configuration
- **Strict Validation**: Profiles must explicitly define all required modes to prevent silent failures

---

## System Architecture

### Profile Structure

**Location**: `profiles/fronius.yaml`, `profiles/deye.yaml`, `profiles/sungrow.yaml`, `profiles/generic.yaml`

**Profile Schema**:
```yaml
# Profile metadata
name: "Fronius Gen24"
description: "Fronius hybrid inverters with battery management"
version: "1.0"
author: "Darkstar Community"

# Hardware capabilities
capabilities:
  control_unit: "W"              # "A" (Amperes) or "W" (Watts)
  has_work_modes: true           # Supports mode switching
  has_grid_charging: true        # Can charge from grid
  has_export_control: true       # Can export to grid
  has_soc_target: true           # Supports SoC target setting

# HA Entity mappings (with defaults)
entities:
  work_mode: "select.fronius_battery_mode"
  charge_power: "number.fronius_charge_power"
  discharge_power: "number.fronius_discharge_power"
  grid_charging: null            # Fronius may not have separate switch
  soc_target: "input_number.master_soc_target"

# Mode value translations
modes:
  # Darkstar internal mode → Inverter-specific value
  export: "Discharge to grid"
  zero_export: "Auto"
  idle: "Zero export to CT"    # REQUIRED: Mode for pausing/safe state
  charge_from_grid: "Charge from grid"
  force_discharge: "Block discharging"

# Profile-specific behavior flags
behavior:
  auto_mode_handles_pv: true     # "Auto" mode manages PV charging automatically
  requires_power_setpoint: true  # Must set power value when changing modes
  separate_grid_switch: false    # Grid charging controlled via mode, not separate switch
```

### Profile Loading & Validation

1.  **Strict Validation**: The executor aggressively validates loaded profiles. Missing required modes (`export`, `zero_export`, `idle`, `self_consumption`) will cause a `ValueError` and prevent the executor from running in an undefined state.
2.  **No Implicit Defaults**: The Python code does *not* assume any default values for work modes. If a profile is missing a mode, it must be fixed in the YAML.
3.  **Capability Checks**: The `ActionDispatcher` checks capability flags (e.g., `supports_soc_target`) before attempting to set entities, preventing errors in the log.

---

## Implementation Status

### Completed Phases
- ✅ **Infrastructure**: Profile schema, loader, and dataclasses (`executor/profiles.py`)
- ✅ **Deye Profile**: Migrated legacy hardcoded logic to `profiles/deye.yaml`
- ✅ **Fronius Profile**: Implemented `profiles/fronius.yaml` with correct case-sensitive modes
- ✅ **Generic Profile**: safe fallback for unknown hardware
- ✅ **UI Integration**: Frontend displays active profile and any configuration errors

### Inverter Support
- **Deye / SunSynk**: Full support (Amperes, separate grid switch)
- **Fronius Gen24**: Full support (Watts, mode-based grid charging) (Verified IP3)
- **Sungrow**: Basic support (Verified IP2)
- **Generic**: Limited support (Manual configuration required)

---

## Future Roadmap

### 1. Profile Marketplace
- Community repository for profiles?
- Automatic profile updates?

### 2. Auto-Discovery
- Attempt to auto-detect inverter type based on available HA entities?

### 3. Advanced Multi-Inverter Support
- Current system supports one active profile. Future versions could support multiple profiles for complex setups (e.g., AC-coupled retrofit + Hybrid).

---

## Problem Statement

Darkstar currently supports Deye/SunSynk inverters with hardcoded entity names and work mode values. To support other inverter brands (Fronius, Victron, etc.), we need a flexible profile system that:

1. **Maintains planner logic** - The optimization engine stays brand-agnostic
2. **Adapts executor behavior** - Different inverters use different HA entities and control patterns
3. **Enables easy expansion** - Adding new brands should not require core code changes
4. **Preserves backward compatibility** - Existing Deye users continue working without changes

---

## Core Principles

### 1. Separation of Concerns

**Planner (Brand-Agnostic)**
- Decides WHAT to do: "Charge 3kW from grid at 02:00"
- Outputs: `schedule.json` with charge/discharge/export plans
- **Never changes** between inverter brands

**Executor (Brand-Specific)**
- Decides HOW to achieve it: "Set select.fronius_battery_mode to 'Charge from grid'"
- Translates Darkstar decisions → Inverter-specific HA entity commands
- **Adapts** based on inverter profile

### 2. Home Assistant as Abstraction Layer

- Darkstar controls **HA entities only** (select, switch, number)
- Users configure their inverter integration in HA (Modbus, official integration, etc.)
- Profiles define which HA entities to use and what values to send

### 3. YAML Configuration + Python Logic

- **YAML profiles**: Define entity mappings, mode values, capabilities
- **Python strategies**: Implement control logic using profile configuration
- **Balance**: Simple enough for community contributions, powerful enough for complex behaviors

---

## Current System (Deye/Generic)

### How It Works Today

**Configuration** (`config.yaml`):
```yaml
executor:
  inverter:
    work_mode_entity: select.inverter_work_mode
    work_mode_export: "Export First"
    work_mode_zero_export: "Zero Export To CT"
    grid_charging_entity: switch.inverter_battery_grid_charging
    max_charging_current_entity: number.inverter_battery_max_charging_current
    control_unit: "A"
```

**Controller Decision** (Python):
```python
# When planner says "charge 3kW from grid"
work_mode = "Zero Export To CT"
grid_charging = True
charge_value = 60  # Amps
soc_target = 80
```

**Executor Actions** (Python → HA):
```python
ha.set_select_option("select.inverter_work_mode", "Zero Export To CT")
ha.set_switch("switch.inverter_battery_grid_charging", True)
ha.set_number("number.inverter_battery_max_charging_current", 60)
ha.set_number("input_number.master_soc_target", 80)
```

### Limitations

- Entity names hardcoded in config
- Mode values ("Export First") hardcoded
- Control unit (A vs W) is a simple toggle
- Adding new brands requires code changes

---

## Proposed System (Profile-Based)

### Profile Structure

**Location**: `profiles/fronius.yaml`, `profiles/deye.yaml`, `profiles/victron.yaml`

**Profile Schema**:
```yaml
# Profile metadata
name: "Fronius Gen24"
description: "Fronius hybrid inverters with battery management"
version: "1.0"
author: "Darkstar Community"

# Hardware capabilities
capabilities:
  control_unit: "W"              # "A" (Amperes) or "W" (Watts)
  has_work_modes: true           # Supports mode switching
  has_grid_charging: true        # Can charge from grid
  has_export_control: true       # Can export to grid
  has_soc_target: true           # Supports SoC target setting

# HA Entity mappings (with defaults)
entities:
  work_mode: "select.fronius_battery_mode"
  charge_power: "number.fronius_charge_power"
  discharge_power: "number.fronius_discharge_power"
  grid_charging: null            # Fronius may not have separate switch
  soc_target: "input_number.master_soc_target"

# Mode value translations
modes:
  # Darkstar internal mode → Inverter-specific value
  export: "Discharge to grid"
  zero_export: "Auto"
  hold: "Block discharging"
  charge_from_grid: "Charge from grid"

# Default configuration values
defaults:
  work_mode_export: "Discharge to grid"
  work_mode_zero_export: "Auto"
  max_charge_w: 5000
  max_discharge_w: 5000
  min_charge_w: 500

# Profile-specific behavior flags
behavior:
  auto_mode_handles_pv: true     # "Auto" mode manages PV charging automatically
  requires_power_setpoint: true  # Must set power value when changing modes
  separate_grid_switch: false    # Grid charging controlled via mode, not separate switch
```

### How Profiles Are Used

**1. User Selection** (`config.yaml`):
```yaml
system:
  inverter_profile: "fronius"  # Loads profiles/fronius.yaml
```

**2. Profile Loading** (Python):
```python
# executor/profiles.py
profile = load_profile("fronius")
# Returns: InverterProfile dataclass with all settings
```

**3. Controller Decision** (Unchanged):
```python
# Controller logic stays the same!
decision = ControllerDecision(
    work_mode="export",  # Internal Darkstar mode
    grid_charging=True,
    charge_value=3000,   # Watts
    soc_target=80
)
```

**4. Executor Translation** (Profile-aware):
```python
# executor/actions.py
async def _set_work_mode(self, internal_mode: str):
    # Translate internal mode → profile-specific value
    target_mode = self.profile.modes[internal_mode]
    entity = self.profile.entities["work_mode"]

    # "export" → "Discharge to grid" for Fronius
    # "export" → "Export First" for Deye
    await ha.set_select_option(entity, target_mode)
```

---

## Inverter-Specific Behaviors

### Deye / SunSynk (Current)

**Characteristics**:
- Separate work mode select + grid charging switch
- Uses Amperes (A) for charge/discharge limits
- Explicit "Export First" vs "Zero Export To CT" modes

**Profile Highlights**:
```yaml
control_unit: "A"
entities:
  work_mode: "select.inverter_work_mode"
  grid_charging: "switch.inverter_battery_grid_charging"
  charge_current: "number.inverter_battery_max_charging_current"
modes:
  export: "Export First"
  zero_export: "Zero Export To CT"
behavior:
  separate_grid_switch: true
```

### Fronius Gen24

**Characteristics**:
- Single battery mode select (no separate grid switch)
- Uses Watts (W) for charge/discharge limits
- "Auto" mode intelligently handles PV/load/battery
- Grid charging controlled via mode selection

**Profile Highlights**:
```yaml
control_unit: "W"
entities:
  work_mode: "select.fronius_battery_mode"
  charge_power: "number.fronius_charge_power"
  discharge_power: "number.fronius_discharge_power"
  grid_charging: null  # No separate switch
modes:
  export: "Discharge to grid"
  zero_export: "Auto"
  hold: "Block discharging"
  charge_from_grid: "Charge from grid"
behavior:
  auto_mode_handles_pv: true
  separate_grid_switch: false
```

### Victron (Future)

**Characteristics**:
- ESS (Energy Storage System) mode control
- Modbus-based control via Cerbo GX
- Complex multi-phase support

**Profile Highlights** (Placeholder):
```yaml
control_unit: "W"
entities:
  work_mode: "select.victron_ess_mode"
  charge_power: "number.victron_max_charge_power"
modes:
  export: "External Control"
  zero_export: "Optimized (with BatteryLife)"
behavior:
  requires_external_control: true
```

---

## Implementation Strategy

### Phase 1: Profile Infrastructure (REV X1)
- Create profile YAML schema and validation
- Implement profile loader (`executor/profiles.py`)
- Add profile dataclass with type hints
- Load profile based on `system.inverter_profile` setting

### Phase 2: Deye Profile Migration (REV X2)
- Create `profiles/deye.yaml` with current behavior
- Refactor executor to use profile for entity lookups
- Maintain 100% backward compatibility
- Test with existing Deye users

### Phase 3: Fronius Profile Implementation (REV X3)
- Create `profiles/fronius.yaml` based on community feedback
- Implement Fronius-specific mode translations
- Handle Watts-based control
- Beta test with Fronius users (Simon, Kristoffer)

### Phase 4: Generic Profile (REV X4)
- Create `profiles/generic.yaml` for unknown inverters
- Provide sensible defaults
- Allow manual entity configuration

### Phase 5: Community Expansion (REV X5+)
- Document profile creation guide
- Accept community-contributed profiles (Victron, Goodwe, etc.)
- Implement profile validation in CI/CD

---

## Technical Design

### Profile Data Structure

```python
# executor/profiles.py
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class InverterCapabilities:
    control_unit: str  # "A" or "W"
    has_work_modes: bool
    has_grid_charging: bool
    has_export_control: bool
    has_soc_target: bool

@dataclass
class InverterEntities:
    work_mode: Optional[str]
    charge_power: Optional[str]
    charge_current: Optional[str]
    discharge_power: Optional[str]
    discharge_current: Optional[str]
    grid_charging: Optional[str]
    soc_target: Optional[str]
    max_export_power: Optional[str]

@dataclass
class InverterModes:
    export: str
    zero_export: str
    hold: Optional[str]
    charge_from_grid: Optional[str]

@dataclass
class InverterBehavior:
    auto_mode_handles_pv: bool
    requires_power_setpoint: bool
    separate_grid_switch: bool
    requires_external_control: bool = False

@dataclass
class InverterProfile:
    name: str
    description: str
    version: str
    capabilities: InverterCapabilities
    entities: InverterEntities
    modes: InverterModes
    behavior: InverterBehavior
    defaults: Dict[str, any]
```

### Profile Loading

```python
def load_profile(profile_name: str) -> InverterProfile:
    """Load and validate inverter profile from YAML."""
    path = Path(f"profiles/{profile_name}.yaml")

    if not path.exists():
        logger.warning(f"Profile {profile_name} not found, using generic")
        return load_profile("generic")

    with path.open() as f:
        data = yaml.safe_load(f)

    # Validate schema
    validate_profile_schema(data)

    # Parse into dataclass
    return InverterProfile(
        name=data["name"],
        description=data["description"],
        version=data["version"],
        capabilities=InverterCapabilities(**data["capabilities"]),
        entities=InverterEntities(**data["entities"]),
        modes=InverterModes(**data["modes"]),
        behavior=InverterBehavior(**data["behavior"]),
        defaults=data.get("defaults", {})
    )
```

### Executor Integration

```python
# executor/engine.py
class ExecutorEngine:
    def __init__(self, config_path: str):
        self.config = load_executor_config(config_path)

        # Load inverter profile
        profile_name = self.config.inverter_profile
        self.profile = load_profile(profile_name)

        # Create profile-aware action dispatcher
        self.dispatcher = ActionDispatcher(
            ha_client=self.ha,
            config=self.config,
            profile=self.profile  # NEW!
        )
```

```python
# executor/actions.py
class ActionDispatcher:
    def __init__(self, ha_client, config, profile):
        self.ha = ha_client
        self.config = config
        self.profile = profile  # NEW!

    async def _set_work_mode(self, internal_mode: str):
        """Set work mode using profile translation."""
        # Get profile-specific entity and value
        entity = self.profile.entities.work_mode
        target_value = self.profile.modes[internal_mode]

        # Rest of logic stays the same
        current = self.ha.get_state_value(entity)
        if current == target_value:
            return  # Already set

        await self.ha.set_select_option(entity, target_value)
```

---

## Configuration Migration

### Backward Compatibility

Existing `config.yaml` continues to work:
```yaml
executor:
  inverter:
    work_mode_entity: select.inverter_work_mode
    work_mode_export: "Export First"
    # ... existing config
```

**Migration Strategy**:
1. If `system.inverter_profile` is set → Use profile
2. If not set → Use legacy config values (Deye behavior)
3. Profile values override config values (profile is SSOT)

### User Migration Path

**Step 1**: Add profile selection to config
```yaml
system:
  inverter_profile: "deye"  # Explicitly set
```

**Step 2**: Profile provides defaults, user can override
```yaml
system:
  inverter_profile: "fronius"

executor:
  inverter:
    # Override profile defaults if needed
    work_mode_entity: select.my_custom_fronius_mode
```

**Step 3**: Eventually deprecate legacy config (v3.0+)

---

## UI Integration

### Settings Page Updates

**System Tab** - Inverter Profile Selector:
```typescript
{
  key: 'system.inverter_profile',
  label: 'Inverter Profile',
  type: 'select',
  options: [
    { label: 'Deye / SunSynk', value: 'deye' },
    { label: 'Fronius Gen24', value: 'fronius' },
    { label: 'Victron ESS', value: 'victron' },
    { label: 'Generic (Manual)', value: 'generic' },
  ],
  helper: 'Select your inverter brand. Profile auto-configures entities and control behavior.'
}
```

**Dynamic Entity Fields**:
- When profile is selected, show only relevant entity fields
- Pre-fill entity names from profile defaults
- Show profile-specific help text

**Example**: Fronius profile selected
- Show: `work_mode_entity`, `charge_power_entity`, `discharge_power_entity`
- Hide: `grid_charging_entity` (not used by Fronius)
- Default: `select.fronius_battery_mode`

---

## Testing Strategy

### Profile Validation Tests
- Schema validation (required fields, types)
- Mode mapping completeness
- Entity name format validation

### Executor Tests
- Profile loading and fallback to generic
- Mode translation (internal → profile-specific)
- Entity lookup from profile
- Backward compatibility with legacy config

### Integration Tests
- Deye profile matches current behavior exactly
- Fronius profile produces correct HA calls
- Profile switching without restart

### User Acceptance Testing
- Beta test with Fronius users (Simon, Kristoffer)
- Verify real-world inverter behavior
- Collect feedback on missing modes/features

---

## Community Contribution

### Profile Creation Guide

**Documentation** (`docs/CREATING_INVERTER_PROFILES.md`):
1. Identify your inverter's HA entities
2. Map Darkstar modes to inverter modes
3. Define capabilities and behavior flags
4. Test with shadow mode
5. Submit PR with profile YAML

**Profile Template**:
```yaml
# profiles/template.yaml
name: "Your Inverter Brand"
description: "Brief description"
version: "1.0"
author: "Your Name"

capabilities:
  control_unit: "A"  # or "W"
  has_work_modes: true
  has_grid_charging: true
  has_export_control: true
  has_soc_target: true

entities:
  work_mode: "select.your_inverter_mode"
  # ... fill in your entities

modes:
  export: "Your Export Mode Name"
  zero_export: "Your Zero Export Mode Name"
  # ... map all modes

behavior:
  auto_mode_handles_pv: false
  requires_power_setpoint: false
  separate_grid_switch: true

defaults:
  max_charge_w: 5000
  # ... your defaults
```

---

## Open Questions

### 1. Profile Discovery
- Should profiles be auto-detected from HA entities?
- Or always require manual selection?

### 2. Profile Versioning
- How to handle profile updates?
- Notify users when profile schema changes?

### 3. Hybrid Profiles
- Some users have multiple inverters (e.g., Fronius + Victron)
- Support multiple profiles simultaneously?

### 4. Advanced Behaviors
- Some inverters have complex multi-phase control
- How to handle in profile system without over-complicating?

### 5. Profile Marketplace
- Community repository for profiles?
- Automatic profile updates?

---

## Success Criteria

### Must Have
- ✅ Deye users continue working without changes
- ✅ Fronius users can configure and use Darkstar
- ✅ Adding new profiles doesn't require Python code changes
- ✅ Profile system is documented and testable

### Should Have
- ✅ UI auto-configures based on selected profile
- ✅ Profile validation catches configuration errors
- ✅ Community can contribute profiles via PR

### Nice to Have
- ⭕ Profile auto-detection from HA entities
- ⭕ Profile marketplace/repository
- ⭕ Multi-inverter support

---

## Next Steps

1. **Review & Feedback**: Discuss this vision with beta testers
2. **REV Planning**: Break down into concrete implementation revisions
3. **Prototype**: Create basic profile loader and Deye profile
4. **Beta Test**: Test Fronius profile with Simon & Kristoffer
5. **Iterate**: Refine based on real-world usage

---

**Document Status**: Draft for Review
**Last Updated**: 2026-01-26
**Contributors**: Simon (Fronius feedback), Kristoffer (Fronius testing)
