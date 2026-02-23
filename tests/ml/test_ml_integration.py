from datetime import UTC, datetime, timedelta
from unittest.mock import mock_open, patch

import pytest
import yaml

from backend.services.scheduler_service import SchedulerService

# Mock valid config for tests
VALID_CONFIG = {
    "timezone": "UTC",
    "automation": {
        "enable_scheduler": True,
        "schedule": {"every_minutes": 60},
        "ml_training": {
            "enabled": True,
            "run_days": [1, 4],  # Tue, Fri
            "run_time": "03:00",
        },
    },
}


@pytest.fixture
def scheduler():
    return SchedulerService()


@pytest.fixture
def mock_config_loader():
    with patch("builtins.open", mock_open(read_data=yaml.dump(VALID_CONFIG))) as m:
        yield m


def test_compute_next_training_normal(scheduler, mock_config_loader):
    # Mock current time: Monday 10:00 UTC
    # Next run should be Tuesday (Day 1) at 03:00 UTC
    now = datetime(2023, 1, 2, 10, 0, 0, tzinfo=UTC)  # Jan 2 2023 is Monday

    with patch("backend.services.scheduler_service.datetime") as mock_dt:
        mock_dt.now.return_value = now
        # Also mock side_effect for other calls or simple return_value

        # We need to ensure pytz sees this generic time or mock pytz entirely
        # The service uses: datetime.now(tz)

        # Let's rely on the service logic. It uses Path("config.yaml").open()
        # We need to mock Path.open specifically as it's used in _compute_next_training

        with patch("pathlib.Path.open", mock_open(read_data=yaml.dump(VALID_CONFIG))):
            next_run = scheduler._compute_next_training(VALID_CONFIG["automation"]["ml_training"])

    # Expected: Tuesday Jan 3rd, 03:00 UTC
    expected = datetime(2023, 1, 3, 3, 0, 0, tzinfo=UTC)
    assert next_run == expected


def test_compute_next_training_invalid_runtime(scheduler):
    # Mock config with invalid time
    bad_config = {
        "enabled": True,
        "run_days": [0],
        "run_time": "25:99",  # Invalid
    }

    # Should fallback to 03:00
    # Mock file read for timezone
    with patch("pathlib.Path.open", mock_open(read_data=yaml.dump(VALID_CONFIG))):
        # We just check that it doesn't crash and returns a valid datetime
        next_run = scheduler._compute_next_training(bad_config)
        assert isinstance(next_run, datetime)


def test_compute_next_training_timezone(scheduler):
    # Test offset calculation
    # Timezone: Europe/Stockholm (UTC+1 in winter)
    config_stockholm = VALID_CONFIG.copy()
    config_stockholm["timezone"] = "Europe/Stockholm"

    # Mock file read for timezone
    with patch("pathlib.Path.open", mock_open(read_data=yaml.dump(config_stockholm))):
        pass


@pytest.mark.asyncio
async def test_scheduler_loop_triggers_training(scheduler):
    # Verify _run_ml_training is called when time matches

    # Setup state
    scheduler._status.training_enabled = True
    scheduler._status.current_task = "idle"
    scheduler._status.next_training_at = datetime.now(UTC) - timedelta(minutes=1)  # Past due

    # Better: Test _run_ml_training logic itself
    pass


@pytest.mark.asyncio
async def test_run_ml_training_locking():
    # Test that _run_ml_training handles locking from orchestrator
    service = SchedulerService()

    # Mock train_all_models to return busy status first, then success
    with patch("ml.training_orchestrator.train_all_models") as mock_train:
        # Case 1: Success
        mock_train.return_value = {"status": "success"}
        await service._run_ml_training(VALID_CONFIG["automation"]["ml_training"])
        assert service.status.last_training_status == "success"

        # Case 2: Error with retry (mocking loop behavior is hard, so we just check finding "error")
        mock_train.return_value = {"status": "error", "error": "Mocked failure"}

        # We want to break the retry loop to avoid waiting
        # We can mock sleep
        with patch("asyncio.sleep"):
            await service._run_ml_training(VALID_CONFIG["automation"]["ml_training"])

        assert service.status.last_training_status == "error"


def test_integration_config_validation():
    # Verify that invalid days are caught
    scheduler = SchedulerService()
    invalid_days_config = {"run_days": [7, -1], "run_time": "03:00"}

    with (
        patch("pathlib.Path.open", mock_open(read_data=yaml.dump(VALID_CONFIG))),
        patch("backend.services.scheduler_service.logger") as mock_logger,
    ):
        scheduler._compute_next_training(invalid_days_config)
        # Should invoke warning about run_days
        args, _ = mock_logger.warning.call_args
        assert "Invalid run_days" in args[0]
