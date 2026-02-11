import contextlib
import logging
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from ruamel.yaml import YAML
except ImportError:
    # Fallback if ruamel.yaml is not available (should be in requirements.txt)
    YAML = None

logger = logging.getLogger("darkstar.config_migration")

# Type alias for migration functions
# Returns: (modified_config, changed_bool)
MigrationStep = Callable[[Any], tuple[Any, bool]]


# =============================================================================
# Centralized Deprecated Keys Registry
# =============================================================================
# These keys MUST be removed during migration to prevent corruption

# Root-level deprecated keys
DEPRECATED_KEYS = {
    "deferrable_loads",  # ARC15: Replaced by water_heaters[] and ev_chargers[]
    "ev_charger",  # ARC15: Replaced by ev_chargers[] array (plural)
    "solar_array",  # Replaced by solar_arrays[] array (plural)
    "version",  # Replaced by config_version
    "schedule_future_only",  # REV F19: Removed
}

# Nested deprecated keys (path.to.key format)
DEPRECATED_NESTED_KEYS = {
    "executor.inverter": [
        # IP4: Old _entity suffix keys replaced by standardized names
        "work_mode_entity",
        "soc_target_entity",
        "grid_charging_entity",
        "max_charging_current_entity",
        "max_discharging_current_entity",
        "max_charging_power_entity",
        "max_discharging_power_entity",
        "grid_max_export_power_entity",
        "grid_charge_power_entity",
        "minimum_reserve_entity",
    ]
}


def remove_deprecated_keys(config: Any) -> tuple[Any, bool]:
    """Remove all deprecated keys from config.

    REV F57: Centralized cleanup to prevent corrupted configs with legacy keys.

    Args:
        config: Configuration dict to clean

    Returns:
        Tuple of (cleaned_config, changed_flag)
    """
    changed = False

    if not isinstance(config, dict):
        return config, False

    # Root-level deprecated keys
    for key in DEPRECATED_KEYS:
        if key in config:
            del config[key]
            logger.info(f"✂️  Removed deprecated key: '{key}'")
            changed = True

    # Nested deprecated keys
    for path, keys in DEPRECATED_NESTED_KEYS.items():
        parts = path.split(".")
        obj = config

        # Navigate to nested object
        for part in parts:
            if isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                break
        else:
            # Object exists, clean deprecated keys
            if isinstance(obj, dict):
                for key in keys:
                    if key in obj:
                        del obj[key]
                        logger.info(f"✂️  Removed deprecated key: '{path}.{key}'")
                        changed = True

    return config, changed


def migrate_version_key(config: Any) -> tuple[Any, bool]:
    """Migration: Rename 'version' to 'config_version'.

    REV F57: Old configs used 'version' (string like "2.4.21-beta").
    New configs use 'config_version' (integer like 2 for format tracking).

    Args:
        config: Configuration dict

    Returns:
        Tuple of (migrated_config, changed_flag)
    """
    changed = False

    if not isinstance(config, dict):
        return config, False

    if "version" in config:
        old_version = config.pop("version")

        # Only set config_version if not already present
        if "config_version" not in config:
            config["config_version"] = 2  # Current format version
            logger.info(f"📝 Migrated 'version' ({old_version}) -> 'config_version' (2)")
            changed = True
        else:
            logger.info(
                f"📝 Removed old 'version' key ({old_version}), 'config_version' already set"
            )
            changed = True

    return config, changed


def migrate_battery_config(config: Any) -> tuple[Any, bool]:
    """
    Migration for REV F17: Unify Battery & Control Configuration.
    Moves hardware limits from executor.controller to root battery section.
    """
    changed = False

    # Target section
    if "battery" not in config:
        config["battery"] = {}
    battery = config["battery"]

    # Source section
    executor = config.get("executor", {})
    controller = executor.get("controller", {})

    if not controller:
        return config, False

    # Mapping of (Legacy Key, New Key)
    mapping = {
        "battery_capacity_kwh": "capacity_kwh",
        "system_voltage_v": "nominal_voltage_v",
        "worst_case_voltage_v": "min_voltage_v",
        "max_charge_a": "max_charge_a",
        "max_discharge_a": "max_discharge_a",
        "max_charge_w": "max_charge_w",
        "max_discharge_w": "max_discharge_w",
    }

    for legacy_key, new_key in mapping.items():
        if legacy_key in controller:
            val = controller.pop(legacy_key)

            # Only set if not already present in target (preserve existing battery settings if any)
            # OR if it was the redundant battery_capacity_kwh which we want to unify
            if new_key not in battery or legacy_key == "battery_capacity_kwh":
                battery[new_key] = val
                logger.info(f"Migrated {legacy_key} -> battery.{new_key}")
                changed = True
            else:
                logger.info(f"Removed legacy {legacy_key} (already exists in battery.{new_key})")
                changed = True

    return config, changed


def cleanup_obsolete_keys(config: Any) -> tuple[Any, bool]:
    """
    Migration for REV F19: Cleanup obsolete keys and move end_date.
    Matches the actual observed nesting in config.yaml.
    """
    changed = False

    # 1. Remove schedule_future_only (could be at root or under water_heating)
    if "schedule_future_only" in config:
        config.pop("schedule_future_only")
        logger.info("Removed root level obsolete key: schedule_future_only")
        changed = True

    if (
        "water_heating" in config
        and isinstance(config["water_heating"], dict)
        and "schedule_future_only" in config["water_heating"]
    ):
        config["water_heating"].pop("schedule_future_only")
        logger.info("Removed water_heating level obsolete key: schedule_future_only")
        changed = True

    # 2. Re-anchor end_date if it is "leaking" past comments
    end_date_val = None
    source_parent = None

    if "end_date" in config:
        end_date_val = config.pop("end_date")
        source_parent = "root"
    elif "water_heating" in config and isinstance(config["water_heating"], dict):
        wh = config["water_heating"]
        if "end_date" in wh:
            end_date_val = wh.pop("end_date")
            source_parent = "water_heating"
        elif "vacation_mode" in wh and isinstance(wh["vacation_mode"], dict):
            vm = wh["vacation_mode"]
            if "end_date" in vm:
                end_date_val = vm.pop("end_date")
                source_parent = "vacation_mode"

    if end_date_val is not None:
        if "water_heating" not in config:
            config["water_heating"] = {}
        if "vacation_mode" not in config["water_heating"]:
            config["water_heating"]["vacation_mode"] = {}

        config["water_heating"]["vacation_mode"]["end_date"] = end_date_val
        logger.info(f"Re-aligned end_date to vacation_mode from {source_parent}")
        changed = True

    return config, changed


def migrate_soc_target_entity(config: Any) -> tuple[Any, bool]:
    """
    Migration for soc_target_entity: Move from root executor to executor.inverter.
    """
    changed = False

    if "executor" not in config:
        return config, False

    executor = config["executor"]

    # Check for legacy key
    if "soc_target_entity" in executor:
        legacy_val = executor.pop("soc_target_entity")

        # Ensure target section exists
        if "inverter" not in executor:
            executor["inverter"] = {}

        inverter = executor["inverter"]

        # Only set if not already present (prefer existing new config)
        if "soc_target_entity" not in inverter:
            inverter["soc_target_entity"] = legacy_val
            logger.info(
                "Migrated executor.soc_target_entity -> executor.inverter.soc_target_entity"
            )
            changed = True
        else:
            logger.info("Removed legacy executor.soc_target_entity (already exists in inverter)")
            changed = True

    return config, changed


def migrate_solar_arrays(config: Any) -> tuple[Any, bool]:
    """
    Migration for REV ARC14: Multi-Array PV Support.
    Converts legacy 'solar_array' object to 'solar_arrays' list.
    """
    changed = False

    if "system" not in config or not isinstance(config["system"], dict):
        return config, False

    system = config["system"]

    if "solar_array" in system:
        legacy_array = system.pop("solar_array")
        if isinstance(legacy_array, dict):
            # Ensure name is present for migrated array
            if "name" not in legacy_array:
                legacy_array["name"] = "Main Array"

            system["solar_arrays"] = [legacy_array]
            logger.info("Migrated system.solar_array -> system.solar_arrays (list)")
            changed = True
        else:
            logger.warning("Found legacy system.solar_array but it was not a dict.")

    # REV F57: Verify solar_array is actually gone
    if "solar_array" in system:
        logger.warning("⚠️  'solar_array' still present after migration - forcing delete")
        del system["solar_array"]
        changed = True

    return config, changed


def migrate_inverter_profile_keys(config: Any) -> tuple[Any, bool]:
    """
    Migration for REV IP4: Standardize Inverter Profile Keys.
    Removes `_entity` suffixes to match new profile schema.
    """
    changed = False

    if "executor" not in config:
        return config, False

    executor = config["executor"]
    if "inverter" not in executor:
        return config, False

    inverter = executor["inverter"]

    mapping = {
        "work_mode_entity": "work_mode",
        "soc_target_entity": "soc_target",
        "grid_charging_entity": "grid_charging_enable",
        "max_charging_current_entity": "max_charge_current",
        "max_discharging_current_entity": "max_discharge_current",
        "max_charging_power_entity": "max_charge_power",
        "max_discharging_power_entity": "max_discharge_power",
        "grid_max_export_power_entity": "grid_max_export_power",
        "grid_charge_power_entity": "grid_charge_power",
        "minimum_reserve_entity": "minimum_reserve",
    }

    for legacy, new in mapping.items():
        if legacy in inverter:
            val = inverter.pop(legacy)
            if new not in inverter:
                inverter[new] = val
                logger.info(f"Migrated executor.inverter.{legacy} -> {new}")
                changed = True
            else:
                logger.info(f"Removed legacy executor.inverter.{legacy} (already exists as {new})")
                changed = True

    return config, changed


def migrate_arc15_entity_config(config: Any) -> tuple[Any, bool]:
    """
    Migration for REV ARC15: Entity-Centric Config Restructure.

    Converts old deferrable_loads array to new water_heaters[] and ev_chargers[] arrays.
    This provides a single source of truth for each entity type and eliminates
    duplication between system toggles, input_sensors, and deferrable_loads.

    Migration rules:
    - deferrable_loads with id="water_heater" -> water_heaters[]
    - deferrable_loads with id="ev_charger" or type="ev" -> ev_chargers[]
    - Preserves all settings and maps sensors appropriately
    - Sets config_version to 2
    """
    changed = False

    # Check if already migrated (config_version >= 2 or new arrays exist)
    current_version = config.get("config_version", 1)
    if current_version >= 2:
        logger.debug("Config already at version %d, skipping ARC15 migration", current_version)
        return config, False

    if "water_heaters" in config and "ev_chargers" in config:
        logger.debug("New entity arrays already exist, marking as migrated")
        config["config_version"] = 2
        return config, True

    deferrable_loads = config.get("deferrable_loads", [])
    if not deferrable_loads:
        logger.debug("No deferrable_loads to migrate")
        # Still mark as migrated if we have the new arrays or nothing to migrate
        if "water_heaters" in config or "ev_chargers" in config:
            config["config_version"] = 2
            changed = True
        return config, changed

    input_sensors = config.get("input_sensors", {})
    water_heating = config.get("water_heating", {})
    ev_charger = config.get("ev_charger", {})
    system = config.get("system", {})

    # Initialize new arrays if they don't exist
    if "water_heaters" not in config:
        config["water_heaters"] = []
    if "ev_chargers" not in config:
        config["ev_chargers"] = []

    water_heaters = config["water_heaters"]
    ev_chargers = config["ev_chargers"]

    # Track existing IDs to avoid duplicates
    existing_water_ids = {wh.get("id") for wh in water_heaters if wh.get("id")}
    existing_ev_ids = {ev.get("id") for ev in ev_chargers if ev.get("id")}

    for load in deferrable_loads:
        load_id = load.get("id", "")
        load_type = load.get("type", "").lower()

        if load_id == "water_heater" or load_type == "binary":
            # Migrate to water_heaters
            if "main_tank" in existing_water_ids:
                logger.debug("Water heater 'main_tank' already exists, skipping")
                continue

            has_water = system.get("has_water_heater", False)
            sensor_key = load.get("sensor_key", "water_power")
            sensor_entity = input_sensors.get(sensor_key, f"sensor.{sensor_key}")

            water_heater = {
                "id": "main_tank",
                "name": load.get("name", "Main Water Heater"),
                "enabled": has_water,
                "power_kw": load.get("nominal_power_kw", 3.0),
                "min_kwh_per_day": water_heating.get("min_kwh_per_day", 6.0),
                "max_hours_between_heating": water_heating.get("max_hours_between_heating", 8),
                "water_min_spacing_hours": water_heating.get("min_spacing_hours", 4),
                "sensor": sensor_entity,
                "type": load_type or "binary",
                "nominal_power_kw": load.get("nominal_power_kw", 3.0),
            }

            water_heaters.append(water_heater)
            existing_water_ids.add("main_tank")
            logger.info(
                "Migrated water heater from deferrable_loads: id=%s, enabled=%s, power=%.1fkW",
                water_heater["id"],
                water_heater["enabled"],
                water_heater["power_kw"],
            )
            changed = True

        elif load_id in ["ev_charger", "ev"] or load_type == "variable":
            # Migrate to ev_chargers
            if "main_ev" in existing_ev_ids:
                logger.debug("EV charger 'main_ev' already exists, skipping")
                continue

            has_ev = system.get("has_ev_charger", False)
            sensor_key = load.get("sensor_key", "ev_power")
            sensor_entity = input_sensors.get(sensor_key, f"sensor.{sensor_key}")

            ev_entry = {
                "id": "main_ev",
                "name": load.get("name", "EV Charger"),
                "enabled": has_ev,
                "max_power_kw": load.get("nominal_power_kw", 7.4),
                "battery_capacity_kwh": ev_charger.get("battery_capacity_kwh", 77.0),
                "min_soc_percent": 20.0,
                "target_soc_percent": 80.0,
                "sensor": sensor_entity,
                "type": load_type or "variable",
                "nominal_power_kw": load.get("nominal_power_kw", 7.4),
            }

            ev_chargers.append(ev_entry)
            existing_ev_ids.add("main_ev")
            logger.info(
                "Migrated EV charger from deferrable_loads: id=%s, enabled=%s, power=%.1fkW, capacity=%.1fkWh",
                ev_entry["id"],
                ev_entry["enabled"],
                ev_entry["max_power_kw"],
                ev_entry["battery_capacity_kwh"],
            )
            changed = True
        else:
            logger.warning("Unknown deferrable_load type: id=%s, type=%s", load_id, load_type)

    # REV F57: ACTUALLY DELETE deprecated keys (not just log intent)
    if "deferrable_loads" in config:
        del config["deferrable_loads"]
        logger.info("✂️  Deleted deprecated 'deferrable_loads' array")
        changed = True

    if "ev_charger" in config:
        del config["ev_charger"]
        logger.info("✂️  Deleted deprecated 'ev_charger' section")
        changed = True

    # Update config version
    if changed or water_heaters or ev_chargers:
        config["config_version"] = 2
        logger.info("Set config_version to 2 (ARC15 migration)")
        changed = True

    return config, changed


def cleanup_water_heating_duplicates(config: Any) -> tuple[Any, bool]:
    """
    Cleanup: Remove duplicate keys from water_heating that now exist in water_heaters[].

    These keys are per-device settings and should not be duplicated in the global section:
    - power_kw (now in water_heaters[].power_kw)
    - min_kwh_per_day (now in water_heaters[].min_kwh_per_day)
    - max_hours_between_heating (now in water_heaters[].max_hours_between_heating)
    - min_spacing_hours (different name in array: water_min_spacing_hours)
    """
    changed = False

    # Only cleanup if new array format exists
    if "water_heaters" not in config or not config.get("water_heaters", []):
        return config, changed

    water_heating = config.get("water_heating", {})
    if not water_heating:
        return config, changed

    # Keys to remove (they're now per-device in water_heaters[])
    duplicate_keys = [
        "power_kw",
        "min_kwh_per_day",
        "max_hours_between_heating",
        "min_spacing_hours",
    ]

    for key in duplicate_keys:
        if key in water_heating:
            water_heating.pop(key)
            logger.info(f"Removed duplicate key from water_heating: {key}")
            changed = True

    return config, changed


def _validate_config_structure(config: Any) -> bool:
    """
    Validates that the config has minimum expected structure.
    Prevents merging empty/corrupted configs with defaults.

    Returns True if config passes validation, False otherwise.
    """
    # Must have system section with key identifiers
    if not isinstance(config, dict):
        logger.error("Config is not a dictionary")
        return False

    system = config.get("system")
    if not isinstance(system, dict):
        logger.error("Config missing 'system' section")
        return False

    # Check for critical keys that indicate a valid user config
    # If these are missing, the config is likely empty/corrupted
    critical_keys = ["system_id", "inverter_profile", "has_solar", "has_battery"]
    missing_keys = [key for key in critical_keys if key not in system]

    if missing_keys:
        logger.error(f"Config missing critical keys in system section: {missing_keys}")
        return False

    # Additional check: verify location section exists (strong indicator of user config)
    location = system.get("location")
    if not isinstance(location, dict):
        logger.error("Config missing 'system.location' section")
        return False

    if "latitude" not in location or "longitude" not in location:
        logger.error("Config missing location coordinates")
        return False

    logger.debug("Config structure validation passed")
    return True


def validate_config_for_write(config: Any) -> bool:
    """Enhanced validation before writing config to disk.

    REV F57: Ensures no deprecated keys survive and structure is intact.

    Returns:
        True if config is safe to write, False otherwise.
    """
    if not isinstance(config, dict):
        logger.error("❌ Validation failed: Config is not a dictionary")
        return False

    # 1. Critical Sections
    required_sections = ["system", "battery", "executor", "input_sensors"]
    for section in required_sections:
        if section not in config:
            logger.error(f"❌ Validation failed: Missing required section '{section}'")
            return False

    # 2. Deprecated Keys (MUST be gone)
    for key in DEPRECATED_KEYS:
        if key in config:
            logger.error(f"❌ Validation failed: Deprecated key '{key}' still present")
            return False

    # 3. Version Position
    # config_version should be near the top
    keys = list(config.keys())
    if "config_version" in keys:
        idx = keys.index("config_version")
        if idx > 10:
            logger.error(f"❌ Validation failed: 'config_version' at index {idx} (too deep)")
            return False

    return True


def template_aware_merge(default_cfg: dict, user_cfg: dict) -> None:
    """
    Uses default_cfg as the BASE (template).
    Overwrites values from user_cfg.
    Appends extra keys from user_cfg (recursively).
    Modifies default_cfg IN PLACE.
    """

    def recursive_merge(target, source):
        # 1. Update/Recurse on existing keys
        for key, value in source.items():
            if key in target:
                if isinstance(target[key], dict) and isinstance(value, dict):
                    recursive_merge(target[key], value)
                else:
                    # Copy value. Structure/comments of 'target' remain.
                    target[key] = value
            else:
                # 2. Append new keys
                logger.info(f"Preserving custom user key '{key}'")
                target[key] = value

    recursive_merge(default_cfg, user_cfg)


def _extract_critical_values(config: Any) -> dict:
    """Extract critical user values that should never be lost."""
    if not isinstance(config, dict):
        return {}

    system = config.get("system", {})
    return {
        "inverter_profile": system.get("inverter_profile"),
        "has_ev_charger": system.get("has_ev_charger"),
        "has_water_heater": system.get("has_water_heater"),
        "latitude": system.get("location", {}).get("latitude"),
        "longitude": system.get("location", {}).get("longitude"),
        "solar_arrays_count": len(system.get("solar_arrays", [])),
        "min_soc": config.get("battery", {}).get("min_soc_percent"),
    }


def _validate_critical_values_preserved(before: dict, after: dict) -> bool:
    """
    Verify that critical user values were preserved during merge.
    Returns True if all values are preserved, False otherwise.
    """
    critical_keys = [
        "inverter_profile",
        "has_ev_charger",
        "has_water_heater",
        "latitude",
        "longitude",
        "solar_arrays_count",
        "min_soc",
    ]

    issues = []
    for key in critical_keys:
        before_val = before.get(key)
        after_val = after.get(key)

        # Skip if value was None before (not set)
        if before_val is None:
            continue

        # Check if value changed to a default
        if after_val != before_val:
            # Special case: allow solar_arrays_count to increase (adding default arrays)
            if key == "solar_arrays_count" and (after_val or 0) > (before_val or 0):
                continue
            issues.append(f"{key}: {before_val} -> {after_val}")

    if issues:
        logger.error(f"❌ CRITICAL VALUES LOST DURING MIGRATION: {', '.join(issues)}")
        return False

    return True


async def migrate_config(
    config_path: str = "config.yaml", default_path: str = "config.default.yaml"
) -> None:
    """
    Run all registered config migrations.
    Uses ruamel.yaml to preserve comments and structure.
    """
    path = Path(config_path)
    if not path.exists():
        logger.debug(f"Config file {config_path} not found, skipping migration")
        return

    if YAML is None:
        logger.warning(
            "ruamel.yaml not installed, skipping auto-migration. Please update config manually."
        )
        return

    # 1. Load User Config
    try:
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.width = 4096

        with path.open("r", encoding="utf-8") as f:
            user_config = yaml.load(f)

        if user_config is None or not isinstance(user_config, dict):
            logger.error(f"❌ Config {config_path} is invalid or empty.")
            return

        # SAFETY CHECK: Verify config has minimum expected structure
        # This prevents merging an empty/corrupted config with defaults
        if not _validate_config_structure(user_config):
            logger.error(
                f"❌ Config {config_path} failed structure validation. Aborting migration to prevent data loss."
            )
            return

    except Exception as e:
        logger.error(f"❌ Failed to read user config: {e}")
        return

    # 2. Run In-Place Legacy Migrations (Cleanup) on User Config
    # These prepare the user config to be merged cleanly
    pre_merge_changes = False

    # List of legacy cleanup steps
    legacy_steps = [
        migrate_version_key,  # REV F57: FIRST - Clean up old version key
        migrate_battery_config,
        cleanup_obsolete_keys,
        migrate_solar_arrays,
        migrate_soc_target_entity,
        migrate_inverter_profile_keys,
        migrate_arc15_entity_config,  # ARC15: Entity-centric config restructure
        cleanup_water_heating_duplicates,  # Cleanup: Remove duplicate keys from water_heating
    ]

    for step in legacy_steps:
        try:
            user_config, changed = step(user_config)
            if changed:
                pre_merge_changes = True
        except Exception as e:
            logger.error(f"❌ Legacy migration step {step.__name__} failed: {e}")

    # 3. Load Default Config (The Template)
    def_path_obj = Path(default_path)
    if not def_path_obj.exists():
        logger.warning(f"{default_path} not found. Skipping template merge.")
        # If we made legacy changes, save them at least.
        if pre_merge_changes:
            _write_config(path, user_config, yaml)
        return

    try:
        with def_path_obj.open("r", encoding="utf-8") as f:
            default_config = yaml.load(f)
    except Exception as e:
        logger.error(f"❌ Failed to read default config: {e}")
        if pre_merge_changes:
            _write_config(path, user_config, yaml)
        return

    # 4. Perform Template Merge
    # We use default_config as the base and fill it with user_config values
    try:
        # We need a deep copy of default structure to detect changes?
        # Actually, we can just assume we want to write the new structure
        # IF it differs from the original user_config structure.
        # But 'user_config' object structure is messy. 'default_config' is clean.
        # We ALWAYS want to write the clean structure if we are enforcing strict mode.
        # BUT we only want to write if actual values changed OR structure changed.
        # To simplify: We just write it. The IO cost is negligible on startup.
        # But for safety, let's look at the result.

        # We clone default_config to 'final_config' to be safe?
        # No, yaml.load() already gave us a fresh object.
        final_config = default_config

        # Sync Version explicitly
        if "version" in user_config:
            # Ensure version in final_config matches default (usually what we want)
            # OR matches user? Usually migration brings it UP to default version.
            pass

        # CAPTURE CRITICAL VALUES BEFORE MERGE
        critical_before = _extract_critical_values(user_config)
        logger.debug(f"Critical values before merge: {critical_before}")

        template_aware_merge(final_config, user_config)

        # REV F57: Final cleanup - remove any deprecated keys that survived
        final_config, cleanup_changed = remove_deprecated_keys(final_config)
        if cleanup_changed:
            logger.info("✅ Final deprecated keys cleanup successful")

        # VALIDATE CRITICAL VALUES AFTER MERGE
        critical_after = _extract_critical_values(final_config)
        logger.debug(f"Critical values after merge: {critical_after}")

        if not _validate_critical_values_preserved(critical_before, critical_after):
            logger.error("❌ CRITICAL CONFIG VALUES WOULD BE LOST! Aborting migration.")
            logger.error("This usually means the user config failed to load properly.")
            logger.error(f"Please check {config_path} for corruption or file locks.")
            return

        # 5. Save (Strict Enforcement)
        # We always save because we want to enforce the default structure/comments.
        # To avoid unnecessary writes, we could compare dumped strings, but
        # comment diffs make that hard. Let's just write safely.
        _write_config(path, final_config, yaml)

    except Exception as e:
        logger.error(f"❌ Template merge failed: {e}", exc_info=True)


def create_timestamped_backup(path: Path, max_backups: int = 30) -> Path | None:
    """Create a timestamped backup of the file and cleanup old ones.

    REV F57: Enhanced backup system for better recovery.

    Args:
        path: Path to the file to backup
        max_backups: Maximum number of backups to retain

    Returns:
        Path to the backup file or None if failed
    """
    if not path.exists():
        return None

    try:
        backup_dir = path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{path.name}_{timestamp}.bak"

        shutil.copy2(path, backup_path)
        logger.info(f"💾 Created timestamped backup: {backup_path.name}")

        # Retention logic
        backups = sorted(
            backup_dir.glob(f"{path.name}_*.bak"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if len(backups) > max_backups:
            for old_backup in backups[max_backups:]:
                old_backup.unlink()
                logger.info(f"🧹 Cleaned up old backup: {old_backup.name}")

        return backup_path
    except Exception as e:
        logger.error(f"❌ Failed to create backup: {e}")
        return None


def _write_config(path: Path, config: Any, yaml_instance: Any) -> None:
    """Safely write config with backup."""

    # SAFETY VALIDATION (REVISED Phase 4)
    if not validate_config_for_write(config):
        logger.error(f"❌ Aborting write to {path} - validation failed.")
        return

    temp_path = path.with_name(path.name + ".tmp")
    # REV F57: Legacy backup path (still used for atomic restore fallback)
    legacy_backup_path = path.with_name(path.name + ".bak")
    log_prefix = "[CONTAINER]" if Path("/.dockerenv").exists() else "[HOST]"

    try:
        # Create Timestamped Backup (Phase 3)
        if path.exists():
            create_timestamped_backup(path)
            # Still keep legacy .bak for atomic fallback logic below
            shutil.copy2(path, legacy_backup_path)

        logger.info(f"{log_prefix} Writing updated config to {temp_path}")
        with temp_path.open("w", encoding="utf-8") as f:
            yaml_instance.dump(config, f)

        # Atomic Replace
        try:
            temp_path.replace(path)
            logger.info(f"✅ {log_prefix} Successfully updated {path} (Atomic)")
            # Cleanup backup if successful?
            # Maybe keep it for one cycle? No, usually cleanup.
            # but let's keep .bak for safety in beta.
        except OSError as e:
            # Fallback for Bind Mounts (same as before)
            import errno

            if e.errno in (errno.EBUSY, errno.EXDEV, errno.ETXTBSY):
                logger.info(f"{log_prefix} Bind mount detected, using direct write.")
                shutil.copy2(
                    temp_path, path
                )  # Python copy is not atomic but works across filesystems
                logger.info(f"✅ {log_prefix} Successfully updated {path} (Direct Copy)")
            else:
                raise

    except Exception as e:
        logger.error(f"❌ Write failed: {e}")
        # Restore backup
        if legacy_backup_path.exists():
            logger.warning(f"🔄 Restoring {path} from legacy backup...")
            shutil.copy2(legacy_backup_path, path)
    finally:
        with contextlib.suppress(Exception):
            if temp_path.exists():
                temp_path.unlink()


if __name__ == "__main__":
    import asyncio

    # Setup basic logging for standalone run
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    asyncio.run(migrate_config())
