"""
Tests for Executor Actions (HAClient and ActionDispatcher)

Tests with mocked HTTP requests to avoid needing a live Home Assistant instance.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from executor.actions import ActionResult, HACallError, HAClient


class TestActionResult:
    """Test the ActionResult dataclass."""

    def test_required_fields(self):
        """ActionResult requires action_type and success."""
        result = ActionResult(action_type="work_mode", success=True)
        assert result.action_type == "work_mode"
        assert result.success is True

    def test_default_values(self):
        """ActionResult has sensible defaults."""
        result = ActionResult(action_type="test", success=True)
        assert result.message == ""
        assert result.previous_value is None
        assert result.new_value is None
        assert result.skipped is False
        assert result.duration_ms == 0


class TestHAClientGetState:
    """Test HAClient.get_state and get_state_value."""

    @pytest.mark.asyncio
    async def test_get_state_success(self):
        """get_state returns parsed JSON on success."""
        client = HAClient("http://ha:8123", "token123")

        # Create mock response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(
            return_value={
                "entity_id": "switch.test",
                "state": "on",
            }
        )
        mock_response.raise_for_status = MagicMock()

        # Create mock session that returns mock_response as context manager
        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_cm

        # Patch _get_session to return our mock
        with patch.object(client, "_get_session", return_value=mock_session):
            result = await client.get_state("switch.test")
            assert result == {"entity_id": "switch.test", "state": "on"}

    @pytest.mark.asyncio
    async def test_get_state_failure_returns_none(self):
        """get_state returns None on request error."""
        client = HAClient("http://ha:8123", "token123")

        # Create mock session that raises an error
        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection error"))
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_cm

        with patch.object(client, "_get_session", return_value=mock_session):
            result = await client.get_state("switch.test")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_state_value_extracts_state(self):
        """get_state_value returns just the state string."""
        client = HAClient("http://ha:8123", "token123")

        # Create mock response
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"state": "Export First"})
        mock_response.raise_for_status = MagicMock()

        # Create mock session
        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_cm

        with patch.object(client, "_get_session", return_value=mock_session):
            result = await client.get_state_value("select.work_mode")
            assert result == "Export First"


class TestHAClientCallService:
    """Test HAClient.call_service."""

    @pytest.mark.asyncio
    async def test_call_service_success(self):
        """call_service returns True on success."""
        client = HAClient("http://ha:8123", "token123")

        # Create mock response
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        # Create mock session
        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_cm

        with patch.object(client, "_get_session", return_value=mock_session):
            result = await client.call_service("switch", "turn_on", "switch.test")
            assert result is True

    @pytest.mark.asyncio
    async def test_call_service_failure(self):
        """call_service raises HACallError on request exception (REV F52 Phase 5)."""
        client = HAClient("http://ha:8123", "token123")

        # Create mock session that raises an error
        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection refused"))
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_cm

        with patch.object(client, "_get_session", return_value=mock_session):
            with pytest.raises(HACallError) as exc_info:
                await client.call_service("switch", "turn_on", "switch.test")

            assert exc_info.value.exception_type == "ClientError"


class TestHAClientSetMethods:
    """Test HAClient setter methods."""

    @pytest.mark.asyncio
    async def test_set_select_option(self):
        """set_select_option calls select_option service."""
        client = HAClient("http://ha:8123", "token123")

        # Create mock response
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        # Create mock session
        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_cm

        with patch.object(client, "_get_session", return_value=mock_session):
            result = await client.set_select_option("select.mode", "Self Use")
            assert result is True

    @pytest.mark.asyncio
    async def test_set_switch(self):
        """set_switch calls turn_on/turn_off service."""
        client = HAClient("http://ha:8123", "token123")

        # Create mock response
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        # Create mock session
        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_cm

        with patch.object(client, "_get_session", return_value=mock_session):
            result = await client.set_switch("switch.test", True)
            assert result is True

    @pytest.mark.asyncio
    async def test_set_number(self):
        """set_number calls set_value service."""
        client = HAClient("http://ha:8123", "token123")

        # Create mock response
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        # Create mock session
        mock_session = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_cm

        with patch.object(client, "_get_session", return_value=mock_session):
            result = await client.set_number("number.soc_target", 80.0)
            assert result is True


class TestHAClientValidation:
    """Test HAClient input validation."""

    @pytest.mark.asyncio
    async def test_get_state_with_none_entity(self):
        """get_state returns None for None entity_id."""
        client = HAClient("http://ha:8123", "token123")
        result = await client.get_state(None)  # type: ignore[arg-type]
        assert result is None

    @pytest.mark.asyncio
    async def test_get_state_with_empty_entity(self):
        """get_state returns None for empty entity_id."""
        client = HAClient("http://ha:8123", "token123")
        result = await client.get_state("")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_state_with_whitespace_entity(self):
        """get_state returns None for whitespace-only entity_id."""
        client = HAClient("http://ha:8123", "token123")
        result = await client.get_state("   ")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_state_with_literal_none_string(self):
        """get_state returns None for literal 'None' string."""
        client = HAClient("http://ha:8123", "token123")
        result = await client.get_state("None")
        assert result is None


class TestHAClientSafetyGuards:
    """Test HAClient safety guards."""

    @pytest.mark.asyncio
    async def test_cannot_control_sensor_entity(self):
        """Safety guard prevents controlling sensor entities."""
        client = HAClient("http://ha:8123", "token123")

        with pytest.raises(HACallError) as exc_info:
            await client.set_number("sensor.temperature", 25.0)

        assert (
            "read-only" in str(exc_info.value).lower()
            or "invalid domain" in str(exc_info.value).lower()
        )

    @pytest.mark.asyncio
    async def test_cannot_control_binary_sensor(self):
        """Safety guard prevents controlling binary_sensor entities."""
        client = HAClient("http://ha:8123", "token123")

        with pytest.raises(HACallError) as exc_info:
            await client.set_switch("binary_sensor.motion", True)

        assert (
            "read-only" in str(exc_info.value).lower()
            or "invalid domain" in str(exc_info.value).lower()
        )
