from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
import pytz

from backend.services.scheduler_service import SchedulerService


@pytest.fixture
def scheduler():
    return SchedulerService()


def test_compute_next_training_basic(scheduler):
    """Test standard next run calculation."""
    # Monday = 0, Tuesday = 1, Wednesday = 2, Thursday = 3, Friday = 4, Saturday = 5, Sunday = 6
    # Config: Mon (0), Thu (3) at 03:00 — weekly mode
    config = {"frequency": "weekly", "run_days": [0, 3], "run_time": "03:00"}

    # Mock timezone to Europe/Stockholm
    with (
        patch("yaml.safe_load", return_value={"timezone": "Europe/Stockholm"}),
        patch("pathlib.Path.open", MagicMock()),
    ):
        # Mock current time to Tuesday 10:00 AM Stockholm
        stockholm = pytz.timezone("Europe/Stockholm")
        now = stockholm.localize(datetime(2024, 1, 2, 10, 0))  # Jan 2, 2024 is Tuesday

        # Use patch to control datetime.now
        with patch("backend.services.scheduler_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromtimestamp = datetime.fromtimestamp
            mock_dt.UTC = UTC

            next_run = scheduler._compute_next_training(config)

            # Should be Thursday Jan 4, 03:00 AM Stockholm
            expected_local = stockholm.localize(datetime(2024, 1, 4, 3, 0))
            expected_utc = expected_local.astimezone(pytz.UTC)

            assert next_run == expected_utc
            assert next_run.weekday() == 3  # Thursday


def test_compute_next_training_today_passed(scheduler):
    """Test that if run_time for today already passed, it picks next day."""
    config = {"frequency": "weekly", "run_days": [1, 3], "run_time": "03:00"}  # Tue, Thu

    with (
        patch("yaml.safe_load", return_value={"timezone": "Europe/Stockholm"}),
        patch("pathlib.Path.open", MagicMock()),
    ):
        stockholm = pytz.timezone("Europe/Stockholm")
        # Mock current time to Tuesday 10:00 AM (03:00 run time already passed)
        now = stockholm.localize(datetime(2024, 1, 2, 10, 0))

        with patch("backend.services.scheduler_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.UTC = UTC

            next_run = scheduler._compute_next_training(config)

            # Should be Thursday Jan 4, 03:00 (since it skips today)
            expected_local = stockholm.localize(datetime(2024, 1, 4, 3, 0))
            assert next_run == expected_local.astimezone(pytz.UTC)


def test_compute_next_training_today_future(scheduler):
    """Test that if run_time for today is in future, it picks today."""
    config = {"frequency": "weekly", "run_days": [1, 3], "run_time": "23:00"}  # Tue, Thu

    with (
        patch("yaml.safe_load", return_value={"timezone": "Europe/Stockholm"}),
        patch("pathlib.Path.open", MagicMock()),
    ):
        stockholm = pytz.timezone("Europe/Stockholm")
        # Mock current time to Tuesday 10:00 AM (23:00 is in the future)
        now = stockholm.localize(datetime(2024, 1, 2, 10, 0))

        with patch("backend.services.scheduler_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.UTC = UTC

            next_run = scheduler._compute_next_training(config)

            # Should be Tuesday Jan 2, 23:00
            expected_local = stockholm.localize(datetime(2024, 1, 2, 23, 0))
            assert next_run == expected_local.astimezone(pytz.UTC)


def test_compute_next_training_invalid_config(scheduler):
    """Test that invalid config falls back to defaults."""
    # Invalid run_days and run_time, no frequency key → defaults to daily
    config = {"run_days": "invalid", "run_time": "99:99"}

    with (
        patch("yaml.safe_load", return_value={"timezone": "Europe/Stockholm"}),
        patch("pathlib.Path.open", MagicMock()),
    ):
        stockholm = pytz.timezone("Europe/Stockholm")
        # Mock current time to Tuesday Jan 2, 10:00 AM
        now = stockholm.localize(datetime(2024, 1, 2, 10, 0))

        with patch("backend.services.scheduler_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.UTC = UTC

            # Default frequency is "daily", invalid run_time falls back to 03:00.
            # Since 03:00 has passed today, next daily run is tomorrow Wed Jan 3 03:00.
            next_run = scheduler._compute_next_training(config)

            expected_local = stockholm.localize(datetime(2024, 1, 3, 3, 0))
            assert next_run == expected_local.astimezone(pytz.UTC)
