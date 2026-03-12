import sys
from unittest.mock import AsyncMock, patch

import pytest

from backend.services.planner_service import PlannerService
from backend.services.scheduler_service import SchedulerService

# Ensure bin is in path (though tests usually run from root)
sys.path.append("bin")


@pytest.mark.asyncio
async def test_planner_service_lifecycle():
    service = PlannerService()

    # Patch run_planner.main instead of _run_sync
    with (
        patch("bin.run_planner.main", new_callable=AsyncMock) as mock_main,
        patch.object(PlannerService, "_count_schedule_slots", return_value=48),
    ):
        mock_main.return_value = 0  # Success exit code

        # Test run_once
        result = await service.run_once()
        assert result.success is True
        assert result.slot_count == 48

        # Verify lock is released
        assert not service._lock.locked()


@pytest.mark.asyncio
async def test_planner_service_failure():
    service = PlannerService()
    # Patch run_planner.main to raise exception
    with patch("bin.run_planner.main", new_callable=AsyncMock) as mock_main:
        mock_main.side_effect = Exception("Planner crashed")

        result = await service.run_once()
        # run_once catches exception and returns PlannerResult with success=False
        assert result.success is False
        assert "Planner crashed" in result.error


@pytest.mark.asyncio
async def test_planner_service_error_includes_exception_type():
    """Verify that error payload includes exception type for better debugging.

    This is a regression test for vague error messages that only showed "incomplete format"
    without indicating it was a ValueError.

    The fix: Exception handler now prepends type(e).__name__ to the error message.

    Scenario: Exception Caught in Planner
    WHEN a ValueError is raised during planner execution
    THEN the WebSocket notification includes "ValueError: incomplete format"
    instead of just "incomplete format"
    """
    service = PlannerService()
    # Patch run_planner.main to raise a ValueError
    with patch("bin.run_planner.main", new_callable=AsyncMock) as mock_main:
        mock_main.side_effect = ValueError("incomplete format")

        result = await service.run_once()
        # run_once catches exception and returns PlannerResult with enriched error
        assert result.success is False
        # Error should include the exception type
        assert result.error == "ValueError: incomplete format"
        # Should NOT be just the message without the type
        assert result.error != "incomplete format"


@pytest.mark.asyncio
async def test_scheduler_service_lifecycle():
    scheduler = SchedulerService()

    # Test startup/shutdown
    assert not scheduler.status.running

    # Default is enabled=False until loop starts/config loaded
    assert not scheduler.status.enabled

    # Test starting (mocks loop to prevent infinite run)
    with patch.object(SchedulerService, "_loop"):
        await scheduler.start()
        assert scheduler.status.running
        assert scheduler._task is not None

        # Test stop signal
        await scheduler.stop()
        assert not scheduler.status.running
        assert scheduler._task is None
