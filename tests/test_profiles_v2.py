"""
Tests for the Inverter Profile System v2

Tests profile loading, validation, parsing for v2 schema profiles.
These tests exercise profiles directly from disk using the v2 YAML format.
"""

from typing import ClassVar

import pytest

from executor.profiles import InverterProfile, list_profiles, load_profile

PROFILE_NAMES = ["deye", "sungrow", "fronius", "generic"]


class TestProfileV2Loading:
    """Test v2 profile YAML loading from disk."""

    @pytest.mark.parametrize("profile_name", PROFILE_NAMES)
    def test_load_profile_from_disk(self, profile_name):
        """Test that all profiles load successfully from disk."""
        profile = load_profile(profile_name)
        assert profile is not None
        assert isinstance(profile, InverterProfile)

    @pytest.mark.parametrize("profile_name", PROFILE_NAMES)
    def test_profile_has_schema_version_2(self, profile_name):
        """All profiles must have schema_version == 2."""
        profile = load_profile(profile_name)
        assert profile.metadata.schema_version == 2

    @pytest.mark.parametrize("profile_name", PROFILE_NAMES)
    def test_profile_has_metadata(self, profile_name):
        """Profile must have valid metadata."""
        profile = load_profile(profile_name)
        assert profile.metadata.name == profile_name
        assert profile.metadata.version is not None
        assert profile.metadata.description is not None

    @pytest.mark.parametrize("profile_name", PROFILE_NAMES)
    def test_profile_has_supported_brands(self, profile_name):
        """Profile must list supported brands."""
        profile = load_profile(profile_name)
        assert profile.metadata.supported_brands is not None
        assert len(profile.metadata.supported_brands) > 0


class TestProfileV2Modes:
    """Test v2 profile mode structure."""

    REQUIRED_MODES: ClassVar = ["charge", "export", "self_consumption", "idle"]

    @pytest.mark.parametrize("profile_name", PROFILE_NAMES)
    def test_profile_has_4_required_modes(self, profile_name):
        """All profiles must have 4 required modes."""
        profile = load_profile(profile_name)
        for mode_name in self.REQUIRED_MODES:
            assert mode_name in profile.modes, f"Profile {profile_name} missing mode: {mode_name}"

    @pytest.mark.parametrize("profile_name", PROFILE_NAMES)
    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_mode_has_actions(self, profile_name, mode_name):
        """Each mode must have actions list."""
        profile = load_profile(profile_name)
        mode = profile.get_mode(mode_name)
        assert mode.actions is not None
        assert isinstance(mode.actions, list)

    @pytest.mark.parametrize("profile_name", PROFILE_NAMES)
    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_mode_has_description(self, profile_name, mode_name):
        """Each mode must have a description."""
        profile = load_profile(profile_name)
        mode = profile.get_mode(mode_name)
        assert mode.description is not None
        assert len(mode.description) > 0


class TestProfileV2EntityValidation:
    """Test v2 profile entity validation."""

    VALID_DOMAINS: ClassVar = {"select", "number", "switch", "input_number", "sensor"}
    VALID_CATEGORIES: ClassVar = {"system", "battery"}

    @pytest.mark.parametrize("profile_name", PROFILE_NAMES)
    def test_all_entity_domains_are_valid(self, profile_name):
        """All entity domains must be valid."""
        profile = load_profile(profile_name)
        for key, entity in profile.entities.items():
            assert entity.domain in self.VALID_DOMAINS, f"Invalid domain {entity.domain} for {key}"

    @pytest.mark.parametrize("profile_name", PROFILE_NAMES)
    def test_all_entity_categories_are_valid(self, profile_name):
        """All entity categories must be valid."""
        profile = load_profile(profile_name)
        for key, entity in profile.entities.items():
            assert entity.category in self.VALID_CATEGORIES, (
                f"Invalid category {entity.category} for {key}"
            )

    @pytest.mark.parametrize("profile_name", PROFILE_NAMES)
    def test_all_mode_actions_reference_valid_entity_keys(self, profile_name):
        """All mode actions must reference valid entity keys."""
        profile = load_profile(profile_name)
        for mode_name in profile.modes:
            mode = profile.get_mode(mode_name)
            for action in mode.actions:
                assert action.entity in profile.entities, (
                    f"Invalid entity key {action.entity} in mode {mode_name}"
                )


class TestProfileV2DynamicTemplates:
    """Test v2 profile dynamic template validation."""

    VALID_TEMPLATES: ClassVar = {
        "{{charge_value}}",
        "{{discharge_value}}",
        "{{soc_target}}",
        "{{export_power_w}}",
        "{{max_charge}}",
        "{{max_discharge}}",
        "true",
        "false",
    }

    @pytest.mark.parametrize("profile_name", PROFILE_NAMES)
    def test_all_dynamic_templates_are_valid(self, profile_name):
        """All dynamic templates must be valid."""
        profile = load_profile(profile_name)
        for mode_name in profile.modes:
            mode = profile.get_mode(mode_name)
            for action in mode.actions:
                value = action.value
                if isinstance(value, str) and "{{" in value:
                    assert value in self.VALID_TEMPLATES, (
                        f"Invalid template {value} in mode {mode_name}"
                    )


class TestProfileV2Roundtrip:
    """Test profile roundtrip: YAML -> dataclass -> validation."""

    @pytest.mark.parametrize("profile_name", PROFILE_NAMES)
    def test_profile_roundtrip(self, profile_name):
        """Profile can be parsed from YAML and re-serialized."""
        profile = load_profile(profile_name)

        assert profile.metadata.name == profile_name
        assert profile.metadata.schema_version == 2
        assert len(profile.modes) >= 4
        assert len(profile.entities) > 0

    @pytest.mark.parametrize("profile_name", PROFILE_NAMES)
    def test_profile_validation_passes(self, profile_name):
        """Parsed profile should pass validation."""
        profile = load_profile(profile_name)
        is_valid, errors = profile.validate()
        assert is_valid, f"Validation errors: {errors}"


class TestProfileV2ListProfiles:
    """Test profile listing."""

    def test_list_profiles_returns_all_4(self):
        """list_profiles should return all 4 profiles."""
        profiles = list_profiles()
        assert len(profiles) == 4
        names = [p["name"] for p in profiles]
        for name in PROFILE_NAMES:
            assert name in names

    def test_list_profiles_sorted(self):
        """list_profiles should return sorted list."""
        profiles = list_profiles()
        names = [p["name"] for p in profiles]
        assert names == sorted(names)
