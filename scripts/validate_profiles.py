#!/usr/bin/env python3
"""
Inverter Profile Validator
Validates Darkstar inverter profile YAML files against the schema.
"""

import sys
from pathlib import Path

import yaml

# Mapping of required modes that Darkstar expects
REQUIRED_MODES = ["export", "zero_export", "charge_from_grid", "idle", "self_consumption"]


def validate_profile(file_path):
    print(f"Validating {file_path}...")
    try:
        path = Path(file_path)
        with path.open("r") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"  [ERROR] Failed to parse YAML: {e}")
        return False

    errors = []

    # 1. Metadata Check
    metadata = data.get("metadata", {})
    if not metadata.get("name"):
        errors.append("Missing metadata.name")
    if not metadata.get("version"):
        errors.append("Missing metadata.version")

    # 2. Capabilities Check
    capabilities = data.get("capabilities", {})
    if "watts_based_control" not in capabilities:
        errors.append("Missing capabilities.watts_based_control")

    # 3. Entities Check
    entities = data.get("entities", {})
    required_entities = entities.get("required", {})
    if "work_mode_entity" not in required_entities:
        errors.append("Missing entities.required.work_mode_entity")

    # 4. Mode Completeness
    modes = data.get("modes", {})
    for mode_name in REQUIRED_MODES:
        if mode_name not in modes:
            errors.append(f"Missing required mode: '{mode_name}'")

    # 5. Entity Format Check (simple regex-like check)
    def check_entities(entity_dict):
        for key, val in entity_dict.items():
            if val and "." not in val:
                errors.append(
                    f"Invalid HA entity ID format for '{key}': '{val}' (must be 'domain.name')"
                )

    check_entities(required_entities)
    check_entities(entities.get("optional", {}))

    if errors:
        for err in errors:
            print(f"  [ERROR] {err}")
        return False

    print("  [OK] Profile is valid.")
    return True


def main():
    if len(sys.argv) < 2:
        # Default to all profiles in ./profiles/
        profiles = [str(p) for p in Path("profiles").glob("*.yaml")]
        # Exclude schema.yaml
        profiles = [p for p in profiles if "schema.yaml" not in p]
    else:
        profiles = sys.argv[1:]

    success = True
    for profile in profiles:
        if not validate_profile(profile):
            success = False

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
