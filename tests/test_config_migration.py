import asyncio
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


if __name__ == "__main__":
    asyncio.run(test_migration_logic())
