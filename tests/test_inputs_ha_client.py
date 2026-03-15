"""Tests for inputs.py HA client - regression test for resource management.

This test ensures httpx.AsyncClient resources are properly closed after use
to prevent resource leaks when fetching HA data.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_ev_soc_fallback_logging_no_crash():
    """Verify that EV SoC fallback logging with '0%%' does not crash due to formatting.

    This is a regression test for the ValueError: incomplete format bug where
    the logging statement in get_initial_state() contained an unescaped percent sign.

    The fix: Escape the percent sign as '0%%' so Python's logging percent-formatting
    interprets it as a literal '%' character.

    Scenario: Logging EV SoC fallback
    WHEN EV SoC sensor returns no data
    THEN the system logs a warning with the literal "0%" without crashing
    """

    from backend.core.ha_client import get_initial_state

    # Config with EV charger enabled but sensor returns no data
    test_config = {
        "system": {"has_ev_charger": True, "battery": {"capacity_kwh": 10.0}},
        "ev_chargers": [
            {
                "enabled": True,
                "soc_sensor": "sensor.test_ev_soc",
                "plug_sensor": "sensor.test_ev_plug",
            }
        ],
        "input_sensors": {"battery_soc": "sensor.battery_soc"},
    }

    # Track if the warning was called with proper format
    warning_calls = []

    def mock_yaml_load(f):
        return test_config

    with (
        patch("yaml.safe_load", side_effect=mock_yaml_load),
        patch("backend.core.ha_client.get_ha_sensor_float") as mock_get_sensor,
        patch("backend.core.ha_client.logger") as mock_logger,
    ):
        # Battery SoC returns valid data
        mock_get_sensor.side_effect = lambda entity_id: {
            "sensor.battery_soc": 50.0,
            "sensor.test_ev_soc": None,  # EV SoC returns no data
            "sensor.test_ev_plug": False,
        }.get(entity_id)

        mock_logger.warning = lambda msg, *args: warning_calls.append((msg, args))

        # This should NOT raise ValueError: incomplete format
        result = await get_initial_state()

        # Verify the warning was logged with 0%%
        ev_soc_warnings = [call for call in warning_calls if "defaulting to" in call[0]]
        assert len(ev_soc_warnings) == 1
        assert "0%%" in ev_soc_warnings[0][0]  # Format string has escaped %%

        # Verify result has default EV SoC of 0
        assert result["ev_soc_percent"] == 0.0


@pytest.mark.asyncio
async def test_get_ha_entity_state_uses_async_context_manager():
    """Verify that get_ha_entity_state() uses async with for proper resource cleanup.

    This is a regression test for the resource leak bug where httpx.AsyncClient
    instances were created but never closed, causing socket/connection pool leaks.

    The fix: Use `async with httpx.AsyncClient() as client:` to ensure
    automatic cleanup via context manager.
    """
    from backend.core.ha_client import get_ha_entity_state

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
    from backend.core.ha_client import get_ha_entity_state

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
    from backend.core.ha_client import get_load_profile_from_ha

    # Mock the response with empty data (will trigger fallback)
    mock_response = MagicMock()
    mock_response.json.return_value = [[]]  # Empty history data
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    # Mock config
    config = {
        "timezone": "Europe/Stockholm",
        "input_sensors": {"total_load_consumption": "sensor.test_consumption"},
    }

    with (
        patch("httpx.AsyncClient") as mock_async_client,
        patch("backend.core.secrets.load_home_assistant_config") as mock_load_config,
    ):
        mock_async_client.return_value = mock_client
        mock_load_config.return_value = {
            "url": "http://homeassistant:8123",
            "token": "test_token",
            "consumption_entity_id": "sensor.test_consumption",
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
