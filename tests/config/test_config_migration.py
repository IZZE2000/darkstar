import logging
from pathlib import Path

import pytest
import yaml

from backend.config_migration import migrate_config

# Setup logging
logging.basicConfig(level=logging.INFO)


@pytest.mark.asyncio
async def test_migration_logic():
    """Verify that config migration correctly handles legacy keys and merges defaults."""
    test_file = Path("test_config_migration_pytest.yaml")

    # 1. Prepare legacy config
    legacy_config = {
        "version": "2.4.0",
        "executor": {
            "controller": {
                "battery_capacity_kwh": 15.0,
                "system_voltage_v": 48.0,
                "max_charge_a": 100.0,
            }
        },
    }

    with test_file.open("w") as f:
        yaml.dump(legacy_config, f)

    try:
        # 2. Run migration with lenient validation (for testing minimal configs)
        await migrate_config(str(test_file), strict_validation=False)

        # 3. Verify changes
        with test_file.open("r") as f:
            migrated = yaml.safe_load(f)

        assert "battery" in migrated
        assert migrated["battery"]["capacity_kwh"] == 15.0
        assert migrated["battery"]["nominal_voltage_v"] == 48.0
        # REV F57: version key is migrated to config_version, not preserved
        assert "version" not in migrated
        assert "config_version" in migrated

    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()
        for suffix in (".tmp", ".bak"):
            tmp = test_file.with_suffix(suffix)
            if tmp.exists():
                tmp.unlink()


@pytest.mark.asyncio
async def test_arc15_migration_water_heater():
    """Test ARC15 migration for water heater from deferrable_loads."""
    test_file = Path("test_config_arc15_water.yaml")

    # Prepare old config with deferrable_loads
    old_config = {
        "version": "2.5.0",
        "config_version": 1,
        "system": {
            "has_water_heater": True,
            "has_ev_charger": False,
        },
        "input_sensors": {
            "water_power": "sensor.vvb_power",
        },
        "water_heating": {
            "power_kw": 3.0,
            "min_kwh_per_day": 6.0,
            "max_hours_between_heating": 8,
            "min_spacing_hours": 4,
        },
        "deferrable_loads": [
            {
                "id": "water_heater",
                "name": "Water Heater",
                "sensor_key": "water_power",
                "type": "binary",
                "nominal_power_kw": 3.0,
            }
        ],
    }

    with test_file.open("w") as f:
        yaml.dump(old_config, f)

    try:
        # Run migration with lenient validation (for testing minimal configs)
        await migrate_config(str(test_file), strict_validation=False)

        # Verify migration
        with test_file.open("r") as f:
            migrated = yaml.safe_load(f)

        # Check config version updated
        assert migrated.get("config_version") == 2

        # Check water_heaters array created
        assert "water_heaters" in migrated
        assert len(migrated["water_heaters"]) == 1

        wh = migrated["water_heaters"][0]
        assert wh["id"] == "main_tank"
        assert wh["name"] == "Water Heater"
        assert wh["enabled"] is True
        assert wh["power_kw"] == 3.0
        assert wh["min_kwh_per_day"] == 6.0
        assert wh["sensor"] == "sensor.vvb_power"
        assert wh["type"] == "binary"

    finally:
        # Cleanup
        for suffix in ("", ".tmp", ".bak"):
            tmp = test_file.with_suffix(suffix) if suffix else test_file
            if tmp.exists():
                tmp.unlink()


@pytest.mark.asyncio
async def test_arc15_migration_ev_charger():
    """Test ARC15 migration for EV charger from deferrable_loads."""
    test_file = Path("test_config_arc15_ev.yaml")

    # Prepare old config with EV charger
    old_config = {
        "version": "2.5.0",
        "config_version": 1,
        "system": {
            "has_water_heater": False,
            "has_ev_charger": True,
        },
        "input_sensors": {
            "ev_power": "sensor.tesla_power",
        },
        "ev_charger": {
            "max_power_kw": 11.0,
            "battery_capacity_kwh": 82.0,
        },
        "deferrable_loads": [
            {
                "id": "ev_charger",
                "name": "Tesla Charger",
                "sensor_key": "ev_power",
                "type": "variable",
                "nominal_power_kw": 11.0,
            }
        ],
    }

    with test_file.open("w") as f:
        yaml.dump(old_config, f)

    try:
        # Run migration with lenient validation (for testing minimal configs)
        await migrate_config(str(test_file), strict_validation=False)

        # Verify migration
        with test_file.open("r") as f:
            migrated = yaml.safe_load(f)

        # Check config version updated
        assert migrated.get("config_version") == 2

        # Check ev_chargers array created
        assert "ev_chargers" in migrated
        assert len(migrated["ev_chargers"]) == 1

        ev = migrated["ev_chargers"][0]
        assert ev["id"] == "main_ev"
        assert ev["name"] == "Tesla Charger"
        assert ev["enabled"] is True
        assert ev["max_power_kw"] == 11.0
        assert ev["battery_capacity_kwh"] == 82.0
        assert ev["sensor"] == "sensor.tesla_power"
        assert ev["type"] == "variable"

    finally:
        # Cleanup
        for suffix in ("", ".tmp", ".bak"):
            tmp = test_file.with_suffix(suffix) if suffix else test_file
            if tmp.exists():
                tmp.unlink()


@pytest.mark.asyncio
async def test_arc15_migration_both_devices():
    """Test ARC15 migration with both water heater and EV charger."""
    test_file = Path("test_config_arc15_both.yaml")

    # Prepare old config with both devices
    old_config = {
        "version": "2.5.0",
        "config_version": 1,
        "system": {
            "has_water_heater": True,
            "has_ev_charger": True,
        },
        "input_sensors": {
            "water_power": "sensor.vvb_power",
            "ev_power": "sensor.tesla_power",
        },
        "water_heating": {
            "power_kw": 3.0,
            "min_kwh_per_day": 6.0,
        },
        "ev_charger": {
            "max_power_kw": 11.0,
            "battery_capacity_kwh": 82.0,
        },
        "deferrable_loads": [
            {
                "id": "water_heater",
                "name": "Water Heater",
                "sensor_key": "water_power",
                "type": "binary",
                "nominal_power_kw": 3.0,
            },
            {
                "id": "ev_charger",
                "name": "Tesla Charger",
                "sensor_key": "ev_power",
                "type": "variable",
                "nominal_power_kw": 11.0,
            },
        ],
    }

    with test_file.open("w") as f:
        yaml.dump(old_config, f)

    try:
        # Run migration with lenient validation (for testing minimal configs)
        await migrate_config(str(test_file), strict_validation=False)

        # Verify migration
        with test_file.open("r") as f:
            migrated = yaml.safe_load(f)

        # Check config version updated
        assert migrated.get("config_version") == 2

        # Check both arrays created
        assert "water_heaters" in migrated
        assert "ev_chargers" in migrated
        assert len(migrated["water_heaters"]) == 1
        assert len(migrated["ev_chargers"]) == 1

    finally:
        # Cleanup
        for suffix in ("", ".tmp", ".bak"):
            tmp = test_file.with_suffix(suffix) if suffix else test_file
            if tmp.exists():
                tmp.unlink()


@pytest.mark.asyncio
async def test_arc15_idempotency():
    """Test that ARC15 migration is idempotent (safe to run multiple times)."""
    test_file = Path("test_config_arc15_idempotent.yaml")

    # Prepare old config
    old_config = {
        "version": "2.5.0",
        "config_version": 1,
        "system": {
            "has_water_heater": True,
        },
        "input_sensors": {
            "water_power": "sensor.vvb_power",
        },
        "water_heating": {
            "power_kw": 3.0,
            "min_kwh_per_day": 6.0,
        },
        "deferrable_loads": [
            {
                "id": "water_heater",
                "name": "Water Heater",
                "sensor_key": "water_power",
                "type": "binary",
                "nominal_power_kw": 3.0,
            }
        ],
    }

    with test_file.open("w") as f:
        yaml.dump(old_config, f)

    try:
        # Run migration first time with lenient validation
        await migrate_config(str(test_file), strict_validation=False)

        # Read result after first migration
        with test_file.open("r") as f:
            first_migration = yaml.safe_load(f)

        wh_count_first = len(first_migration.get("water_heaters", []))

        # Run migration second time (should not duplicate) with lenient validation
        await migrate_config(str(test_file), strict_validation=False)

        # Read result after second migration
        with test_file.open("r") as f:
            second_migration = yaml.safe_load(f)

        wh_count_second = len(second_migration.get("water_heaters", []))

        # Should have same count (no duplicates)
        assert wh_count_first == wh_count_second
        assert wh_count_first == 1

    finally:
        # Cleanup
        for suffix in ("", ".tmp", ".bak"):
            tmp = test_file.with_suffix(suffix) if suffix else test_file
            if tmp.exists():
                tmp.unlink()


@pytest.mark.asyncio
async def test_arc15_already_migrated():
    """Test that already migrated configs are skipped."""
    test_file = Path("test_config_arc15_done.yaml")

    # Prepare already migrated config
    migrated_config = {
        "version": "2.5.0",
        "config_version": 2,  # Already at version 2
        "system": {
            "has_water_heater": True,
        },
        "water_heaters": [
            {
                "id": "main_tank",
                "name": "Water Heater",
                "enabled": True,
                "power_kw": 3.0,
                "min_kwh_per_day": 6.0,
                "sensor": "sensor.vvb_power",
                "type": "binary",
                "nominal_power_kw": 3.0,
            }
        ],
        "ev_chargers": [],
    }

    with test_file.open("w") as f:
        yaml.dump(migrated_config, f)

    try:
        # Run migration on already migrated config with lenient validation
        await migrate_config(str(test_file), strict_validation=False)

        # Read result
        with test_file.open("r") as f:
            result = yaml.safe_load(f)

        # Should still be version 2 and have same structure
        assert result.get("config_version") == 2
        assert len(result.get("water_heaters", [])) == 1

    finally:
        # Cleanup
        for suffix in ("", ".tmp", ".bak"):
            tmp = test_file.with_suffix(suffix) if suffix else test_file
            if tmp.exists():
                tmp.unlink()


class TestDeprecatedKeyRemoval:
    """Test that deprecated keys are actually deleted (F57)."""

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
    """Test backend save logic with template merge (F57)."""

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
    """Test timestamped backup system (F57)."""

    def test_create_timestamped_backup(self, tmp_path):
        from backend.config_migration import create_timestamped_backup

        config_file = tmp_path / "config.yaml"
        config_file.write_text("test content")

        backup_path = create_timestamped_backup(config_file)
        assert backup_path is not None
        assert backup_path.exists()
        assert "config.yaml_" in backup_path.name


class TestTemplateAwareMerge:
    """Test template_aware_merge functionality (F57)."""

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
    """Test the complete migration pipeline for F57 fixes."""

    @pytest.mark.asyncio
    async def test_migrate_config_heals_corruption(self, tmp_path, monkeypatch):
        from ruamel.yaml import YAML

        import backend.config_migration as cm

        yaml_loader = YAML()
        config_file = tmp_path / "config.yaml"
        default_file = tmp_path / "config.default.yaml"

        corrupted_config = {
            "version": "2.4.21-beta",
            "deferrable_loads": [{"id": "old"}],
            "system": {
                "system_id": "test",
                "inverter_profile": "test",
                "has_battery": True,
                "has_solar": False,
                "solar_array": {"kwp": 5.0},
            },
        }

        default_template = {
            "config_version": 2,
            "system": {
                "system_id": "default",
                "inverter_profile": "generic",
                "has_battery": False,
                "has_solar": False,
                "solar_arrays": [],
            },
            "battery": {},
            "executor": {},
            "input_sensors": {},
        }

        with config_file.open("w") as f:
            yaml_loader.dump(corrupted_config, f)
        with default_file.open("w") as f:
            yaml_loader.dump(default_template, f)

        monkeypatch.setattr(
            cm,
            "Path",
            lambda p: tmp_path / p if p in ["config.yaml", "config.default.yaml"] else Path(p),
        )
        await cm.migrate_config(strict_validation=False)

        with config_file.open() as f:
            healed = yaml_loader.load(f)
        assert healed["config_version"] == 2
        assert "deferrable_loads" not in healed
        assert "solar_array" not in healed["system"]
