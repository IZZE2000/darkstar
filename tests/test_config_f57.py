"""
REV F57 Test Suite - Config Corruption Prevention
Tests for migration cleanup, backend save, and validation.
"""

import io
import time
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from backend.config_migration import (
    create_timestamped_backup,
    migrate_arc15_entity_config,
    migrate_config,
    migrate_solar_arrays,
    migrate_version_key,
    remove_deprecated_keys,
    template_aware_merge,
    validate_config_for_write,
)


class TestDeprecatedKeyRemoval:
    """Test that deprecated keys are actually deleted."""

    def test_migrate_version_key(self):
        """Test version -> config_version migration."""
        config = {
            "version": "2.4.21-beta",
            "timezone": "Europe/Stockholm",
        }

        result, changed = migrate_version_key(config)

        assert changed
        assert "version" not in result
        assert "config_version" in result
        assert result["config_version"] == 2

    def test_remove_deprecated_keys_root_level(self):
        """Test root-level deprecated key removal."""
        config = {
            "config_version": 2,
            "deferrable_loads": [],
            "ev_charger": {},
            "solar_array": {},
        }

        result, changed = remove_deprecated_keys(config)

        assert changed
        assert "deferrable_loads" not in result
        assert "ev_charger" not in result
        assert "solar_array" not in result

    def test_remove_deprecated_keys_nested(self):
        """Test nested deprecated key removal."""
        config = {
            "executor": {
                "inverter": {
                    "work_mode": "select.ems_mode",
                    "work_mode_entity": "select.ems_mode",  # Deprecated
                    "soc_target": "",
                    "soc_target_entity": "",  # Deprecated
                }
            }
        }

        result, changed = remove_deprecated_keys(config)

        assert changed
        assert "work_mode" in result["executor"]["inverter"]
        assert "work_mode_entity" not in result["executor"]["inverter"]
        assert "soc_target_entity" not in result["executor"]["inverter"]

    def test_arc15_deletes_deprecated_keys(self):
        """Test ARC15 migration actually deletes deferrable_loads and ev_charger."""
        config = {
            "config_version": 1,
            "deferrable_loads": [{"id": "water_heater", "nominal_power_kw": 3.0}],
            "ev_charger": {"enabled": True},
            "system": {"has_water_heater": True, "has_ev_charger": True},
            "input_sensors": {},
            "water_heating": {},
        }

        result, changed = migrate_arc15_entity_config(config)

        assert changed
        assert result["config_version"] == 2
        assert "deferrable_loads" not in result
        assert "ev_charger" not in result
        assert "water_heaters" in result
        assert len(result["water_heaters"]) == 1

    def test_solar_arrays_deletes_legacy_key(self):
        """Test migrate_solar_arrays deletes legacy solar_array key."""
        config = {"system": {"solar_array": {"azimuth": 180, "kwp": 5.0, "tilt": 35}}}

        result, changed = migrate_solar_arrays(config)

        assert changed
        assert "solar_arrays" in result["system"]
        assert "solar_array" not in result["system"]


class TestBackendSave:
    """Test backend save logic with template merge."""

    @pytest.mark.asyncio
    async def test_backend_save_removes_deprecated_keys(self, tmp_path, monkeypatch):
        """Test that backend save removes deprecated keys."""
        from backend.api.routers.config import save_config

        yaml = YAML()

        # Setup mock files
        config_file = tmp_path / "config.yaml"
        default_file = tmp_path / "config.default.yaml"

        user_config = {
            "config_version": 2,
            "deferrable_loads": [{"id": "old_load"}],
            "timezone": "Europe/London",
            "system": {
                "system_id": "test",
                "inverter_profile": "test",
                "has_solar": False,
                "has_battery": False,
            },
            "battery": {},
            "executor": {},
            "input_sensors": {},
        }

        default_config = {
            "config_version": 2,
            "timezone": "Europe/London",
            "system": {
                "system_id": "test",
                "inverter_profile": "test",
                "has_solar": False,
                "has_battery": False,
            },
            "battery": {},
            "executor": {},
            "input_sensors": {},
        }

        with config_file.open("w") as f:
            yaml.dump(user_config, f)
        with default_file.open("w") as f:
            yaml.dump(default_config, f)

        import backend.api.routers.config as config_router

        monkeypatch.setattr(
            config_router,
            "Path",
            lambda p: tmp_path / p if p in ["config.yaml", "config.default.yaml"] else Path(p),
        )
        monkeypatch.setattr(config_router, "get_executor_instance", lambda: None)
        monkeypatch.setattr(config_router, "_validate_config_for_save", lambda x: [])

        payload = {"timezone": "Europe/Stockholm"}
        result = await save_config(payload)
        assert result["status"] == "success"

        with config_file.open() as f:
            saved_data = yaml.load(f)
        assert saved_data["timezone"] == "Europe/Stockholm"
        assert "deferrable_loads" not in saved_data


class TestBackupSystem:
    """Test timestamped backup system."""

    def test_create_timestamped_backup(self, tmp_path):
        """Test that a backup is created in the backups/ folder."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("test content")

        backup_path = create_timestamped_backup(config_file)

        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.parent.name == "backups"
        assert "config.yaml_" in backup_path.name
        assert backup_path.read_text() == "test content"

    def test_backup_retention(self, tmp_path):
        """Test that only max_backups are retained."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("test content")

        for _ in range(5):
            create_timestamped_backup(config_file, max_backups=3)
            time.sleep(1.1)

        backup_dir = tmp_path / "backups"
        backups = list(backup_dir.glob("config.yaml_*.bak"))
        assert len(backups) == 3


class TestValidation:
    """Test pre-write validation."""

    def test_validate_config_for_write_success(self):
        """Test validation passes for healthy config."""
        config = {
            "config_version": 2,
            "system": {},
            "battery": {},
            "executor": {},
            "input_sensors": {},
        }
        assert validate_config_for_write(config) is True

    def test_validate_config_for_write_missing_section(self):
        """Test validation fails if required section is missing."""
        config = {"config_version": 2, "system": {}, "executor": {}, "input_sensors": {}}
        assert validate_config_for_write(config) is False

    def test_validate_config_for_write_deprecated_key(self):
        """Test validation fails if deprecated key is present."""
        config = {
            "config_version": 2,
            "system": {},
            "battery": {},
            "executor": {},
            "input_sensors": {},
            "deferrable_loads": [],
        }
        assert validate_config_for_write(config) is False

    def test_validate_config_for_write_version_position(self):
        """Test validation fails if config_version is too deep."""
        config = {f"key_{i}": i for i in range(15)}
        config["config_version"] = 2
        config["system"] = {}
        config["battery"] = {}
        config["executor"] = {}
        config["input_sensors"] = {}
        assert validate_config_for_write(config) is False


class TestTemplateAwareMerge:
    """Test template_aware_merge functionality."""

    def test_merge_preserves_comments(self):
        """Test that comments from template are preserved."""
        yaml = YAML()
        template_str = """
# Global Comment
system:
  # Section Comment
  id: "default_id"
  # Key Comment
  has_battery: true
"""
        user_cfg = {"system": {"id": "user_id", "has_battery": False}}
        template_cfg = yaml.load(template_str)
        template_aware_merge(template_cfg, user_cfg)

        assert template_cfg["system"]["id"] == "user_id"
        assert template_cfg["system"]["has_battery"] is False

        out = io.StringIO()
        yaml.dump(template_cfg, out)
        dumped = out.getvalue()
        assert "# Global Comment" in dumped
        assert "# Section Comment" in dumped
        assert "# Key Comment" in dumped

    def test_merge_preserves_order(self):
        """Test that template section ordering is preserved."""
        yaml = YAML()
        template_str = "z_section: 1\na_section: 2\nm_section: 3\n"
        user_cfg = {"m_section": 10, "z_section": 20, "a_section": 30}
        template_cfg = yaml.load(template_str)
        template_aware_merge(template_cfg, user_cfg)

        keys = list(template_cfg.keys())
        assert keys == ["z_section", "a_section", "m_section"]
        assert template_cfg["z_section"] == 20
        assert template_cfg["a_section"] == 30
        assert template_cfg["m_section"] == 10


class TestFullMigrationFlow:
    """Test the complete migration pipeline for F57 fixes."""

    @pytest.mark.asyncio
    async def test_migrate_config_heals_corruption(self, tmp_path, monkeypatch):
        """Test that migrate_config applies all F57 fixes at once."""
        yaml = YAML()
        config_file = tmp_path / "config.yaml"
        default_file = tmp_path / "config.default.yaml"

        # COMPLETE mock config to pass structural validation
        corrupted_config = {
            "version": "2.4.21-beta",
            "deferrable_loads": [{"id": "old"}],
            "system": {
                "system_id": "test",
                "inverter_profile": "test",
                "has_battery": True,
                "has_solar": False,
                "location": {"latitude": 59.3, "longitude": 18.0},
                "solar_array": {"kwp": 5.0},  # Legacy key
            },
        }

        default_template = {
            "config_version": 2,
            "system": {
                "system_id": "default",
                "inverter_profile": "generic",
                "has_battery": False,
                "has_solar": False,
                "location": {"latitude": 0, "longitude": 0},
                "solar_arrays": [],
            },
            "battery": {},
            "executor": {},
            "input_sensors": {},
        }

        with config_file.open("w") as f:
            yaml.dump(corrupted_config, f)
        with default_file.open("w") as f:
            yaml.dump(default_template, f)

        import backend.config_migration as cm

        monkeypatch.setattr(
            cm,
            "Path",
            lambda p: tmp_path / p if p in ["config.yaml", "config.default.yaml"] else Path(p),
        )

        await migrate_config()

        with config_file.open() as f:
            healed = yaml.load(f)

        assert healed["config_version"] == 2
        assert "version" not in healed
        assert "deferrable_loads" not in healed
        assert "solar_array" not in healed["system"]
        assert "solar_arrays" in healed["system"]
        assert healed["system"]["has_battery"] is True
        assert healed["system"]["system_id"] == "test"
        assert len(list(healed.keys())) >= 5
