"""
Inverter Profile System

Loads and validates inverter profiles from YAML files.
Enables Darkstar to support multiple inverter brands without code changes.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ProfileMetadata:
    """Profile identification and documentation."""

    name: str
    version: str
    description: str
    supported_brands: list[str] = field(default_factory=list)
    author: str = "Unknown"
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ProfileCapabilities:
    """Feature flags for inverter-specific capabilities."""

    # Control capabilities
    grid_charging_control: bool = True
    watts_based_control: bool = False
    service_call_mode: bool = False
    separate_grid_charging_switch: bool = True

    # Work mode capabilities
    supports_export_mode: bool = True
    supports_zero_export: bool = True
    supports_self_consumption: bool = True

    # Advanced features
    supports_soc_target: bool = True
    supports_grid_export_limit: bool = True
    supports_force_discharge: bool = False


@dataclass
class ProfileEntities:
    """Home Assistant entity mappings."""

    # Required entities
    required: dict[str, str | None] = field(default_factory=dict)

    # Optional entities
    optional: dict[str, str | None] = field(default_factory=dict)
    # forced_power_entity: str | None = None  # Planned for Rev IP2 Phase 3 (Keeping as dict entry for consistency)

    def validate_required(self) -> tuple[bool, list[str]]:
        """
        Validate that all required entities are configured.

        Returns:
            Tuple of (is_valid, missing_entities)
        """
        missing = []
        for key, value in self.required.items():
            if value is None or value == "":
                missing.append(key)

        return len(missing) == 0, missing


@dataclass
class WorkMode:
    """Work mode definition with value and description."""

    value: str | None
    description: str = ""
    requires_grid_charging: bool = False  # Whether this mode needs grid_charging_entity=ON
    skip_discharge_limit: bool = False  # Explicitly skip writing discharge limit in this mode
    skip_export_power: bool = False  # Explicitly skip writing export power limit in this mode
    # Composite mode settings (Rev IP2)
    # Maps profile entity key -> value to set
    set_entities: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProfileModes:
    """Work mode translations for the inverter."""

    export: WorkMode | None = None
    zero_export: WorkMode | None = None
    self_consumption: WorkMode | None = None
    charge_from_grid: WorkMode | None = None  # Grid charging mode
    force_discharge: WorkMode | None = None  # Force discharge mode
    idle: WorkMode | None = None  # Idle/standby mode


@dataclass
class ProfileBehavior:
    """Inverter-specific behavioral parameters."""

    # Control unit settings
    control_unit: str | None = "A"  # "A" or "W"

    # Ampere-based control limits
    min_charge_a: float = 10.0
    round_step_a: float = 5.0
    write_threshold_a: float = 5.0

    # Watt-based control limits
    min_charge_w: float = 500.0
    round_step_w: float = 100.0
    write_threshold_w: float = 100.0

    # Mode behavior
    soc_target_is_discharge_floor: bool = True
    soc_target_is_charge_ceiling: bool = True

    # Safety parameters
    inverter_ac_limit_kw: float = 8.0

    # Mode settling behavior
    requires_mode_settling: bool = False
    mode_settling_ms: int = 0

    # Grid Charge Specifics
    grid_charge_round_step_w: float | None = None  # Specific rounding for grid charging


@dataclass
class ProfileDefaults:
    """Suggested configuration values for this profile."""

    battery: dict[str, Any] = field(default_factory=dict)
    executor: dict[str, Any] = field(default_factory=dict)
    # Note: suggested_entities is deprecated in favor of defining suggestions
    # directly as values in the entities block.
    suggested_entities: dict[str, str] = field(default_factory=dict)


@dataclass
class InverterProfile:
    """
    Complete inverter profile definition.

    Contains all information needed to control a specific inverter brand.
    """

    metadata: ProfileMetadata
    capabilities: ProfileCapabilities
    entities: ProfileEntities
    modes: ProfileModes
    behavior: ProfileBehavior
    defaults: ProfileDefaults = field(default_factory=ProfileDefaults)

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate the profile for completeness and correctness.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Validate metadata
        if not self.metadata.name:
            errors.append("Profile metadata.name is required")
        if not self.metadata.version:
            errors.append("Profile metadata.version is required")

        # Validate control unit
        if self.behavior.control_unit is not None and self.behavior.control_unit not in [
            "A",
            "W",
        ]:
            errors.append(f"Invalid control_unit: {self.behavior.control_unit}. Must be 'A' or 'W'")

        # Validate mode values
        if not self.modes.export or not self.modes.export.value:
            errors.append("modes.export.value is required")
        if not self.modes.zero_export or not self.modes.zero_export.value:
            errors.append("modes.zero_export.value is required")
        if not self.modes.self_consumption or not self.modes.self_consumption.value:
            errors.append("modes.self_consumption.value is required")
        if not self.modes.idle or not self.modes.idle.value:
            errors.append("modes.idle.value is required")

        # Optional modes can be null, but if they exist, they must have a value
        if self.modes.charge_from_grid and not self.modes.charge_from_grid.value:
            errors.append("modes.charge_from_grid.value is required")
        if self.modes.force_discharge and not self.modes.force_discharge.value:
            errors.append("modes.force_discharge.value is required")

        # Validate required entities (only log warnings, don't fail validation)
        # This is because entities are configured by the user in config.yaml
        is_entities_valid, missing = self.entities.validate_required()
        if not is_entities_valid:
            logger.warning(
                "Profile '%s' has missing required entities (user must configure): %s",
                self.metadata.name,
                ", ".join(missing),
            )

        return len(errors) == 0, errors

    def get_suggested_config(self) -> dict[str, Any]:
        """
        Return suggested configuration based on profile defaults.

        Returns:
            Dictionary with suggested config keys and values
        """
        suggestions = {}

        # 1. Internal entities block suggestions (Rev IP4)
        for key, value in self.entities.required.items():
            if value:
                suggestions[f"executor.inverter.{key}"] = value
        for key, value in self.entities.optional.items():
            if value:
                suggestions[f"executor.inverter.{key}"] = value

        # 2. Legacy suggested_entities block (for compatibility)
        for key, value in self.defaults.suggested_entities.items():
            suggestions[f"executor.inverter.{key}"] = value

        # 3. Battery defaults
        for key, value in self.defaults.battery.items():
            suggestions[f"battery.{key}"] = value

        # 4. Executor defaults
        for key, value in self.defaults.executor.items():
            if isinstance(value, dict):
                for subkey, subval in value.items():
                    suggestions[f"executor.{key}.{subkey}"] = subval
            else:
                suggestions[f"executor.{key}"] = value

        return suggestions

    def get_missing_entities(self, config: dict[str, Any]) -> list[str]:
        """
        Check which required entities are missing in the provided config.

        Args:
            config: Full configuration dictionary

        Returns:
            List of missing configuration keys (e.g., 'executor.inverter.work_mode')
        """
        missing = []
        inverter_config = config.get("executor", {}).get("inverter", {})

        for entity_key in self.entities.required:
            # Check both clean key and legacy key (with _entity suffix)
            val = inverter_config.get(entity_key)
            if not val:
                legacy_key = f"{entity_key}_entity"
                val = inverter_config.get(legacy_key)

            # REV F56: Check custom_entities as well for profile-specific required keys
            if not val:
                val = inverter_config.get("custom_entities", {}).get(entity_key)

            if not val:
                missing.append(f"executor.inverter.{entity_key}")

        return missing


def load_profile_yaml(profile_path: Path) -> dict[str, Any]:
    """
    Load profile YAML file.

    Args:
        profile_path: Path to the profile YAML file

    Returns:
        Parsed YAML dict

    Raises:
        FileNotFoundError: If profile file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile file not found: {profile_path}")

    with profile_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(f"Profile file is empty: {profile_path}")

    return data


def _parse_work_mode(mode_data: dict[str, Any] | None) -> WorkMode | None:
    """Parse work mode from YAML data."""
    if not mode_data:
        return None

    return WorkMode(
        value=mode_data.get("value"),
        description=mode_data.get("description", ""),
        requires_grid_charging=mode_data.get("requires_grid_charging", False),
        skip_discharge_limit=mode_data.get("skip_discharge_limit", False),
        skip_export_power=mode_data.get("skip_export_power", False),
        set_entities=mode_data.get("set_entities", {}),
    )


def parse_profile(data: dict[str, Any]) -> InverterProfile:
    """
    Parse profile data into InverterProfile dataclass.

    Args:
        data: Profile YAML data

    Returns:
        InverterProfile instance

    Raises:
        ValueError: If required fields are missing
    """
    # Parse metadata
    metadata_data = data.get("metadata", {})
    metadata = ProfileMetadata(
        name=metadata_data.get("name", "unknown"),
        version=metadata_data.get("version", "1.0.0"),
        description=metadata_data.get("description", ""),
        supported_brands=metadata_data.get("supported_brands", []),
        author=metadata_data.get("author", "Unknown"),
        created_at=metadata_data.get("created_at", ""),
        updated_at=metadata_data.get("updated_at", ""),
    )

    # Parse capabilities
    cap_data = data.get("capabilities", {})
    capabilities = ProfileCapabilities(
        grid_charging_control=cap_data.get("grid_charging_control", True),
        watts_based_control=cap_data.get("watts_based_control", False),
        service_call_mode=cap_data.get("service_call_mode", False),
        separate_grid_charging_switch=cap_data.get("separate_grid_charging_switch", True),
        supports_export_mode=cap_data.get("supports_export_mode", True),
        supports_zero_export=cap_data.get("supports_zero_export", True),
        supports_self_consumption=cap_data.get("supports_self_consumption", True),
        supports_soc_target=cap_data.get("supports_soc_target", True),
        supports_grid_export_limit=cap_data.get("supports_grid_export_limit", True),
        supports_force_discharge=cap_data.get("supports_force_discharge", False),
    )

    # Parse entities
    entities_data = data.get("entities", {})
    entities = ProfileEntities(
        required=entities_data.get("required", {}),
        optional=entities_data.get("optional", {}),
    )

    # Parse modes
    modes_data = data.get("modes", {})
    modes = ProfileModes(
        export=_parse_work_mode(modes_data.get("export")),
        zero_export=_parse_work_mode(modes_data.get("zero_export")),
        self_consumption=_parse_work_mode(modes_data.get("self_consumption")),
        charge_from_grid=_parse_work_mode(modes_data.get("charge_from_grid")),
        force_discharge=_parse_work_mode(modes_data.get("force_discharge")),
        idle=_parse_work_mode(modes_data.get("idle")),
    )

    # Parse behavior
    behavior_data = data.get("behavior", {})
    behavior = ProfileBehavior(
        control_unit=behavior_data.get("control_unit", "A"),
        min_charge_a=behavior_data.get("min_charge_a", 10.0),
        round_step_a=behavior_data.get("round_step_a", 5.0),
        write_threshold_a=behavior_data.get("write_threshold_a", 5.0),
        min_charge_w=behavior_data.get("min_charge_w", 500.0),
        round_step_w=behavior_data.get("round_step_w", 100.0),
        write_threshold_w=behavior_data.get("write_threshold_w", 100.0),
        soc_target_is_discharge_floor=behavior_data.get("soc_target_is_discharge_floor", True),
        soc_target_is_charge_ceiling=behavior_data.get("soc_target_is_charge_ceiling", True),
        inverter_ac_limit_kw=behavior_data.get("inverter_ac_limit_kw", 8.0),
        requires_mode_settling=behavior_data.get("requires_mode_settling", False),
        mode_settling_ms=behavior_data.get("mode_settling_ms", 0),
        grid_charge_round_step_w=behavior_data.get("grid_charge_round_step_w"),
    )

    # Parse defaults
    defaults_data = data.get("defaults", {})
    defaults = ProfileDefaults(
        battery=defaults_data.get("battery", {}),
        executor=defaults_data.get("executor", {}),
        suggested_entities=defaults_data.get("suggested_entities", {}),
    )

    return InverterProfile(
        metadata=metadata,
        capabilities=capabilities,
        entities=entities,
        modes=modes,
        behavior=behavior,
        defaults=defaults,
    )


def load_profile(profile_name: str, profiles_dir: str | Path = "profiles") -> InverterProfile:
    """
    Load an inverter profile by name.

    Args:
        profile_name: Name of the profile (e.g., "deye", "fronius", "generic")
        profiles_dir: Directory containing profile YAML files

    Returns:
        InverterProfile instance

    Raises:
        FileNotFoundError: If profile file doesn't exist
        ValueError: If profile is invalid
    """
    profiles_path = Path(profiles_dir)
    profile_file = profiles_path / f"{profile_name}.yaml"

    logger.info("Loading inverter profile: %s from %s", profile_name, profile_file)

    # Load YAML
    try:
        data = load_profile_yaml(profile_file)
    except FileNotFoundError:
        logger.error("Profile file not found: %s", profile_file)
        raise
    except yaml.YAMLError as e:
        logger.error("Failed to parse profile YAML: %s", e)
        raise ValueError(f"Invalid YAML in profile {profile_name}: {e}") from e

    # Parse into dataclass
    try:
        profile = parse_profile(data)
    except Exception as e:
        logger.exception("Failed to parse profile data for profile %s", profile_name)
        raise ValueError(f"Failed to parse profile {profile_name}: {e}") from e

    # Validate
    is_valid, errors = profile.validate()
    if not is_valid:
        error_msg = f"Profile {profile_name} validation failed: {', '.join(errors)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(
        "Profile loaded successfully: %s v%s (%s)",
        profile.metadata.name,
        profile.metadata.version,
        ", ".join(profile.metadata.supported_brands),
    )

    return profile


def get_profile_from_config(
    config: dict[str, Any], profiles_dir: str | Path = "profiles"
) -> InverterProfile:
    """
    Load profile based on config setting with fallback to generic.

    Args:
        config: Full config dictionary with system.inverter_profile setting
        profiles_dir: Directory containing profile YAML files

    Returns:
        InverterProfile instance
    """
    # Get profile name from config
    system_config = config.get("system", {})
    profile_name = system_config.get("inverter_profile", "generic")

    logger.info("Loading inverter profile from config: %s", profile_name)

    # Try to load the specified profile
    try:
        return load_profile(profile_name, profiles_dir)
    except FileNotFoundError:
        logger.warning("Profile '%s' not found, falling back to 'generic' profile", profile_name)
        # Fallback to generic profile
        return load_profile("generic", profiles_dir)
    except Exception as e:
        logger.error("Failed to load profile '%s': %s. Falling back to 'generic'", profile_name, e)
        # Fallback to generic profile
        return load_profile("generic", profiles_dir)


def list_profiles(profiles_dir: str | Path = "profiles") -> list[dict[str, Any]]:
    """
    List all available profiles in the profiles directory.

    Returns:
        List of profile metadata dictionaries (name, description, supported_brands)
    """
    profiles_path = Path(profiles_dir)
    profiles = []

    if not profiles_path.exists():
        logger.warning("Profiles directory not found: %s", profiles_path)
        return []

    for yaml_file in profiles_path.glob("*.yaml"):
        if yaml_file.name == "schema.yaml":
            continue

        try:
            # We only need metadata for the list, but loading the whole profile
            # ensures only valid profiles are shown in the UI.
            profile = load_profile(yaml_file.stem, profiles_dir)
            profiles.append(
                {
                    "name": profile.metadata.name,
                    "description": profile.metadata.description,
                    "supported_brands": profile.metadata.supported_brands,
                    "version": profile.metadata.version,
                    "capabilities": {
                        "grid_charging_control": profile.capabilities.grid_charging_control,
                        "watts_based_control": profile.capabilities.watts_based_control,
                        "service_call_mode": profile.capabilities.service_call_mode,
                        "separate_grid_charging_switch": profile.capabilities.separate_grid_charging_switch,
                        "supports_export_mode": profile.capabilities.supports_export_mode,
                        "supports_zero_export": profile.capabilities.supports_zero_export,
                        "supports_self_consumption": profile.capabilities.supports_self_consumption,
                        "supports_soc_target": profile.capabilities.supports_soc_target,
                        "supports_grid_export_limit": profile.capabilities.supports_grid_export_limit,
                        "supports_force_discharge": profile.capabilities.supports_force_discharge,
                    },
                    "behavior": {
                        "control_unit": profile.behavior.control_unit,
                    },
                    "entities": {
                        "required": profile.entities.required,
                        "optional": profile.entities.optional,
                    },
                }
            )
        except Exception as e:
            logger.error("Skipping invalid profile %s: %s", yaml_file.name, e)

    # Sort by name
    return sorted(profiles, key=lambda x: x["name"])
