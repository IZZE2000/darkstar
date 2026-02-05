import contextlib
import logging
import shutil
from collections.abc import Callable
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

    return config, changed


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

    except Exception as e:
        logger.error(f"❌ Failed to read user config: {e}")
        return

    # 2. Run In-Place Legacy Migrations (Cleanup) on User Config
    # These prepare the user config to be merged cleanly
    pre_merge_changes = False

    # List of legacy cleanup steps
    legacy_steps = [migrate_battery_config, cleanup_obsolete_keys, migrate_solar_arrays]

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

        template_aware_merge(final_config, user_config)

        # 5. Save (Strict Enforcement)
        # We always save because we want to enforce the default structure/comments.
        # To avoid unnecessary writes, we could compare dumped strings, but
        # comment diffs make that hard. Let's just write safely.
        _write_config(path, final_config, yaml)

    except Exception as e:
        logger.error(f"❌ Template merge failed: {e}", exc_info=True)


def _write_config(path: Path, config: Any, yaml_instance: Any) -> None:
    """Safely write config with backup."""

    # SAFETY VALIDATION
    if not isinstance(config, dict):
        logger.error("❌ Invalid config structure. Aborting write.")
        return

    temp_path = path.with_name(path.name + ".tmp")
    backup_path = path.with_name(path.name + ".bak")
    log_prefix = "[CONTAINER]" if Path("/.dockerenv").exists() else "[HOST]"

    try:
        # Create Backup
        if path.exists():
            shutil.copy2(path, backup_path)

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
        if backup_path.exists():
            logger.warning(f"🔄 Restoring {path} from backup...")
            shutil.copy2(backup_path, path)
    finally:
        with contextlib.suppress(Exception):
            if temp_path.exists():
                temp_path.unlink()


if __name__ == "__main__":
    import asyncio

    # Setup basic logging for standalone run
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    asyncio.run(migrate_config())
