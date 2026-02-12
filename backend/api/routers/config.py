import logging
import re
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, Body, HTTPException
from ruamel.yaml import YAML

from backend.api.routers.executor import get_executor_instance
from backend.config_migration import (
    remove_deprecated_keys,
    template_aware_merge,
)
from executor.profiles import get_profile_from_config
from inputs import load_home_assistant_config, load_notifications_config, load_yaml

logger = logging.getLogger("darkstar.api.config")

router = APIRouter(tags=["config"])


@router.get(
    "/api/config",
    summary="Get System Configuration",
    description="Returns sanitized configuration with secrets redacted.",
)
async def get_config() -> dict[str, Any]:
    """Get sanitized config."""
    try:
        conf: dict[str, Any] = load_yaml("config.yaml") or {}

        # Merge Home Assistant secrets
        ha_secrets = load_home_assistant_config()
        if ha_secrets:
            if "home_assistant" not in conf:
                conf["home_assistant"] = {}
            # Update only keys that exist in secrets (overwriting config.yaml placeholders)
            cast("dict[str, Any]", conf["home_assistant"]).update(ha_secrets)

        # Merge Notification secrets
        notif_secrets = load_notifications_config()
        if notif_secrets:
            if "notifications" not in conf:
                conf["notifications"] = {}
            cast("dict[str, Any]", conf["notifications"]).update(notif_secrets)

        # Sanitize secrets before returning
        if "home_assistant" in conf:
            cast("dict[str, Any]", conf["home_assistant"]).pop("token", None)
        if "notifications" in conf:
            for key in ["api_key", "token", "password", "webhook_url"]:
                cast("dict[str, Any]", conf.get("notifications", {})).pop(key, None)

        return conf
    except Exception as e:
        return {"error": str(e)}


@router.post(
    "/api/config/save",
    summary="Save Configuration",
    description="Updates config.yaml with new values.",
)
async def save_config(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Save config.yaml."""
    try:
        yaml_handler = YAML()
        yaml_handler.preserve_quotes = True
        yaml_handler.width = 4096  # Prevent wrapping of long entity IDs (REV F16)

        # We might want to merge payload into existing to preserve comments?
        # Or just dump. webapp.py usually did a load-update-dump cycle using ruamel.
        # EXCLUSION FILTER: Ensure secrets from secrets.yaml never leak into config.yaml
        # These keys should only live in secrets.yaml
        SECRET_KEYS = {
            "home_assistant": {"token"},
            "notifications": {"api_key", "token", "password", "webhook_url", "discord_webhook_url"},
            "openrouter_api_key": None,
        }

        def filter_secrets(overrides: dict[str, Any], exclusions: dict[str, Any] | None) -> None:
            """Recursively remove keys that are marked as secrets from the payload."""
            if exclusions is None:
                return

            for key in list(overrides.keys()):
                if key in exclusions:
                    excl_val = exclusions[key]
                    if excl_val is None:
                        logger.warning(
                            f"Security: Stripped sensitive block '{key}' from config save."
                        )
                        overrides.pop(key)
                    elif isinstance(overrides[key], dict):
                        if isinstance(excl_val, set):
                            for subkey in list(overrides[key].keys()):
                                if subkey in excl_val:
                                    logger.warning(
                                        f"Security: Stripped sensitive sub-key '{key}.{subkey}' from config save."
                                    )
                                    overrides[key].pop(subkey)
                        elif isinstance(excl_val, dict):
                            filter_secrets(overrides[key], excl_val)

                        if not overrides[key]:
                            overrides.pop(key)

        # Deep merge helper - FIXED to preserve YAML structure and coerce types
        def deep_update(
            source: dict[str, Any],
            overrides: dict[str, Any],
            schema: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            """Recursively merge overrides into source, preserving structure and types."""
            for key, value in overrides.items():
                # Get expected type from schema if available
                expected_val = schema.get(key) if schema else None

                if isinstance(value, dict) and value:
                    # Ensure parent key exists as dict before merging
                    if key not in source:
                        source[key] = {}
                    elif not isinstance(source[key], dict):
                        logger.warning(f"Config key '{key}' exists but isn't a dict - replacing")
                        source[key] = {}

                    # Recursively merge the nested dict, passing sub-schema
                    sub_schema = expected_val if isinstance(expected_val, dict) else None
                    deep_update(source[key], value, sub_schema)
                else:
                    # Type Coercion Logic
                    coerced_value = value
                    if expected_val is not None and value is not None:
                        try:
                            if isinstance(expected_val, bool) and not isinstance(value, bool):
                                if str(value).lower() in ("true", "1", "yes"):
                                    coerced_value = True
                                elif str(value).lower() in ("false", "0", "no"):
                                    coerced_value = False
                            elif isinstance(expected_val, int) and not isinstance(value, int):
                                coerced_value = int(float(value))
                            elif isinstance(expected_val, float) and not isinstance(
                                value, int | float
                            ):
                                coerced_value = float(value)
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Failed to coerce '{key}': {value} -> {type(expected_val)}"
                            )

                    source[key] = coerced_value
            return source

        config_path = Path("config.yaml")
        default_path = Path("config.default.yaml")

        # REV F57: ALWAYS start with fresh template (preserves structure/comments)
        if not default_path.exists():
            raise HTTPException(500, "config.default.yaml not found")

        # Load template as base (has all comments and structure)
        with default_path.open(encoding="utf-8") as df:
            template_config = cast("dict[str, Any]", yaml_handler.load(df) or {})

        # Load user config for current values
        with config_path.open(encoding="utf-8") as f:
            user_data = cast("dict[str, Any]", yaml_handler.load(f) or {})

        # Filter secrets before merging
        filter_secrets(payload, SECRET_KEYS)

        # Merge payload into user data first
        # We use template_config as schema for type coercion
        deep_update(user_data, payload, template_config)

        # Then merge user values into fresh template (preserves template structure)
        template_aware_merge(template_config, user_data)

        # Clean deprecated keys
        template_config, cleanup_changed = remove_deprecated_keys(template_config)
        if cleanup_changed:
            logger.info("Backend save: Removed deprecated keys")

        # template_config now has: template structure + comments + user values
        data = template_config

        # REV LCL01: Validate config before saving and collect warnings/errors
        validation_issues = _validate_config_for_save(data)
        errors = [i for i in validation_issues if i["severity"] == "error"]
        warnings = [i for i in validation_issues if i["severity"] == "warning"]

        # If there are critical errors, reject the save
        if errors:
            raise HTTPException(
                400,
                detail={
                    "message": "Configuration has critical errors",
                    "errors": errors,
                    "warnings": warnings,
                },
            )

        # Save the config (even if warnings exist)
        with config_path.open("w", encoding="utf-8") as f:
            yaml_handler.dump(data, f)  # type: ignore

        # REV F53: Notify executor to reload config after successful save
        try:
            executor = get_executor_instance()
            if executor is not None:
                executor.reload_config()
                logger.info("Executor configuration reloaded after config save")
        except Exception as e:
            # Log but don't fail the save if executor reload fails
            logger.warning("Failed to reload executor config after save: %s", e)

        # Return success with any warnings
        if warnings:
            return {"status": "success", "warnings": warnings}  # type: ignore[return-value]
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e)) from e


def _validate_config_for_save(config: dict[str, Any]) -> list[dict[str, str]]:
    """Validate config and return list of issues.

    REV LCL01: Run on every config save to catch misconfigurations immediately.
    ARC15: Added validation for water_heaters[] and ev_chargers[] arrays.
    Returns list of {"severity": "error"|"warning", "message": str, "guidance": str}
    """
    issues: list[dict[str, str]] = []
    system_cfg = config.get("system", {})
    water_cfg = config.get("water_heating", {})
    battery_cfg = config.get("battery", {})
    config_version = config.get("config_version", 1)

    # Battery: ERROR if enabled but no capacity (breaks MILP solver)
    if system_cfg.get("has_battery", True):
        try:
            capacity = float(battery_cfg.get("capacity_kwh", 0) or 0)
        except (ValueError, TypeError):
            capacity = 0.0
        if capacity <= 0:
            issues.append(
                {
                    "severity": "error",
                    "message": "Battery enabled but capacity not configured",
                    "guidance": "Set battery.capacity_kwh to your battery's capacity, "
                    "or set system.has_battery to false.",
                }
            )

    # Water heater: WARNING (feature disabled, system still works)
    # ARC15: Also validate new water_heaters[] array format
    if system_cfg.get("has_water_heater", True):
        water_heaters = config.get("water_heaters", [])

        if config_version >= 2 and water_heaters:
            # Validate new array format
            existing_ids = set()
            for i, wh in enumerate(water_heaters):
                # Check for required fields
                if not wh.get("id"):
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"Water heater {i + 1} is missing required field 'id'",
                            "guidance": "Each water heater must have a unique 'id' field (e.g., 'main_tank').",
                        }
                    )
                elif wh["id"] in existing_ids:
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"Duplicate water heater ID: '{wh['id']}'",
                            "guidance": "Each water heater must have a unique ID.",
                        }
                    )
                else:
                    existing_ids.add(wh["id"])

                if not wh.get("name"):
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"Water heater '{wh.get('id', i + 1)}' is missing required field 'name'",
                            "guidance": "Each water heater must have a display name.",
                        }
                    )

                # Validate power values are positive
                power_kw = wh.get("power_kw", 0)
                if not isinstance(power_kw, int | float) or power_kw <= 0:
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"Water heater '{wh.get('id', i + 1)}' has invalid power_kw: {power_kw}",
                            "guidance": "power_kw must be a positive number (e.g., 3.0).",
                        }
                    )

                # Validate sensor format
                sensor = wh.get("sensor", "")
                if sensor and not sensor.startswith("sensor."):
                    issues.append(
                        {
                            "severity": "warning",
                            "message": f"Water heater '{wh.get('id', i + 1)}' sensor may be invalid: {sensor}",
                            "guidance": "Sensors should be valid Home Assistant entity IDs (e.g., 'sensor.vvb_power').",
                        }
                    )

            # Check if at least one water heater is enabled
            if not any(wh.get("enabled", True) for wh in water_heaters):
                issues.append(
                    {
                        "severity": "warning",
                        "message": "All water heaters are disabled",
                        "guidance": "Enable at least one water heater or set system.has_water_heater to false.",
                    }
                )
        else:
            # Legacy validation for config_version < 2
            try:
                power_kw = float(water_cfg.get("power_kw", 0) or 0)
            except (ValueError, TypeError):
                power_kw = 0.0
            if power_kw <= 0:
                issues.append(
                    {
                        "severity": "warning",
                        "message": "Water heater enabled but power not configured",
                        "guidance": "Set water_heating.power_kw to your heater's power (e.g., 3.0), "
                        "or set system.has_water_heater to false.",
                    }
                )

    # EV Charger: WARNING (feature disabled, system still works)
    # ARC15: Validate new ev_chargers[] array format
    if system_cfg.get("has_ev_charger", False):
        ev_chargers = config.get("ev_chargers", [])

        if config_version >= 2 and ev_chargers:
            # Validate new array format
            existing_ev_ids = set()
            for i, ev in enumerate(ev_chargers):
                # Check for required fields
                if not ev.get("id"):
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"EV charger {i + 1} is missing required field 'id'",
                            "guidance": "Each EV charger must have a unique 'id' field (e.g., 'main_ev').",
                        }
                    )
                elif ev["id"] in existing_ev_ids:
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"Duplicate EV charger ID: '{ev['id']}'",
                            "guidance": "Each EV charger must have a unique ID.",
                        }
                    )
                else:
                    existing_ev_ids.add(ev["id"])

                if not ev.get("name"):
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"EV charger '{ev.get('id', i + 1)}' is missing required field 'name'",
                            "guidance": "Each EV charger must have a display name.",
                        }
                    )

                # Validate power values are positive
                max_power_kw = ev.get("max_power_kw", 0)
                if not isinstance(max_power_kw, int | float) or max_power_kw <= 0:
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"EV charger '{ev.get('id', i + 1)}' has invalid max_power_kw: {max_power_kw}",
                            "guidance": "max_power_kw must be a positive number (e.g., 11.0).",
                        }
                    )

                # Validate battery capacity
                capacity = ev.get("battery_capacity_kwh", 0)
                if not isinstance(capacity, int | float) or capacity <= 0:
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"EV charger '{ev.get('id', i + 1)}' has invalid battery_capacity_kwh: {capacity}",
                            "guidance": "battery_capacity_kwh must be a positive number (e.g., 82.0).",
                        }
                    )

                # Validate SoC percentages
                min_soc = ev.get("min_soc_percent", 0)
                if not isinstance(min_soc, int | float) or min_soc < 0 or min_soc > 100:
                    issues.append(
                        {
                            "severity": "warning",
                            "message": f"EV charger '{ev.get('id', i + 1)}' has invalid min_soc_percent: {min_soc}",
                            "guidance": "min_soc_percent must be between 0 and 100.",
                        }
                    )

                target_soc = ev.get("target_soc_percent", 0)
                if not isinstance(target_soc, int | float) or target_soc < 0 or target_soc > 100:
                    issues.append(
                        {
                            "severity": "warning",
                            "message": f"EV charger '{ev.get('id', i + 1)}' has invalid target_soc_percent: {target_soc}",
                            "guidance": "target_soc_percent must be between 0 and 100.",
                        }
                    )

                # Validate sensor format
                sensor = ev.get("sensor", "")
                if sensor and not sensor.startswith("sensor."):
                    issues.append(
                        {
                            "severity": "warning",
                            "message": f"EV charger '{ev.get('id', i + 1)}' sensor may be invalid: {sensor}",
                            "guidance": "Sensors should be valid Home Assistant entity IDs (e.g., 'sensor.tesla_power').",
                        }
                    )

            # Check if at least one EV charger is enabled
            if not any(ev.get("enabled", True) for ev in ev_chargers):
                issues.append(
                    {
                        "severity": "warning",
                        "message": "All EV chargers are disabled",
                        "guidance": "Enable at least one EV charger or set system.has_ev_charger to false.",
                    }
                )

    # Solar: WARNING (PV forecasts will be zero)
    if system_cfg.get("has_solar", True):
        # REV F60 Phase 9: Validate location coordinates
        location = system_cfg.get("location", {})
        latitude = location.get("latitude")
        longitude = location.get("longitude")

        if latitude is None or longitude is None:
            issues.append(
                {
                    "severity": "error",
                    "message": "Solar enabled but location not configured",
                    "guidance": "Set system.location.latitude and system.location.longitude for PV forecasting.",
                }
            )
        else:
            try:
                lat_val = float(latitude)
                lon_val = float(longitude)
                if not (-90 <= lat_val <= 90):
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"Invalid latitude: {latitude}",
                            "guidance": "Latitude must be between -90 and 90 degrees.",
                        }
                    )
                if not (-180 <= lon_val <= 180):
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"Invalid longitude: {longitude}",
                            "guidance": "Longitude must be between -180 and 180 degrees.",
                        }
                    )
            except (ValueError, TypeError):
                issues.append(
                    {
                        "severity": "error",
                        "message": "Location coordinates must be numeric",
                        "guidance": "Check system.location.latitude and system.location.longitude values.",
                    }
                )

        solar_arrays = system_cfg.get("solar_arrays", [])
        if not isinstance(solar_arrays, list):
            issues.append(
                {
                    "severity": "error",
                    "message": "system.solar_arrays must be a list",
                    "guidance": "Check your config.yaml structure.",
                }
            )
        elif not solar_arrays:
            issues.append(
                {
                    "severity": "warning",
                    "message": "Solar enabled but no arrays configured",
                    "guidance": "Add at least one array to system.solar_arrays, "
                    "or set system.has_solar to false.",
                }
            )
        elif len(solar_arrays) > 6:
            issues.append(
                {
                    "severity": "error",
                    "message": "Too many solar arrays (max 6)",
                    "guidance": "Darkstar supports up to 6 PV arrays.",
                }
            )
        else:
            total_kwp = 0.0
            # REV F60 Phase 9: Track duplicate array names
            array_names: set[str] = set()

            for i, array in enumerate(solar_arrays):
                # Check for duplicate names
                array_name = array.get("name", f"Array {i + 1}")
                if array_name in array_names:
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"Duplicate solar array name: '{array_name}'",
                            "guidance": "Each solar array must have a unique name.",
                        }
                    )
                else:
                    array_names.add(array_name)

                # Check for invalid characters in name
                if not re.match(r"^[\w\s\-\.]", array_name):
                    issues.append(
                        {
                            "severity": "warning",
                            "message": f"Array {i + 1} name contains special characters: '{array_name}'",
                            "guidance": "Use only letters, numbers, spaces, hyphens, and periods in array names.",
                        }
                    )

                kwp = float(array.get("kwp", 0) or 0)
                total_kwp += kwp
                if kwp <= 0:
                    issues.append(
                        {
                            "severity": "warning",
                            "message": f"Solar array {i + 1} ('{array_name}') has no capacity",
                            "guidance": "Set kwp for each PV array.",
                        }
                    )
                if kwp > 50:
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"Solar array {i + 1} exceeds max capacity (50kWp)",
                            "guidance": "Individual arrays are capped at 50kWp for forecasting accuracy.",
                        }
                    )

                # Azimuth/Tilt range checks
                tilt = float(array.get("tilt", 0) or 0)
                if tilt < 0 or tilt > 90:
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"Array {i + 1} tilt must be 0-90°",
                            "guidance": "Check solar_arrays configuration.",
                        }
                    )

                # REV F60: Add azimuth validation
                azimuth = float(array.get("azimuth", 0) or 0)
                if azimuth < 0 or azimuth > 360:
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"Array {i + 1} azimuth must be 0-360°",
                            "guidance": "0° = North, 90° = East, 180° = South, 270° = West.",
                        }
                    )

            if total_kwp > 500:
                issues.append(
                    {
                        "severity": "error",
                        "message": "Total PV capacity exceeds 500kWp",
                        "guidance": "Darkstar is optimized for residential systems.",
                    }
                )

    # Executor: Critical entities (ERROR)
    # REV IP2: Input validation is now Profile-Aware.
    # We ask the active profile which entities are strictly required.
    executor_cfg = config.get("executor", {})
    executor_enabled = executor_cfg.get("enabled", True)
    has_battery = system_cfg.get("has_battery", True)
    input_sensors = config.get("input_sensors", {})

    if executor_enabled and has_battery:
        try:
            active_profile = get_profile_from_config(config)

            # Check for missing required entities as defined by the profile
            missing_entities = active_profile.get_missing_entities(config)

            for missing_key in missing_entities:
                issues.append(
                    {
                        "severity": "error",
                        "message": f"Profile '{active_profile.metadata.name}' requires {missing_key} to be configured.",
                        "guidance": f"Please configure {missing_key} in the Settings - System tab.",
                    }
                )

            # Global Requirement: Battery SoC is always needed for battery operations
            if not input_sensors.get("battery_soc"):
                issues.append(
                    {
                        "severity": "error",
                        "message": "Executor requires input_sensors.battery_soc (Battery State of Charge).",
                        "guidance": "Please configure input_sensors.battery_soc in the Settings - System tab.",
                    }
                )

        except Exception as e:
            # Fallback if profile loading fails
            issues.append(
                {
                    "severity": "warning",
                    "message": f"Could not load inverter profile for validation: {e!s}",
                    "guidance": "Check system logs.",
                }
            )

    # Override Thresholds (WARNING)
    override_cfg = executor_cfg.get("override", {})
    low_soc_floor = override_cfg.get("low_soc_export_floor")
    if low_soc_floor is not None:
        try:
            val = float(low_soc_floor)
            if val < 0 or val > 100:
                issues.append(
                    {
                        "severity": "warning",
                        "message": "Export Prevention Floor should be between 0 and 100%.",
                        "guidance": "Check executor.override.low_soc_export_floor.",
                    }
                )
        except (ValueError, TypeError):
            issues.append(
                {
                    "severity": "error",
                    "message": "Export Prevention Floor must be a number.",
                    "guidance": "Set executor.override.low_soc_export_floor to a valid percentage.",
                }
            )

    excess_pv = override_cfg.get("excess_pv_threshold_kw")
    if excess_pv is not None:
        try:
            val = float(excess_pv)
            if val < 0:
                issues.append(
                    {
                        "severity": "warning",
                        "message": "Excess PV threshold cannot be negative.",
                        "guidance": "Check executor.override.excess_pv_threshold_kw.",
                    }
                )
        except (ValueError, TypeError):
            issues.append(
                {
                    "severity": "error",
                    "message": "Excess PV threshold must be a number.",
                    "guidance": "Set executor.override.excess_pv_threshold_kw to a valid kW value.",
                }
            )

    return issues


@router.post(
    "/api/config/reset",
    summary="Reset Configuration",
    description="Resets config.yaml to defaults.",
)
async def reset_config() -> dict[str, str]:
    """Reset to default config."""
    default_cfg = Path("config.default.yaml")
    if default_cfg.exists():
        import shutil

        shutil.copy(str(default_cfg), "config.yaml")
        return {"status": "success"}
    return {"status": "error", "message": "Default config not found"}


@router.post(
    "/api/aurora/config/toggle_error_correction",
    summary="Toggle Error Correction",
    description="Toggle ML error correction in config.",
)
async def toggle_error_correction(enabled: bool = Body(..., embed=True)):
    """Toggle error correction setting."""
    try:
        conf = load_yaml("config.yaml") or {}
        if "learning" not in conf:
            conf["learning"] = {}

        conf["learning"]["error_correction_enabled"] = enabled

        yaml_handler = YAML()
        yaml_handler.preserve_quotes = True
        with Path("config.yaml").open("w", encoding="utf-8") as f:
            yaml_handler.dump(conf, f)

        return {"status": "success", "enabled": enabled}
    except Exception as e:
        logger.exception("Failed to toggle error correction")
        raise HTTPException(status_code=500, detail=str(e)) from e
