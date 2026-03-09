from pathlib import Path
from unittest.mock import patch

import pytest

import inputs


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up a clean test environment with mocked config for CI."""
    # 1. Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    db_path = data_dir / "test_planner.db"

    # 2. Define test config
    test_config = {
        "version": "2.5.1-beta",
        "timezone": "Europe/Stockholm",
        "learning": {
            "enable": True,
            "sqlite_path": "data/test_planner.db",
            "horizon_days": 2,
        },
        "forecasting": {
            "active_forecast_version": "aurora",
        },
        "input_sensors": {
            "battery_soc": "sensor.test_soc",
        },
    }

    # 3. Monkey-patch load_yaml to return test config
    original_load_yaml = inputs.load_yaml

    def mock_load_yaml(path: str) -> dict:
        if path == "config.yaml":
            return test_config
        return original_load_yaml(path)

    with patch.object(inputs, "load_yaml", mock_load_yaml):
        yield

    # 4. Cleanup - remove test database
    try:
        if db_path.exists():
            db_path.unlink()
    except Exception:
        pass
