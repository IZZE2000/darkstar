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


@dataclass
class ProfileModes:
    """Work mode translations for the inverter."""

    export: WorkMode = field(default_factory=lambda: WorkMode(value="Export First"))
    zero_export: WorkMode = field(default_factory=lambda: WorkMode(value="Zero Export To CT"))
    self_consumption: WorkMode | None = None
    grid_charge: WorkMode | None = None  # Grid charging mode
    force_discharge: WorkMode | None = None  # Force discharge mode
    idle: WorkMode | None = None  # Idle/standby mode


@dataclass
class ProfileBehavior:
    """Inverter-specific behavioral parameters."""

    # Control unit settings
    control_unit: str = "A"  # "A" or "W"

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


@dataclass
class ProfileDefaults:
    """Suggested configuration values for this profile."""

    battery: dict[str, Any] = field(default_factory=dict)
    executor: dict[str, Any] = field(default_factory=dict)


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
        if self.behavior.control_unit not in ["A", "W"]:
            errors.append(f"Invalid control_unit: {self.behavior.control_unit}. Must be 'A' or 'W'")

        # Validate mode values
        if not self.modes.export.value:
            errors.append("modes.export.value is required")
        if not self.modes.zero_export.value:
            errors.append("modes.zero_export.value is required")

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


def _parse_work_mode(mode_data: dict[str, Any] | None) -> WorkMode:
    """Parse work mode from YAML data."""
    if not mode_data:
        return WorkMode(value=None)

    return WorkMode(
        value=mode_data.get("value"),
        description=mode_data.get("description", ""),
        requires_grid_charging=mode_data.get("requires_grid_charging", False),
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
        grid_charge=_parse_work_mode(modes_data.get("grid_charge")),
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
    )

    # Parse defaults
    defaults_data = data.get("defaults", {})
    defaults = ProfileDefaults(
        battery=defaults_data.get("battery", {}),
        executor=defaults_data.get("executor", {}),
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
        logger.error("Failed to parse profile data: %s", e)
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
