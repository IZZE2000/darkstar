import asyncio
import shutil
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from backend.learning.models import Base


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up a clean test environment with a temporary database and config for CI."""
    # 1. Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    db_path = data_dir / "test_planner.db"
    config_path = Path("config.yaml")
    config_backup = Path("config.yaml.bak_test")

    # 2. Backup existing config if it exists
    if config_path.exists():
        shutil.copy2(config_path, config_backup)

    # 3. Create a minimal test config
    test_config = """
version: 2.5.1-beta
timezone: "Europe/Stockholm"
learning:
  enable: true
  sqlite_path: "data/test_planner.db"
  horizon_days: 2
forecasting:
  active_forecast_version: aurora
input_sensors:
  battery_soc: 'sensor.test_soc'
"""
    config_path.write_text(test_config, encoding="utf-8")

    # 4. Initialize Database Schema
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async def init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Run init
    try:
        asyncio.run(init_db())
    except Exception as e:
        print(f"Warning during test DB init: {e}")

    yield

    # 5. Cleanup
    try:
        if db_path.exists():
            db_path.unlink()
    except Exception:
        pass

    # Restore config
    if config_backup.exists():
        if config_path.exists():
            config_path.unlink()
        shutil.move(str(config_backup), str(config_path))
    else:
        # If no config existed before, remove the test one
        if config_path.exists():
            config_path.unlink()
