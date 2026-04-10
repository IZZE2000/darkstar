"""Shared fixtures for API tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytz


def make_mock_learning_engine() -> MagicMock:
    """Return a MagicMock that satisfies the async SQLAlchemy session pattern used
    by learning-history route handlers, without creating any real aiosqlite connections.

    Routes do:
        async with store.AsyncSession() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()
    """
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar.return_value = 0

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.scalar = AsyncMock(return_value=0)

    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_store = MagicMock()
    mock_store.AsyncSession.return_value = mock_session_ctx

    mock_engine = MagicMock()
    mock_engine.store = mock_store
    # Set timezone to a real pytz object so routes using engine.timezone
    # (e.g. forecast.py aurora_dashboard) get a valid tzinfo, not a MagicMock.
    mock_engine.timezone = pytz.UTC
    # Set db_path to prevent MagicMock filenames when code accesses engine.db_path
    mock_engine.db_path = "data/test_learning.db"
    return mock_engine


@pytest.fixture(autouse=True)
def prevent_real_learning_engine():
    """Patch every call site of ``get_learning_engine`` for all API tests.

    Several routers import ``get_learning_engine`` at module level and store a
    local reference.  Patching only ``backend.learning.get_learning_engine``
    misses those pre-imported names.  We patch them all here so no real
    ``LearningStore`` / aiosqlite engine is created during the API test run,
    preventing ``DeprecationWarning: There is no current event loop`` and
    ``PytestUnhandledThreadExceptionWarning`` caused by aiosqlite background
    threads outliving their per-test event loop.

    We also prevent the real ExecutorEngine from starting, which would open a
    real aiohttp.ClientSession to Home Assistant (via secrets.yaml) and leave
    it unclosed at interpreter shutdown.
    """
    mock_engine = make_mock_learning_engine()
    with (
        # Module-level import (deferred importers and direct callers)
        patch("backend.learning.get_learning_engine", return_value=mock_engine),
        # forecast.py and debug.py import at module level
        patch("backend.api.routers.forecast.get_learning_engine", return_value=mock_engine),
        patch("backend.api.routers.debug.get_learning_engine", return_value=mock_engine),
        # ml.api re-exports get_engine which wraps get_learning_engine
        patch("ml.api.get_engine", return_value=mock_engine),
        patch("ml.api.get_learning_engine", return_value=mock_engine),
        # backfill.py imports get_learning_engine at module level; called by recorder_service
        patch("backend.learning.backfill.get_learning_engine", return_value=mock_engine),
        # recorder.py creates LearningStore directly in backfill_missing_prices()
        patch("backend.recorder.LearningStore", return_value=mock_engine.store),
        # Prevent the real ExecutorEngine from starting and opening a live
        # aiohttp.ClientSession to Home Assistant via secrets.yaml.
        # Must patch the pre-imported name in backend.main (not the origin module)
        # because main.py does `from backend.api.routers.executor import get_executor_instance`.
        patch("backend.main.get_executor_instance", return_value=None),
        # Prevent the real HA WebSocket client from starting. It connects to the live
        # HA instance via secrets.yaml; the background thread can outlive the test's
        # event loop and produce RuntimeWarning: coroutine was never awaited.
        patch("backend.ha_socket.start_ha_socket_client"),
    ):
        yield
