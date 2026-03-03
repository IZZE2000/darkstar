"""Tests for inputs.py HA client - regression test for resource management.

This test ensures httpx.AsyncClient resources are properly closed after use
to prevent resource leaks when fetching HA data.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_ha_entity_state_uses_async_context_manager():
    """Verify that get_ha_entity_state() uses async with for proper resource cleanup.

    This is a regression test for the resource leak bug where httpx.AsyncClient
    instances were created but never closed, causing socket/connection pool leaks.

    The fix: Use `async with httpx.AsyncClient() as client:` to ensure
    automatic cleanup via context manager.
    """
    from inputs import get_ha_entity_state

    # Mock the response
    mock_response = MagicMock()
    mock_response.json.return_value = {"state": "10.5", "attributes": {}}
    mock_response.raise_for_status = MagicMock()

    # Mock the client context manager
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value = mock_client

        # Call the function
        result = await get_ha_entity_state("sensor.test")

        # Verify AsyncClient was created with context manager
        mock_async_client.assert_called_once()
        mock_client.__aenter__.assert_called_once()
        mock_client.__aexit__.assert_called_once()
        mock_client.get.assert_called_once()

        # Verify response was processed
        assert result is not None
        assert result["state"] == "10.5"


@pytest.mark.asyncio
async def test_get_ha_entity_state_closes_client_on_exception():
    """Verify that client is closed even when exceptions occur.

    This ensures resource cleanup happens in both success and error cases.
    """
    from inputs import get_ha_entity_state

    # Mock the client that raises an exception
    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value = mock_client

        # Call the function - should not raise, should return None
        result = await get_ha_entity_state("sensor.test")

        # Verify context manager was used even on exception
        mock_client.__aenter__.assert_called_once()
        mock_client.__aexit__.assert_called_once()

        # Function should return None on error
        assert result is None


@pytest.mark.asyncio
async def test_get_load_profile_from_ha_uses_async_context_manager():
    """Verify that get_load_profile_from_ha() uses async with for proper resource cleanup.

    This function fetches historical load data and also needs proper client cleanup.
    """
    from inputs import get_load_profile_from_ha

    # Mock the response with empty data (will trigger fallback)
    mock_response = MagicMock()
    mock_response.json.return_value = [[]]  # Empty history data
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value = mock_client

        # Mock HA config to have valid credentials
        with patch("inputs.load_home_assistant_config") as mock_load_config:
            mock_load_config.return_value = {
                "url": "http://homeassistant:8123",
                "token": "test_token",
                "consumption_entity_id": "sensor.test_consumption",
            }

            # Mock config
            config = {
                "timezone": "Europe/Stockholm",
                "input_sensors": {"total_load_consumption": "sensor.test_consumption"},
            }

            # Call the function
            result = await get_load_profile_from_ha(config)

            # Verify AsyncClient was used with context manager
            mock_async_client.assert_called_once()
            mock_client.__aenter__.assert_called_once()
            mock_client.__aexit__.assert_called_once()

            # Should return a list of 96 values
            assert isinstance(result, list)
            assert len(result) == 96  # 96 slots for 24 hours
