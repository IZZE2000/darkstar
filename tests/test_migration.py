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
        # 2. Run migration
        await migrate_config(str(test_file))

        # 3. Verify changes
        with test_file.open("r") as f:
            migrated = yaml.safe_load(f)

        assert "battery" in migrated
        assert migrated["battery"]["capacity_kwh"] == 15.0
        assert migrated["battery"]["nominal_voltage_v"] == 48.0
        assert "version" in migrated

    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()
        for suffix in (".tmp", ".bak"):
            tmp = test_file.with_suffix(suffix)
            if tmp.exists():
                tmp.unlink()


if __name__ == "__main__":
    asyncio.run(test_migration_logic())
