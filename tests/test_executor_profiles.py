"""
Tests for the Inverter Profile System

Tests profile loading, validation, parsing, and error handling.
"""

import pytest
import yaml

from executor.profiles import (
    InverterProfile,
    ProfileBehavior,
    ProfileCapabilities,
    ProfileEntities,
    ProfileMetadata,
    ProfileModes,
    WorkMode,
    get_profile_from_config,
    load_profile,
    load_profile_yaml,
    parse_profile,
)


class TestProfileYAMLLoading:
    """Test YAML file loading."""

    def test_load_valid_yaml(self, tmp_path):
        """Test loading valid profile YAML."""
        profile_data = {
            "metadata": {"name": "test", "version": "1.0.0", "description": "Test"},
            "capabilities": {},
            "entities": {"required": {}, "optional": {}},
            "modes": {
                "export": {"value": "Export", "description": "Export mode"},
                "zero_export": {"value": "Zero", "description": "Zero export"},
            },
            "behavior": {},
            "defaults": {},
        }

        profile_file = tmp_path / "test.yaml"
        with profile_file.open("w") as f:
            yaml.dump(profile_data, f)

        loaded = load_profile_yaml(profile_file)
        assert loaded["metadata"]["name"] == "test"

    def test_load_missing_file(self, tmp_path):
        """Test loading non-existent profile file."""
        profile_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            load_profile_yaml(profile_file)

    def test_load_malformed_yaml(self, tmp_path):
        """Test loading malformed YAML."""
        profile_file = tmp_path / "malformed.yaml"
        with profile_file.open("w") as f:
            f.write("invalid: yaml: content:\n  - broken")

        with pytest.raises(yaml.YAMLError):
            load_profile_yaml(profile_file)

    def test_load_empty_yaml(self, tmp_path):
        """Test loading empty YAML file."""
        profile_file = tmp_path / "empty.yaml"
        with profile_file.open("w") as f:
            f.write("")

        with pytest.raises(ValueError, match="Profile file is empty"):
            load_profile_yaml(profile_file)


class TestProfileParsing:
    """Test profile data parsing."""

    def test_parse_complete_profile(self):
        """Test parsing a complete profile."""
        data = {
            "metadata": {
                "name": "test_inverter",
                "version": "1.0.0",
                "description": "Test inverter",
                "supported_brands": ["TestBrand"],
                "author": "Test Author",
                "created_at": "2026-01-01",
                "updated_at": "2026-02-01",
            },
            "capabilities": {
                "grid_charging_control": True,
                "watts_based_control": False,
                "supports_export_mode": True,
            },
            "entities": {
                "required": {"work_mode": "select.work_mode", "soc_target": "number.soc"},
                "optional": {"max_charging_current": "number.charge_a"},
            },
            "modes": {
                "export": {"value": "Export First", "description": "Export mode"},
                "zero_export": {"value": "Zero Export", "description": "Zero export mode"},
            },
            "behavior": {
                "control_unit": "A",
                "min_charge_a": 10.0,
                "inverter_ac_limit_kw": 8.0,
            },
            "defaults": {
                "battery": {"nominal_voltage_v": 48.0},
                "executor": {"controller": {"min_charge_a": 10.0}},
            },
        }

        profile = parse_profile(data)

        assert profile.metadata.name == "test_inverter"
        assert profile.metadata.version == "1.0.0"
        assert "TestBrand" in profile.metadata.supported_brands
        assert profile.capabilities.grid_charging_control is True
        assert profile.capabilities.watts_based_control is False
        assert profile.entities.required["work_mode"] == "select.work_mode"
        assert profile.modes.export.value == "Export First"
        assert profile.behavior.control_unit == "A"
        assert profile.behavior.min_charge_a == 10.0

    def test_parse_minimal_profile(self):
        """Test parsing a minimal profile with defaults."""
        data = {
            "metadata": {"name": "minimal", "version": "1.0.0"},
            "modes": {
                "export": {"value": "Export"},
                "zero_export": {"value": "Zero"},
            },
        }

        profile = parse_profile(data)

        assert profile.metadata.name == "minimal"
        # Check defaults are applied
        assert profile.capabilities.grid_charging_control is True
        assert profile.behavior.control_unit == "A"


class TestProfileValidation:
    """Test profile validation."""

    def test_validate_valid_profile(self):
        """Test validation of a valid profile."""
        profile = InverterProfile(
            metadata=ProfileMetadata(name="test", version="1.0.0", description="Test"),
            capabilities=ProfileCapabilities(),
            entities=ProfileEntities(required={"work_mode": "test"}, optional={}),
            modes=ProfileModes(
                export=WorkMode(value="Export"),
                zero_export=WorkMode(value="Zero"),
            ),
            behavior=ProfileBehavior(control_unit="A"),
        )

        is_valid, errors = profile.validate()
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_metadata_name(self):
        """Test validation fails when metadata name is missing."""
        profile = InverterProfile(
            metadata=ProfileMetadata(name="", version="1.0.0", description="Test"),
            capabilities=ProfileCapabilities(),
            entities=ProfileEntities(),
            modes=ProfileModes(
                export=WorkMode(value="Export"),
                zero_export=WorkMode(value="Zero"),
            ),
            behavior=ProfileBehavior(),
        )

        is_valid, errors = profile.validate()
        assert is_valid is False
        assert any("name is required" in err for err in errors)

    def test_validate_invalid_control_unit(self):
        """Test validation fails with invalid control unit."""
        profile = InverterProfile(
            metadata=ProfileMetadata(name="test", version="1.0.0", description="Test"),
            capabilities=ProfileCapabilities(),
            entities=ProfileEntities(),
            modes=ProfileModes(
                export=WorkMode(value="Export"),
                zero_export=WorkMode(value="Zero"),
            ),
            behavior=ProfileBehavior(control_unit="X"),  # Invalid
        )

        is_valid, errors = profile.validate()
        assert is_valid is False
        assert any("Invalid control_unit" in err for err in errors)

    def test_validate_missing_mode_values(self):
        """Test validation fails when mode values are missing."""
        profile = InverterProfile(
            metadata=ProfileMetadata(name="test", version="1.0.0", description="Test"),
            capabilities=ProfileCapabilities(),
            entities=ProfileEntities(),
            modes=ProfileModes(
                export=WorkMode(value=None),  # Missing
                zero_export=WorkMode(value="Zero"),
            ),
            behavior=ProfileBehavior(),
        )

        is_valid, errors = profile.validate()
        assert is_valid is False
        assert any("export.value is required" in err for err in errors)


class TestEntityValidation:
    """Test entity validation."""

    def test_validate_required_entities_present(self):
        """Test validation passes when all required entities are configured."""
        entities = ProfileEntities(
            required={"work_mode": "select.work_mode", "soc_target": "number.soc"},
            optional={},
        )

        is_valid, missing = entities.validate_required()
        assert is_valid is True
        assert len(missing) == 0

    def test_validate_required_entities_missing(self):
        """Test validation fails when required entities are missing."""
        entities = ProfileEntities(
            required={"work_mode": None, "soc_target": "number.soc", "grid_charging": None},
            optional={},
        )

        is_valid, missing = entities.validate_required()
        assert is_valid is False
        assert "work_mode" in missing
        assert "grid_charging" in missing
        assert "soc_target" not in missing


class TestProfileLoading:
    """Test complete profile loading workflow."""

    def test_load_generic_profile(self):
        """Test loading the generic profile."""
        # This assumes profiles/generic.yaml exists
        profile = load_profile("generic", profiles_dir="profiles")

        assert profile.metadata.name == "generic"
        assert profile.modes.export.value is not None
        assert profile.modes.zero_export.value is not None
        # Check charge_from_grid mode (was grid_charge)
        assert profile.modes.charge_from_grid is not None
        assert profile.modes.charge_from_grid.requires_grid_charging is True

    def test_load_nonexistent_profile(self, tmp_path):
        """Test loading a non-existent profile raises error."""
        with pytest.raises(FileNotFoundError):
            load_profile("nonexistent", profiles_dir=tmp_path)

    def test_load_profile_from_config(self, tmp_path):
        """Test loading profile from config with fallback."""
        # Create a test profile
        profile_data = {
            "metadata": {"name": "test", "version": "1.0.0", "description": "Test"},
            "capabilities": {},
            "entities": {"required": {}, "optional": {}},
            "modes": {
                "export": {"value": "Export"},
                "zero_export": {"value": "Zero"},
            },
            "behavior": {},
        }

        profile_file = tmp_path / "test.yaml"
        with profile_file.open("w") as f:
            yaml.dump(profile_data, f)

        # Also create generic profile for fallback
        generic_file = tmp_path / "generic.yaml"
        with generic_file.open("w") as f:
            yaml.dump(profile_data, f)

        # Test with config specifying "test" profile
        config = {"system": {"inverter_profile": "test"}}
        profile = get_profile_from_config(config, profiles_dir=tmp_path)
        assert profile.metadata.name == "test"

    def test_load_profile_from_config_fallback(self, tmp_path):
        """Test fallback to generic when specified profile doesn't exist."""
        # Only create generic profile
        profile_data = {
            "metadata": {"name": "generic", "version": "1.0.0", "description": "Generic"},
            "capabilities": {},
            "entities": {"required": {}, "optional": {}},
            "modes": {
                "export": {"value": "Export"},
                "zero_export": {"value": "Zero"},
            },
            "behavior": {},
        }

        generic_file = tmp_path / "generic.yaml"
        with generic_file.open("w") as f:
            yaml.dump(profile_data, f)

        # Request non-existent profile
        config = {"system": {"inverter_profile": "nonexistent"}}
        profile = get_profile_from_config(config, profiles_dir=tmp_path)

        # Should fall back to generic
        assert profile.metadata.name == "generic"

    def test_load_profile_from_config_no_setting(self, tmp_path):
        """Test loading profile when config has no inverter_profile setting."""
        # Create generic profile
        profile_data = {
            "metadata": {"name": "generic", "version": "1.0.0", "description": "Generic"},
            "capabilities": {},
            "entities": {"required": {}, "optional": {}},
            "modes": {
                "export": {"value": "Export"},
                "zero_export": {"value": "Zero"},
            },
            "behavior": {},
        }

        generic_file = tmp_path / "generic.yaml"
        with generic_file.open("w") as f:
            yaml.dump(profile_data, f)

        # Config with no inverter_profile setting
        config = {"system": {}}
        profile = get_profile_from_config(config, profiles_dir=tmp_path)

        # Should default to generic
        assert profile.metadata.name == "generic"
