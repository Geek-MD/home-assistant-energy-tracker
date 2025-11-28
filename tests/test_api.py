"""Tests for the Energy Tracker API client."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientError
from homeassistant.exceptions import HomeAssistantError

from custom_components.energy_tracker.api import EnergyTrackerApi
from custom_components.energy_tracker.const import DOMAIN


class TestEnergyTrackerApiInit:
    """Test EnergyTrackerApi initialization."""

    def test_init_stores_hass_and_token(self, mock_hass, api_token):
        """Test that __init__ stores hass and token."""
        # Arrange & Act
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)

        # Assert
        assert api._hass == mock_hass
        assert api._token == api_token


class TestGetHeaders:
    """Test _get_headers method."""

    def test_get_headers_returns_correct_structure(self, mock_hass, api_token):
        """Test that headers include Bearer token and correct content types."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)

        # Act
        headers = api._get_headers()

        # Assert
        assert headers["Authorization"] == f"Bearer {api_token}"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"


class TestParseErrorMessage:
    """Test _parse_error_message method."""

    @pytest.mark.asyncio
    async def test_parse_error_message_string(self, mock_hass, api_token):
        """Test parsing error message from string."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)
        resp = AsyncMock()
        resp.json.return_value = {"message": "Error message"}

        # Act
        result = await api._parse_error_message(resp)

        # Assert
        assert result == "Error message"

    @pytest.mark.asyncio
    async def test_parse_error_message_list(self, mock_hass, api_token):
        """Test parsing error message from list."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)
        resp = AsyncMock()
        resp.json.return_value = {"message": ["Error 1", "Error 2", "Error 3"]}

        # Act
        result = await api._parse_error_message(resp)

        # Assert
        assert result == "Error 1; Error 2; Error 3"

    @pytest.mark.asyncio
    async def test_parse_error_message_list_with_empty_strings(
        self, mock_hass, api_token
    ):
        """Test parsing error message list filters empty strings."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)
        resp = AsyncMock()
        resp.json.return_value = {"message": ["Error 1", "", "Error 2", None]}

        # Act
        result = await api._parse_error_message(resp)

        # Assert
        assert result == "Error 1; Error 2"

    @pytest.mark.asyncio
    async def test_parse_error_message_no_message_key(self, mock_hass, api_token):
        """Test parsing returns None when no message key."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)
        resp = AsyncMock()
        resp.json.return_value = {"error": "something"}

        # Act
        result = await api._parse_error_message(resp)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_parse_error_message_json_exception(self, mock_hass, api_token):
        """Test parsing returns None on JSON exception."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)
        resp = AsyncMock()
        resp.json.side_effect = Exception("JSON parse error")

        # Act
        result = await api._parse_error_message(resp)

        # Assert
        assert result is None


class TestHandleErrorResponse:
    """Test _handle_error_response method."""

    def test_handle_400_bad_request(self, mock_hass, api_token, mock_issue_registry):
        """Test 400 Bad Request raises HomeAssistantError with translation."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)

        # Act & Assert
        with pytest.raises(HomeAssistantError) as exc_info:
            api._handle_error_response("[test]", 400, "Invalid value", None)

        assert exc_info.value.translation_domain == DOMAIN
        assert exc_info.value.translation_key == "bad_request"
        assert exc_info.value.translation_placeholders["error"] == "Invalid value"

    def test_handle_401_unauthorized_creates_issue(
        self, mock_hass, api_token, mock_issue_registry
    ):
        """Test 401 Unauthorized creates issue and raises error."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)

        # Act & Assert
        with pytest.raises(HomeAssistantError) as exc_info:
            api._handle_error_response("[test]", 401, None, None)

        # Assert issue was created
        mock_issue_registry.assert_called_once()
        call_args = mock_issue_registry.call_args
        assert call_args[0][0] == mock_hass
        assert call_args[0][1] == DOMAIN
        assert call_args[1]["translation_key"] == "auth_error_invalid_token"

        # Assert exception
        assert exc_info.value.translation_key == "auth_failed"

    def test_handle_403_forbidden_creates_issue(
        self, mock_hass, api_token, mock_issue_registry
    ):
        """Test 403 Forbidden creates issue and raises error."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)

        # Act & Assert
        with pytest.raises(HomeAssistantError) as exc_info:
            api._handle_error_response("[test]", 403, None, None)

        # Assert issue was created
        mock_issue_registry.assert_called_once()
        call_args = mock_issue_registry.call_args
        assert call_args[1]["translation_key"] == "auth_error_insufficient_permissions"

        # Assert exception
        assert exc_info.value.translation_key == "auth_failed"

    def test_handle_404_not_found(self, mock_hass, api_token, mock_issue_registry):
        """Test 404 Not Found raises device_not_found error."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)

        # Act & Assert
        with pytest.raises(HomeAssistantError) as exc_info:
            api._handle_error_response("[test]", 404, None, None)

        assert exc_info.value.translation_key == "device_not_found"

    def test_handle_429_rate_limit_with_retry_after(
        self, mock_hass, api_token, mock_issue_registry
    ):
        """Test 429 Rate Limit with Retry-After header."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)
        headers = {"Retry-After": "60"}

        # Act & Assert
        with pytest.raises(HomeAssistantError) as exc_info:
            api._handle_error_response("[test]", 429, None, headers)

        assert exc_info.value.translation_key == "rate_limit"
        assert exc_info.value.translation_placeholders["retry_after"] == "60"

    def test_handle_429_rate_limit_without_retry_after(
        self, mock_hass, api_token, mock_issue_registry
    ):
        """Test 429 Rate Limit without Retry-After header."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)

        # Act & Assert
        with pytest.raises(HomeAssistantError) as exc_info:
            api._handle_error_response("[test]", 429, None, None)

        assert exc_info.value.translation_key == "rate_limit_no_time"

    def test_handle_429_rate_limit_with_invalid_retry_after(
        self, mock_hass, api_token, mock_issue_registry
    ):
        """Test 429 Rate Limit with invalid Retry-After header."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)
        headers = {"Retry-After": "invalid-value"}

        # Act & Assert
        with pytest.raises(HomeAssistantError) as exc_info:
            api._handle_error_response("[test]", 429, None, headers)

        assert exc_info.value.translation_key == "rate_limit_no_time"

    def test_handle_500_server_error(self, mock_hass, api_token, mock_issue_registry):
        """Test 500 Server Error raises server_error."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)

        # Act & Assert
        with pytest.raises(HomeAssistantError) as exc_info:
            api._handle_error_response("[test]", 500, "Database error", None)

        assert exc_info.value.translation_key == "server_error"
        assert exc_info.value.translation_placeholders["error"] == "Database error"

    def test_handle_unknown_error(self, mock_hass, api_token, mock_issue_registry):
        """Test unknown HTTP error code."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)

        # Act & Assert
        with pytest.raises(HomeAssistantError) as exc_info:
            api._handle_error_response("[test]", 418, "I'm a teapot", None)

        assert exc_info.value.translation_key == "unknown_error"
        assert exc_info.value.translation_placeholders["error"] == "I'm a teapot"


class TestHandleConnectionError:
    """Test _handle_connection_error method."""

    def test_handle_timeout_error(self, mock_hass, api_token, mock_issue_registry):
        """Test handling asyncio.TimeoutError."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)
        error = TimeoutError()

        # Act & Assert
        with pytest.raises(HomeAssistantError) as exc_info:
            api._handle_connection_error("[test]", error)

        assert exc_info.value.translation_key == "timeout"
        assert exc_info.value.__cause__ == error

    def test_handle_client_error(self, mock_hass, api_token, mock_issue_registry):
        """Test handling aiohttp ClientError."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)
        error = ClientError("Connection refused")

        # Act & Assert
        with pytest.raises(HomeAssistantError) as exc_info:
            api._handle_connection_error("[test]", error)

        assert exc_info.value.translation_key == "network_error"
        assert exc_info.value.__cause__ == error

    def test_handle_unexpected_error(self, mock_hass, api_token, mock_issue_registry):
        """Test handling unexpected error type."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)
        error = RuntimeError("Unexpected error")

        # Act & Assert
        with pytest.raises(HomeAssistantError) as exc_info:
            api._handle_connection_error("[test]", error)

        assert exc_info.value.translation_key == "connection_failed"
        assert exc_info.value.__cause__ == error


class TestSendMeterReading:
    """Test send_meter_reading method."""

    @pytest.mark.asyncio
    async def test_send_meter_reading_success(
        self, mock_hass, api_token, device_id, mock_aiohttp_session
    ):
        """Test successful meter reading submission."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)
        timestamp = datetime(2025, 11, 28, 10, 30, 0, tzinfo=timezone.utc)

        resp_mock = AsyncMock()
        resp_mock.status = 200
        resp_mock.__aenter__.return_value = resp_mock
        resp_mock.__aexit__.return_value = None

        mock_aiohttp_session.post.return_value = resp_mock

        # Act
        await api.send_meter_reading(
            source_entity_id="sensor.power_meter",
            device_id=device_id,
            value=1234.5,
            timestamp=timestamp,
            allow_rounding=True,
        )

        # Assert
        mock_aiohttp_session.post.assert_called_once()
        call_args = mock_aiohttp_session.post.call_args

        assert f"/v1/devices/standard/{device_id}/meter-readings" in call_args[0][0]
        assert call_args[1]["json"]["value"] == 1234.5
        assert call_args[1]["params"] == {"allowRounding": "true"}
        assert call_args[1]["headers"]["Authorization"] == f"Bearer {api_token}"

    @pytest.mark.asyncio
    async def test_send_meter_reading_without_rounding(
        self, mock_hass, api_token, device_id, mock_aiohttp_session
    ):
        """Test meter reading submission without rounding."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)
        timestamp = datetime(2025, 11, 28, 10, 30, 0, tzinfo=timezone.utc)

        resp_mock = AsyncMock()
        resp_mock.status = 200
        resp_mock.__aenter__.return_value = resp_mock
        resp_mock.__aexit__.return_value = None

        mock_aiohttp_session.post.return_value = resp_mock

        # Act
        await api.send_meter_reading(
            source_entity_id="sensor.power_meter",
            device_id=device_id,
            value=1234.5,
            timestamp=timestamp,
            allow_rounding=False,
        )

        # Assert
        call_args = mock_aiohttp_session.post.call_args
        assert call_args[1]["params"] is None

    @pytest.mark.asyncio
    async def test_send_meter_reading_400_error(
        self, mock_hass, api_token, device_id, mock_aiohttp_session
    ):
        """Test meter reading with 400 Bad Request error."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)
        timestamp = datetime(2025, 11, 28, 10, 30, 0, tzinfo=timezone.utc)

        resp_mock = AsyncMock()
        resp_mock.status = 400
        resp_mock.json.return_value = {"message": "Invalid timestamp"}
        resp_mock.__aenter__.return_value = resp_mock
        resp_mock.__aexit__.return_value = None

        mock_aiohttp_session.post.return_value = resp_mock

        # Act & Assert
        with pytest.raises(HomeAssistantError) as exc_info:
            await api.send_meter_reading(
                source_entity_id="sensor.power_meter",
                device_id=device_id,
                value=1234.5,
                timestamp=timestamp,
            )

        assert exc_info.value.translation_key == "bad_request"

    @pytest.mark.asyncio
    async def test_send_meter_reading_timeout(
        self, mock_hass, api_token, device_id, mock_aiohttp_session
    ):
        """Test meter reading with timeout error."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)
        timestamp = datetime(2025, 11, 28, 10, 30, 0, tzinfo=timezone.utc)

        mock_aiohttp_session.post.side_effect = TimeoutError()

        # Act & Assert
        with pytest.raises(HomeAssistantError) as exc_info:
            await api.send_meter_reading(
                source_entity_id="sensor.power_meter",
                device_id=device_id,
                value=1234.5,
                timestamp=timestamp,
            )

        assert exc_info.value.translation_key == "timeout"

    @pytest.mark.asyncio
    async def test_send_meter_reading_network_error(
        self, mock_hass, api_token, device_id, mock_aiohttp_session
    ):
        """Test meter reading with network error."""
        # Arrange
        api = EnergyTrackerApi(hass=mock_hass, token=api_token)
        timestamp = datetime(2025, 11, 28, 10, 30, 0, tzinfo=timezone.utc)

        mock_aiohttp_session.post.side_effect = ClientError("Network unreachable")

        # Act & Assert
        with pytest.raises(HomeAssistantError) as exc_info:
            await api.send_meter_reading(
                source_entity_id="sensor.power_meter",
                device_id=device_id,
                value=1234.5,
                timestamp=timestamp,
            )

        assert exc_info.value.translation_key == "network_error"
