"""
Tests for Executor Actions (HAClient and ActionDispatcher)

Tests with mocked HTTP requests to avoid needing a live Home Assistant instance.
"""

from unittest.mock import MagicMock, patch

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

    def test_get_state_success(self):
        """get_state returns parsed JSON on success."""
        with patch("executor.actions.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "entity_id": "switch.test",
                "state": "on",
            }
            mock_session.get.return_value = mock_response

            client = HAClient("http://ha:8123", "token123")
            result = client.get_state("switch.test")

            assert result == {"entity_id": "switch.test", "state": "on"}
            mock_session.get.assert_called_once()

    def test_get_state_failure_returns_none(self):
        """get_state returns None on request error."""
        import requests

        with patch("executor.actions.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_session.get.side_effect = requests.RequestException("Connection error")

            client = HAClient("http://ha:8123", "token123")
            result = client.get_state("switch.test")

            assert result is None

    def test_get_state_value_extracts_state(self):
        """get_state_value returns just the state string."""
        with patch("executor.actions.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_response = MagicMock()
            mock_response.json.return_value = {"state": "Export First"}
            mock_session.get.return_value = mock_response

            client = HAClient("http://ha:8123", "token123")
            result = client.get_state_value("select.work_mode")

            assert result == "Export First"


class TestHAClientCallService:
    """Test HAClient.call_service."""

    def test_call_service_success(self):
        """call_service returns True on success."""
        with patch("executor.actions.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_response = MagicMock()
            mock_session.post.return_value = mock_response

            client = HAClient("http://ha:8123", "token123")
            result = client.call_service("switch", "turn_on", "switch.test")

            assert result is True
            mock_session.post.assert_called_once()

    def test_call_service_failure(self):
        """call_service raises HACallError on request exception (REV F52 Phase 5)."""
        import requests

        with patch("executor.actions.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_session.post.side_effect = requests.RequestException("Failed")

            client = HAClient("http://ha:8123", "token123")

            with pytest.raises(
                HACallError, match=r"Failed to call service switch.turn_on on switch.test"
            ):
                client.call_service("switch", "turn_on", "switch.test")

    def test_set_select_option(self):
        """set_select_option calls select.select_option."""
        with patch("executor.actions.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_response = MagicMock()
            mock_session.post.return_value = mock_response

            client = HAClient("http://ha:8123", "token123")
            client.set_select_option("select.mode", "Export First")

            # Verify the call was made to the correct endpoint
            call_args = mock_session.post.call_args
            assert "select/select_option" in call_args[0][0]

    def test_set_switch_on(self):
        """set_switch(True) calls switch.turn_on."""
        with patch("executor.actions.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_response = MagicMock()
            mock_session.post.return_value = mock_response

            client = HAClient("http://ha:8123", "token123")
            client.set_switch("switch.charging", True)

            call_args = mock_session.post.call_args
            assert "switch/turn_on" in call_args[0][0]

    def test_set_switch_off(self):
        """set_switch(False) calls switch.turn_off."""
        with patch("executor.actions.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_response = MagicMock()
            mock_session.post.return_value = mock_response

            client = HAClient("http://ha:8123", "token123")
            client.set_switch("switch.charging", False)

    def test_set_select_option_input_select(self):
        """set_select_option works with input_select."""
        with patch("executor.actions.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_session.post.return_value = MagicMock()

            client = HAClient("http://ha:8123", "token123")
            result = client.set_select_option("input_select.mode", "Export First")

            assert result is True
            call_args = mock_session.post.call_args
            assert "input_select/select_option" in call_args[0][0]

    def test_set_switch_input_boolean(self):
        """set_switch works with input_boolean."""
        with patch("executor.actions.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_session.post.return_value = MagicMock()

            client = HAClient("http://ha:8123", "token123")
            result = client.set_switch("input_boolean.override", True)

            assert result is True
            call_args = mock_session.post.call_args
            assert "input_boolean/turn_on" in call_args[0][0]

    def test_set_number_input_number(self):
        """set_number works with input_number."""
        with patch("executor.actions.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_session.post.return_value = MagicMock()

            client = HAClient("http://ha:8123", "token123")
            result = client.set_number("input_number.value", 10.0)

            assert result is True
            call_args = mock_session.post.call_args
            assert "input_number/set_value" in call_args[0][0]

    def test_set_input_number_alias(self):
        """set_input_number calls set_number (which handles input_number correctly)."""
        with patch("executor.actions.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_session.post.return_value = MagicMock()

            client = HAClient("http://ha:8123", "token123")
            result = client.set_input_number("input_number.test", 5.0)

            assert result is True
            call_args = mock_session.post.call_args
            assert "input_number/set_value" in call_args[0][0]

    def test_safety_guard_sensor(self):
        """Safety guard prevents controlling sensor entities (raises HACallError REV F52 Phase 5)."""
        client = HAClient("http://ha:8123", "token123")

        with pytest.raises(HACallError, match=r"Invalid domain for select entity sensor.mode"):
            client.set_select_option("sensor.mode", "test")

        with pytest.raises(
            HACallError, match=r"Invalid domain for switch entity binary_sensor.status"
        ):
            client.set_switch("binary_sensor.status", True)

        with pytest.raises(HACallError, match=r"Invalid domain for number entity sensor.value"):
            client.set_number("sensor.value", 10)

    def test_invalid_domain_rejected(self):
        """Rejects domains not in allowed list for specific action (raises HACallError REV F52 Phase 5)."""
        client = HAClient("http://ha:8123", "token123")

        # 'switch' domain is not allowed for set_select_option
        with pytest.raises(HACallError, match=r"Invalid domain for select entity switch.mode"):
            client.set_select_option("switch.mode", "test")


class TestHAClientSendNotification:
    """Test HAClient.send_notification."""

    def test_send_notification_parses_service(self):
        """send_notification correctly parses service name."""
        with patch("executor.actions.requests.Session") as MockSession:
            mock_session = MockSession.return_value
            mock_response = MagicMock()
            mock_session.post.return_value = mock_response

            client = HAClient("http://ha:8123", "token123")
            result = client.send_notification(
                "notify.mobile_app",
                "Test Title",
                "Test Message",
            )

            assert result is True
            call_args = mock_session.post.call_args
            assert "notify/mobile_app" in call_args[0][0]

    def test_send_notification_invalid_format(self):
        """send_notification returns False for invalid service format."""
        with patch("executor.actions.requests.Session"):
            client = HAClient("http://ha:8123", "token123")
            result = client.send_notification("invalid", "Title", "Msg")

            assert result is False
