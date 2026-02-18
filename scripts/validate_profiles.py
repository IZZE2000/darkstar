#!/usr/bin/env python3
"""
Inverter Profile Validator
Validates Darkstar inverter profile YAML files against the schema.
Supports both v1 and v2 schema.
"""

import sys
from pathlib import Path

import yaml

REQUIRED_MODES_V1 = ["export", "zero_export", "charge_from_grid", "idle", "self_consumption"]
REQUIRED_MODES_V2 = ["charge", "export", "idle", "self_consumption"]


def validate_profile(file_path):
    if "schema.yaml" in str(file_path):
        return True

    print(f"Validating {file_path}...")
    try:
        path = Path(file_path)
        with path.open("r") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"  [ERROR] Failed to parse YAML: {e}")
        return False

    errors = []

    metadata = data.get("metadata", {})
    if not metadata.get("name"):
        errors.append("Missing metadata.name")
    if not metadata.get("version"):
        errors.append("Missing metadata.version")

    schema_version = metadata.get("schema_version", 1)

    if schema_version == 2:
        return validate_profile_v2(file_path, data, errors)
    else:
        return validate_profile_v1(file_path, data, errors)


def validate_profile_v1(file_path, data, errors):
    capabilities = data.get("capabilities", {})
    if "watts_based_control" not in capabilities:
        errors.append("Missing capabilities.watts_based_control")

    entities = data.get("entities", {})
    required_entities = entities.get("required", {})
    if "work_mode" not in required_entities:
        errors.append("Missing entities.required.work_mode")

    modes = data.get("modes", {})
    for mode_name in REQUIRED_MODES_V1:
        if mode_name not in modes:
            errors.append(f"Missing required mode: '{mode_name}'")

    def check_entities(entity_dict):
        for key, val in entity_dict.items():
            if val and "." not in val and key not in ["forced_power"]:
                errors.append(
                    f"Invalid HA entity ID format for '{key}': '{val}' (must be 'domain.name')"
                )

    check_entities(required_entities)
    check_entities(entities.get("optional", {}))

    if errors:
        for err in errors:
            print(f"  [ERROR] {err}")
        return False

    print("  [OK] Profile is valid (v1).")
    return True


def validate_profile_v2(file_path, data, errors):
    entities = data.get("entities", {})
    if not entities:
        errors.append("Missing entities registry")

    modes = data.get("modes", {})
    for mode_name in REQUIRED_MODES_V2:
        if mode_name not in modes:
            errors.append(f"Missing required mode: '{mode_name}'")
        else:
            mode = modes[mode_name]
            if "actions" not in mode:
                errors.append(f"Mode '{mode_name}' missing actions list")
            elif not isinstance(mode["actions"], list):
                errors.append(f"Mode '{mode_name}' actions must be a list")

    behavior = data.get("behavior", {})
    if not behavior:
        errors.append("Missing behavior section")
    else:
        if "control_unit" not in behavior:
            errors.append("Missing behavior.control_unit")

    if errors:
        for err in errors:
            print(f"  [ERROR] {err}")
        return False

    print("  [OK] Profile is valid (v2).")
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
