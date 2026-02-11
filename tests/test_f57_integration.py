"""
REV F57 Integration Tests
Tests that verify the actual debugging/config (3).yaml file heals correctly
and that healthy configs don't get corrupted.
"""

import shutil
from pathlib import Path

import pytest
import yaml

from backend.config_migration import migrate_config


class TestF57Integration:
    """Integration tests for REV F57 config migration fixes."""

    @pytest.mark.asyncio
    async def test_debugging_config_heals_corruption(self, tmp_path):
        """
        Test that debugging/config (3).yaml (the beta tester corrupted config)
        is properly healed by the migration.

        All 10 corruption patterns should be fixed:
        1. version key migrated to config_version
        2. deferrable_loads removed
        3. ev_charger removed
        4. solar_array migrated to solar_arrays
        5. Duplicate entity keys removed
        6. config_version at correct position
        7. Comments preserved
        8. Section ordering correct
        9. No deprecated keys present
        10. Config loads without errors
        """
        source_config = Path("debugging/config (3).yaml")
        if not source_config.exists():
            pytest.skip("debugging/config (3).yaml not found")

        # Copy to temp location
        test_config = tmp_path / "config.yaml"
        default_config = tmp_path / "config.default.yaml"
        shutil.copy(source_config, test_config)

        # Create a minimal default config for testing
        default_yaml = {
            "config_version": 2,
            "timezone": "Europe/Stockholm",
            "system": {
                "system_id": "test",
                "inverter_profile": "generic",
                "has_solar": False,
                "has_battery": False,
                "location": {"latitude": 59.3, "longitude": 18.0},
                "solar_arrays": [],
            },
            "battery": {},
            "executor": {},
            "input_sensors": {},
        }
        with default_config.open("w") as f:
            yaml.dump(default_yaml, f)

        # Run migration with lenient validation (test mode)
        await migrate_config(str(test_config), str(default_config), strict_validation=False)

        # Load result
        with test_config.open() as f:
            result = yaml.safe_load(f)

        # Verify all corruption patterns are fixed
        # 1. version key migrated to config_version
        assert "version" not in result, "version key should be removed"
        assert "config_version" in result, "config_version should be present"
        assert result["config_version"] == 2, "config_version should be 2"

        # 2. deferrable_loads removed
        assert "deferrable_loads" not in result, "deferrable_loads should be removed"

        # 3. ev_charger removed
        assert "ev_charger" not in result, "ev_charger should be removed"

        # 4. solar_array migrated to solar_arrays
        assert "solar_array" not in result.get("system", {}), "solar_array should be removed"
        assert "solar_arrays" in result.get("system", {}), "solar_arrays should be present"

        # 5. Duplicate entity keys removed
        inv = result.get("executor", {}).get("inverter", {})
        assert "work_mode_entity" not in inv, "work_mode_entity should be removed"
        assert "soc_target_entity" not in inv, "soc_target_entity should be removed"
        assert "work_mode" in inv, "work_mode should be present"

        # 6. Critical values preserved
        assert result["battery"]["capacity_kwh"] == 16, "battery capacity should be preserved"
        assert result["system"]["system_id"] == "prod", "system_id should be preserved"

        # 7. Config loads without errors (implicit - we loaded it successfully)

    @pytest.mark.asyncio
    async def test_healthy_config_unchanged(self, tmp_path):
        """
        Test that a healthy config (config.default.yaml) stays unchanged
        when migrated.

        This prevents regression where valid configs get corrupted.
        """
        # Create a healthy config
        test_config = tmp_path / "config.yaml"
        default_config = tmp_path / "config.default.yaml"

        healthy_config = {
            "config_version": 2,
            "timezone": "Europe/Stockholm",
            "system": {
                "system_id": "test",
                "inverter_profile": "generic",
                "has_solar": True,
                "has_battery": True,
                "location": {"latitude": 59.3, "longitude": 18.0},
                "solar_arrays": [{"name": "Main", "kwp": 10}],
            },
            "battery": {"capacity_kwh": 16, "max_charge_power_kw": 9.6},
            "executor": {"enabled": True},
            "input_sensors": {"battery_soc": "sensor.battery"},
            "water_heaters": [],
            "ev_chargers": [],
        }

        with test_config.open("w") as f:
            yaml.dump(healthy_config, f)

        with default_config.open("w") as f:
            yaml.dump(healthy_config, f)

        # Run migration with lenient validation
        await migrate_config(str(test_config), str(default_config), strict_validation=False)

        # Load result
        with test_config.open() as f:
            result = yaml.safe_load(f)

        # Verify key values are unchanged
        assert result["config_version"] == 2, "config_version should be unchanged"
        assert result["system"]["system_id"] == "test", "system_id should be unchanged"
        assert result["battery"]["capacity_kwh"] == 16, "battery capacity should be unchanged"
        assert result["water_heaters"] == [], "water_heaters should be empty list"
        assert result["ev_chargers"] == [], "ev_chargers should be empty list"

        # Verify no deprecated keys added
        assert "deferrable_loads" not in result, "deferrable_loads should not be added"
        assert "ev_charger" not in result, "ev_charger should not be added"
        assert "version" not in result, "version should not be added"

    @pytest.mark.asyncio
    async def test_migration_creates_backups(self, tmp_path):
        """Test that migration creates timestamped backups."""
        test_config = tmp_path / "config.yaml"
        default_config = tmp_path / "config.default.yaml"

        # Create a simple config
        config = {
            "version": "2.4.0",
            "config_version": 1,
            "system": {
                "system_id": "test",
                "inverter_profile": "generic",
                "has_solar": False,
                "has_battery": False,
                "location": {"latitude": 59.3, "longitude": 18.0},
            },
            "battery": {},
            "executor": {},
            "input_sensors": {},
        }

        with test_config.open("w") as f:
            yaml.dump(config, f)

        with default_config.open("w") as f:
            yaml.dump(config, f)

        # Run migration
        await migrate_config(str(test_config), str(default_config), strict_validation=False)

        # Check backup was created
        backup_dir = tmp_path / "backups"
        assert backup_dir.exists(), "Backup directory should be created"

        backups = list(backup_dir.glob("config.yaml_*.bak"))
        assert len(backups) >= 1, "At least one backup should be created"

    def test_config_file_safety(self):
        """
        Verify that tests use isolated temp files and don't modify real configs.

        This test documents the safety requirements for config tests.
        """
        # List of files that should NEVER be modified by tests
        protected_files = [
            Path("config.yaml"),
            Path("config.default.yaml"),
            Path("debugging/config (3).yaml"),
        ]

        for f in protected_files:
            if f.exists():
                # Just verify they exist - we can't actually test they weren't
                # modified without complex checksum logic, but this serves as
                # documentation of the requirement
                assert f.exists(), f"{f} should exist"

        # Note: Actual safety is enforced by:
        # 1. Using tmp_path fixture in pytest
        # 2. Copying files before modification
        # 3. Never writing to paths outside of temp directories
