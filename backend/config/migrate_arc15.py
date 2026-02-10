"""
ARC15 Configuration Migration Script

Migrates from old deferrable_loads format to new entity-centric structure.
This script is idempotent - safe to run multiple times.
"""

import logging
from datetime import datetime
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Target config version for ARC15
TARGET_CONFIG_VERSION = 2


def detect_old_format(config: dict) -> bool:
    """
    Detect if config is in old format (before ARC15).

    Returns True if migration is needed.
    """
    # Check explicit version
    current_version = config.get("config_version", 1)
    if current_version >= TARGET_CONFIG_VERSION:
        logger.debug("Config is already at version %d or higher", TARGET_CONFIG_VERSION)
        return False

    # Check for old format indicators
    has_deferrable_loads = "deferrable_loads" in config
    has_old_water_heater = config.get("system", {}).get("has_water_heater", False)
    has_old_ev_charger = config.get("system", {}).get("has_ev_charger", False)

    # If deferrable_loads exists or we're missing the new arrays, migration needed
    missing_new_arrays = "water_heaters" not in config or "ev_chargers" not in config

    needs_migration = has_deferrable_loads or missing_new_arrays

    if needs_migration:
        logger.info(
            "Old format detected: deferrable_loads=%s, has_water_heater=%s, "
            "has_ev_charger=%s, missing_new_arrays=%s",
            has_deferrable_loads,
            has_old_water_heater,
            has_old_ev_charger,
            missing_new_arrays,
        )

    return needs_migration


def migrate_water_heater(old_config: dict) -> list[dict]:
    """
    Migrate water heater from old format to new water_heaters array.

    Returns list of water heater dicts (usually just one).
    """
    water_heaters = []

    # Check if we have deferrable_loads with water_heater entry
    deferrable_loads = old_config.get("deferrable_loads", [])
    water_heating_config = old_config.get("water_heating", {})
    input_sensors = old_config.get("input_sensors", {})

    # Try to find water heater in deferrable_loads
    water_load_def = None
    for load in deferrable_loads:
        if load.get("id") == "water_heater":
            water_load_def = load
            break

    # Also check if system.has_water_heater is enabled
    has_water_heater = old_config.get("system", {}).get("has_water_heater", False)

    if not has_water_heater and not water_load_def:
        logger.debug("No water heater configured in old format")
        return water_heaters

    # Build new water heater entry
    water_heater = {
        "id": "main_tank",
        "name": "Main Water Heater",
        "enabled": has_water_heater,
    }

    # Map power rating
    if water_load_def:
        water_heater["power_kw"] = water_load_def.get("nominal_power_kw", 3.0)
        water_heater["nominal_power_kw"] = water_load_def.get("nominal_power_kw", 3.0)
        water_heater["type"] = water_load_def.get("type", "binary")
    else:
        # Use defaults from water_heating section
        water_heater["power_kw"] = water_heating_config.get("power_kw", 3.0)
        water_heater["nominal_power_kw"] = water_heating_config.get("power_kw", 3.0)
        water_heater["type"] = "binary"

    # Map sensor
    if water_load_def and "sensor_key" in water_load_def:
        sensor_key = water_load_def["sensor_key"]
        sensor_entity = input_sensors.get(sensor_key, "")
        if sensor_entity:
            water_heater["sensor"] = sensor_entity
        else:
            # Use default sensor name
            water_heater["sensor"] = "sensor.vvb_power"
    else:
        water_heater["sensor"] = input_sensors.get("water_power", "sensor.vvb_power")

    # Map water heating parameters
    water_heater["min_kwh_per_day"] = water_heating_config.get("min_kwh_per_day", 6.0)
    water_heater["max_hours_between_heating"] = water_heating_config.get(
        "max_hours_between_heating", 8
    )
    water_heater["water_min_spacing_hours"] = water_heating_config.get("min_spacing_hours", 4)

    water_heaters.append(water_heater)
    logger.info(
        "Migrated water heater: id=%s, enabled=%s, power=%.1fkW",
        water_heater["id"],
        water_heater["enabled"],
        water_heater["power_kw"],
    )

    return water_heaters


def migrate_ev_charger(old_config: dict) -> list[dict]:
    """
    Migrate EV charger from old format to new ev_chargers array.

    Returns list of EV charger dicts (usually just one).
    """
    ev_chargers = []

    # Check if we have deferrable_loads with ev_charger entry
    deferrable_loads = old_config.get("deferrable_loads", [])
    ev_charger_config = old_config.get("ev_charger", {})
    input_sensors = old_config.get("input_sensors", {})

    # Try to find EV charger in deferrable_loads
    ev_load_def = None
    for load in deferrable_loads:
        if load.get("id") in ["ev_charger", "ev"]:
            ev_load_def = load
            break

    # Also check if system.has_ev_charger is enabled
    has_ev_charger = old_config.get("system", {}).get("has_ev_charger", False)

    if not has_ev_charger and not ev_load_def:
        logger.debug("No EV charger configured in old format")
        return ev_chargers

    # Build new EV charger entry
    ev_charger = {
        "id": "main_ev",
        "name": "EV Charger",
        "enabled": has_ev_charger,
    }

    # Map power and capacity
    if ev_load_def:
        ev_charger["max_power_kw"] = ev_load_def.get("nominal_power_kw", 7.4)
        ev_charger["nominal_power_kw"] = ev_load_def.get("nominal_power_kw", 7.4)
        ev_charger["type"] = ev_load_def.get("type", "variable")
    else:
        # Use defaults from ev_charger section
        ev_charger["max_power_kw"] = ev_charger_config.get("max_power_kw", 7.4)
        ev_charger["nominal_power_kw"] = ev_charger_config.get("max_power_kw", 7.4)
        ev_charger["type"] = "variable"

    ev_charger["battery_capacity_kwh"] = ev_charger_config.get("battery_capacity_kwh", 77.0)
    ev_charger["min_soc_percent"] = 20.0
    ev_charger["target_soc_percent"] = 80.0

    # Map sensor
    if ev_load_def and "sensor_key" in ev_load_def:
        sensor_key = ev_load_def["sensor_key"]
        sensor_entity = input_sensors.get(sensor_key, "")
        if sensor_entity:
            ev_charger["sensor"] = sensor_entity
        else:
            ev_charger["sensor"] = "sensor.ev_power"
    else:
        ev_charger["sensor"] = input_sensors.get("ev_power", "sensor.ev_power")

    ev_chargers.append(ev_charger)
    logger.info(
        "Migrated EV charger: id=%s, enabled=%s, power=%.1fkW, capacity=%.1fkWh",
        ev_charger["id"],
        ev_charger["enabled"],
        ev_charger["max_power_kw"],
        ev_charger["battery_capacity_kwh"],
    )

    return ev_chargers


def create_config_backup(config_path: Path) -> Path | None:
    """
    Create a backup of the config file before migration.

    Returns path to backup file or None if failed.
    """
    if not config_path.exists():
        logger.warning("Config file not found: %s", config_path)
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = config_path.parent / f"{config_path.name}.backup.{timestamp}"

    try:
        import shutil

        shutil.copy2(config_path, backup_path)
        logger.info("Created config backup: %s", backup_path)
        return backup_path
    except Exception as e:
        logger.error("Failed to create backup: %s", e)
        return None


def validate_migrated_config(config: dict) -> list[str]:
    """
    Validate the migrated configuration.

    Returns list of validation errors (empty if valid).
    """
    errors = []

    # Check required root fields
    if "config_version" not in config:
        errors.append("Missing config_version field")
    elif config["config_version"] != TARGET_CONFIG_VERSION:
        errors.append(f"Invalid config_version: {config['config_version']}")

    # Validate water_heaters array
    water_heaters = config.get("water_heaters", [])
    if not isinstance(water_heaters, list):
        errors.append("water_heaters must be a list")
    else:
        # Check for duplicate IDs
        ids = [wh.get("id") for wh in water_heaters if wh.get("id")]
        if len(ids) != len(set(ids)):
            errors.append("Duplicate IDs found in water_heaters")

        # Validate each water heater
        for i, wh in enumerate(water_heaters):
            prefix = f"water_heaters[{i}]"
            if "id" not in wh:
                errors.append(f"{prefix}: missing required field 'id'")
            if "name" not in wh:
                errors.append(f"{prefix}: missing required field 'name'")
            if "power_kw" not in wh:
                errors.append(f"{prefix}: missing required field 'power_kw'")
            elif wh.get("power_kw", 0) <= 0:
                errors.append(f"{prefix}: power_kw must be positive")

    # Validate ev_chargers array
    ev_chargers = config.get("ev_chargers", [])
    if not isinstance(ev_chargers, list):
        errors.append("ev_chargers must be a list")
    else:
        # Check for duplicate IDs
        ids = [ev.get("id") for ev in ev_chargers if ev.get("id")]
        if len(ids) != len(set(ids)):
            errors.append("Duplicate IDs found in ev_chargers")

        # Validate each EV charger
        for i, ev in enumerate(ev_chargers):
            prefix = f"ev_chargers[{i}]"
            if "id" not in ev:
                errors.append(f"{prefix}: missing required field 'id'")
            if "name" not in ev:
                errors.append(f"{prefix}: missing required field 'name'")
            if "max_power_kw" not in ev:
                errors.append(f"{prefix}: missing required field 'max_power_kw'")
            elif ev.get("max_power_kw", 0) <= 0:
                errors.append(f"{prefix}: max_power_kw must be positive")

    return errors


def migrate_to_arc15(old_config: dict) -> dict:
    """
    Migrate configuration from old format to ARC15 entity-centric format.

    This function is idempotent - safe to call multiple times.

    Args:
        old_config: The old configuration dictionary

    Returns:
        New configuration dictionary in ARC15 format
    """
    logger.info("Starting ARC15 configuration migration")

    # Create a deep copy to avoid modifying the original
    import copy

    new_config = copy.deepcopy(old_config)

    # Check if migration is needed
    if not detect_old_format(old_config):
        logger.info("No migration needed - config is already in ARC15 format")
        return new_config

    # Migrate water heaters
    if "water_heaters" not in new_config:
        new_config["water_heaters"] = migrate_water_heater(old_config)
        logger.info("Created water_heaters array with %d entries", len(new_config["water_heaters"]))
    else:
        logger.debug("water_heaters array already exists, skipping migration")

    # Migrate EV chargers
    if "ev_chargers" not in new_config:
        new_config["ev_chargers"] = migrate_ev_charger(old_config)
        logger.info("Created ev_chargers array with %d entries", len(new_config["ev_chargers"]))
    else:
        logger.debug("ev_chargers array already exists, skipping migration")

    # Update config version
    new_config["config_version"] = TARGET_CONFIG_VERSION
    logger.info("Set config_version to %d", TARGET_CONFIG_VERSION)

    # Note: We keep the old deferrable_loads section for reference,
    # but it's marked as deprecated in the YAML comments

    # Validate the migrated config
    validation_errors = validate_migrated_config(new_config)
    if validation_errors:
        logger.error("Migration validation failed:")
        for error in validation_errors:
            logger.error("  - %s", error)
        raise ValueError(f"Migration validation failed: {validation_errors}")

    logger.info("ARC15 migration completed successfully")
    return new_config


def run_migration(config_path: str | Path) -> dict:
    """
    Run the full migration process on a config file.

    This includes:
    1. Loading the config
    2. Creating a backup
    3. Running migration
    4. Validating result
    5. Saving the migrated config

    Args:
        config_path: Path to the config.yaml file

    Returns:
        The migrated configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If migration validation fails
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    logger.info("Running ARC15 migration on: %s", config_path)

    # Load current config
    with config_path.open() as f:
        old_config = yaml.safe_load(f)

    # Check if migration is needed
    if not detect_old_format(old_config):
        logger.info("No migration needed for: %s", config_path)
        return old_config

    # Create backup
    backup_path = create_config_backup(config_path)
    if not backup_path:
        logger.warning("Failed to create backup, proceeding without backup")

    # Run migration
    try:
        new_config = migrate_to_arc15(old_config)
    except Exception as e:
        logger.error("Migration failed: %s", e)
        raise

    # Save migrated config
    try:
        with config_path.open("w") as f:
            yaml.dump(new_config, f, default_flow_style=False, sort_keys=False)
        logger.info("Saved migrated config to: %s", config_path)
    except Exception as e:
        logger.error("Failed to save migrated config: %s", e)
        raise

    return new_config


if __name__ == "__main__":
    # Standalone execution for testing
    logging.basicConfig(level=logging.INFO)

    import sys

    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"

    try:
        new_config = run_migration(config_file)
        print(f"Migration successful! Config version: {new_config.get('config_version')}")
        print(f"Water heaters: {len(new_config.get('water_heaters', []))}")
        print(f"EV chargers: {len(new_config.get('ev_chargers', []))}")
    except Exception as e:
        print(f"Migration failed: {e}", file=sys.stderr)
        sys.exit(1)
