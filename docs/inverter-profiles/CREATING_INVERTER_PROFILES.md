# Creating Inverter Profiles

Darkstar uses a profile-based system to support multiple inverter brands (Deye, Fronius, Victron, etc.) without requiring core code changes. This guide explains how to create a new profile for your inverter and contribute it to the community.

## Quick Start (5-Step Guide)

1.  **Find your Entities**: Identify the Home Assistant entity IDs for your inverter (e.g., `select.my_inverter_work_mode`).
2.  **Copy the Schema**: Copy `profiles/schema.yaml` to `profiles/your_brand.yaml`.
3.  **Map Capabilities**: Enable the flags that match your inverter's features (e.g., `watts_based_control: true`).
4.  **Translate Modes**: Map Darkstar internal modes (`export`, `zero_export`) to your inverter's specific mode strings.
5.  **Validate**: Run the validation script: `uv run python scripts/validate_profiles.py profiles/your_brand.yaml`.

---

## Profile Schema Reference

A profile is a YAML file with the following main sections:

### 1. Metadata
Defines basic information about the profile.
- `name`: Unique identifier (lowercase, no spaces).
- `supported_brands`: List of brands this profile works with.

### 2. Capabilities
Feature flags that tell Darkstar how to interact with the hardware.
- `control_unit`: "A" (Amperes) or "W" (Watts).
- `grid_charging_control`: If true, Darkstar will try to enable/disable grid charging.
- `separate_grid_charging_switch`: If true, assumes a separate `switch` entity for grid charging.

### 3. Entities
Home Assistant entity mappings.
- **Required**: `work_mode`, `soc_target`, and `grid_charging_enable` (if charging control is enabled).
- **Optional**: `max_charging_current`, `max_discharging_power`, etc.

### 4. Modes
Maps internal Darkstar states to your inverter's work mode values.
- `export`: Used when Darkstar wants to discharge the battery to the grid.
- `zero_export`: Standard self-consumption mode (prioritize local load).
- `charge_from_grid`: Specific mode for AC charging (if applicable).

### 5. Behavior
Defines numeric limits and rounding rules.
- `min_charge_a`/`w`: Minimum power level to trigger a charge command.
- `round_step_a`/`w`: Rounding increment for current/power values.

---

## Entity Discovery Guide

To find the correct entity IDs for your profile:

1.  Open Home Assistant.
2.  Go to **Developer Tools** -> **States**.
3.  Filter by your inverter integration (e.g., "solis", "victron").
4.  Look for:
    - **Select** entities for "Work Mode" or "Storage Mode".
    - **Number** entities for "Max Charge Current" or "SoC Limit".
    - **Switch** entities for "Grid Charge Enable".

> [!TIP]
> Always check the raw state value in the "State" column. This is the exact string you must put in the `modes` section of your profile.

---

## Mode Mapping Examples

### Deye / SunSynk Pattern
Uses a separate switch for grid charging.
```yaml
capabilities:
  separate_grid_charging_switch: true
modes:
  export: "Export First"
  zero_export: "Zero Export To CT"
  charge_from_grid:
    value: null # Stays in Zero Export, but switch turns ON
    requires_grid_charging: true
```

### Fronius Pattern
Single mode selector, no separate switch.
```yaml
capabilities:
  separate_grid_charging_switch: false
modes:
  export: "Discharge to grid"
  zero_export: "Auto"
  charge_from_grid: "Charge from grid"
```

---

## Testing & Validation

Before submitting a PR, validate your profile:

```bash
uv run python scripts/validate_profiles.py profiles/your_brand.yaml
```

If possible, test your profile in **Shadow Mode** in Darkstar to ensure it produces the expected logs without actually writing to your inverter if you are unsure.

---

## Submission Guidelines

1.  Ensure your profile name is unique and descriptive.
2.  Add yourself as the `author` in the metadata.
3.  Submit a Pull Request adding the `.yaml` file to the `profiles/` directory.
4.  Include a brief description in the PR of which hardware/integration you tested it with.
