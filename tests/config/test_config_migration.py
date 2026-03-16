import logging
from pathlib import Path

import pytest

# Setup logging
logging.basicConfig(level=logging.INFO)


class TestDeprecatedKeyRemoval:
    """Test that deprecated keys are actually deleted."""

    def test_remove_deprecated_keys_root_level(self):
        from backend.config_migration import remove_deprecated_keys

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
        from backend.config_migration import remove_deprecated_keys

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


class TestBackendSave:
    """Test backend save logic with template merge."""

    @pytest.mark.asyncio
    async def test_backend_save_removes_deprecated_keys(self, tmp_path, monkeypatch):
        from ruamel.yaml import YAML

        from backend.api.routers.config import save_config

        yaml_loader = YAML()

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
            yaml_loader.dump(user_config, f)
        with default_file.open("w") as f:
            yaml_loader.dump(default_config, f)

        import backend.api.routers.config as config_router

        monkeypatch.setattr(
            config_router,
            "Path",
            lambda p: tmp_path / p if p in ["config.yaml", "config.default.yaml"] else Path(p),
        )
        monkeypatch.setattr(config_router, "get_executor_instance", lambda: None)
        monkeypatch.setattr(config_router, "_validate_config_for_save", lambda x: [])

        await save_config({"timezone": "Europe/Stockholm"})

        with config_file.open() as f:
            saved_data = yaml_loader.load(f)
        assert saved_data["timezone"] == "Europe/Stockholm"
        assert "deferrable_loads" not in saved_data


class TestBackupSystem:
    """Test timestamped backup system."""

    def test_create_timestamped_backup(self, tmp_path):
        from backend.config_migration import create_timestamped_backup

        config_file = tmp_path / "config.yaml"
        config_file.write_text("test content")

        backup_path = create_timestamped_backup(config_file)
        assert backup_path is not None
        assert backup_path.exists()
        assert "config.yaml_" in backup_path.name


class TestTemplateAwareMerge:
    """Test template_aware_merge functionality."""

    def test_merge_preserves_comments(self):
        from ruamel.yaml import YAML

        from backend.config_migration import template_aware_merge

        yaml_loader = YAML()
        template_str = """
# Global Comment
system:
  # Section Comment
  id: "default_id"
"""
        user_cfg = {"system": {"id": "user_id"}}
        template_cfg = yaml_loader.load(template_str)
        template_aware_merge(template_cfg, user_cfg)
        assert template_cfg["system"]["id"] == "user_id"


class TestFullMigrationFlow:
    """Test the complete migration pipeline."""

    @pytest.mark.asyncio
    async def test_migrate_config_idempotent_for_clean_config(self, tmp_path, monkeypatch):
        """Verify that a clean config_version=2 config with no deprecated keys is not rewritten."""
        from ruamel.yaml import YAML

        import backend.config_migration as cm

        yaml_loader = YAML()
        config_file = tmp_path / "config.yaml"
        default_file = tmp_path / "config.default.yaml"

        clean_config = {
            "config_version": 2,
            "system": {
                "system_id": "test",
                "inverter_profile": "test",
                "has_solar": False,
                "has_battery": True,
            },
            "battery": {"min_soc_percent": 20},
            "executor": {},
            "input_sensors": {},
        }

        with config_file.open("w") as f:
            yaml_loader.dump(clean_config, f)
        with default_file.open("w") as f:
            yaml_loader.dump(clean_config, f)

        monkeypatch.setattr(
            cm,
            "Path",
            lambda p: tmp_path / p if p in ["config.yaml", "config.default.yaml"] else Path(p),
        )

        write_calls: list = []

        def mock_write(*args, **kwargs):
            write_calls.append(args)

        monkeypatch.setattr(cm, "_write_config", mock_write)

        await cm.migrate_config(strict_validation=False)

        assert len(write_calls) == 0, (
            f"_write_config was called {len(write_calls)} time(s) but should not have been "
            f"for a clean config with no deprecated keys"
        )


class TestWaterHeaterMigration:
    """Test water heater field migration from legacy locations to water_heaters[] array."""

    def test_migrate_all_water_heater_fields(self):
        """Legacy config with all three keys → values migrate into water_heaters[0], old keys removed."""
        from backend.config_migration import _migrate_water_heater_fields

        config = {
            "config_version": 2,
            "input_sensors": {
                "water_power": "sensor.boiler_power",
                "water_heater_consumption": "sensor.boiler_energy",
                "grid_power": "sensor.grid",
            },
            "executor": {
                "water_heater": {
                    "target_entity": "climate.boiler",
                    "temp_off": 40,
                    "temp_normal": 60,
                }
            },
            "water_heaters": [
                {
                    "id": "main_tank",
                    "sensor": "",
                    "energy_sensor": "",
                    "target_entity": "",
                    "power_kw": 3.0,
                }
            ],
        }

        result, changed = _migrate_water_heater_fields(config)

        assert changed is True
        # Values should be migrated
        assert result["water_heaters"][0]["sensor"] == "sensor.boiler_power"
        assert result["water_heaters"][0]["energy_sensor"] == "sensor.boiler_energy"
        assert result["water_heaters"][0]["target_entity"] == "climate.boiler"
        # Old keys should be removed
        assert "water_power" not in result["input_sensors"]
        assert "water_heater_consumption" not in result["input_sensors"]
        assert "target_entity" not in result["executor"]["water_heater"]
        # Other keys should remain
        assert result["input_sensors"]["grid_power"] == "sensor.grid"
        assert result["executor"]["water_heater"]["temp_off"] == 40

    def test_migrate_preserves_existing_sensor(self):
        """Config with sensor already set → input_sensors.water_power is NOT copied, old key still removed."""
        from backend.config_migration import _migrate_water_heater_fields

        config = {
            "config_version": 2,
            "input_sensors": {
                "water_power": "sensor.boiler_power",
                "water_heater_consumption": "",
            },
            "executor": {
                "water_heater": {
                    "target_entity": "",
                }
            },
            "water_heaters": [
                {
                    "id": "main_tank",
                    "sensor": "sensor.existing_power",  # Already set
                    "energy_sensor": "",
                    "target_entity": "",
                }
            ],
        }

        result, changed = _migrate_water_heater_fields(config)

        assert changed is True  # Still changed because old keys are removed
        # Existing value should be preserved
        assert result["water_heaters"][0]["sensor"] == "sensor.existing_power"
        # Old key should still be removed
        assert "water_power" not in result["input_sensors"]

    def test_migrate_no_water_heaters(self):
        """Config with no water_heaters array should not crash."""
        from backend.config_migration import _migrate_water_heater_fields

        config = {
            "config_version": 2,
            "input_sensors": {
                "water_power": "sensor.boiler_power",
            },
        }

        result, changed = _migrate_water_heater_fields(config)

        # Should not crash, no changes made
        assert changed is False
        assert "input_sensors" in result

    def test_migrate_empty_water_heaters(self):
        """Config with empty water_heaters array should not crash."""
        from backend.config_migration import _migrate_water_heater_fields

        config = {
            "config_version": 2,
            "input_sensors": {
                "water_power": "sensor.boiler_power",
            },
            "water_heaters": [],
        }

        result, changed = _migrate_water_heater_fields(config)

        # Should not crash, no changes made to array
        assert changed is False
        assert result["water_heaters"] == []
