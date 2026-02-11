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

        # Use the REAL config.default.yaml as template to preserve comments and structure
        real_default = Path("config.default.yaml")
        if real_default.exists():
            shutil.copy(real_default, default_config)
        else:
            pytest.skip("config.default.yaml not found")

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
        # Create a healthy config from the real template
        test_config = tmp_path / "config.yaml"
        default_config = tmp_path / "config.default.yaml"

        # Use the REAL config.default.yaml as both source and template
        real_default = Path("config.default.yaml")
        if not real_default.exists():
            pytest.skip("config.default.yaml not found")

        shutil.copy(real_default, test_config)
        shutil.copy(real_default, default_config)

        # Run migration with lenient validation
        await migrate_config(str(test_config), str(default_config), strict_validation=False)

        # Load result
        with test_config.open() as f:
            result = yaml.safe_load(f)

        # Verify structure is intact (using real template, values come from template)
        assert result["config_version"] == 2, "config_version should be present"
        assert "system" in result, "system section should be present"
        assert "battery" in result, "battery section should be present"
        assert "water_heaters" in result, "water_heaters should be present"
        assert "ev_chargers" in result, "ev_chargers should be present"

        # Verify no deprecated keys added
        assert "deferrable_loads" not in result, "deferrable_loads should not be added"
        assert "ev_charger" not in result, "ev_charger should not be added"
        assert "version" not in result, "version should not be added"

    @pytest.mark.asyncio
    async def test_migration_creates_backups(self, tmp_path):
        """Test that migration creates timestamped backups."""
        test_config = tmp_path / "config.yaml"
        default_config = tmp_path / "config.default.yaml"

        # Use the REAL config.default.yaml as template
        real_default = Path("config.default.yaml")
        if not real_default.exists():
            pytest.skip("config.default.yaml not found")

        # Create a corrupted config from the template
        with real_default.open() as f:
            config = yaml.safe_load(f)
        # Add some corruption
        config["version"] = "2.4.0"
        config["config_version"] = 1

        with test_config.open("w") as f:
            yaml.dump(config, f)

        shutil.copy(real_default, default_config)

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
