"""Async API client for the Energy Tracker public API."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

import aiohttp
from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import issue_registry as ir

from .const import DEFAULT_API_BASE_URL, DOMAIN

LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10


class EnergyTrackerApi:
    def __init__(self, hass: HomeAssistant, token: str) -> None:
        self._hass = hass
        self._token = token

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _handle_error_response(
        self,
        log_prefix: str,
        status: int,
        error_message: str | None,
        headers: aiohttp.typedefs.LooseHeaders | None,
    ) -> None:
        """Handle HTTP error responses.

        Args:
            log_prefix: Prefix for log messages.
            status: HTTP status code.
            error_message: Parsed error message from response.
            headers: Response headers.

        Raises:
            HomeAssistantError: Always, with localized error message.
        """
        if status == 400:
            msg = error_message or "Invalid input"
            LOGGER.warning("%s Bad Request: %s", log_prefix, msg)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="bad_request",
                translation_placeholders={"error": msg},
            )

        if status == 401:
            ir.async_create_issue(
                self._hass,
                DOMAIN,
                f"auth_error_401_{self._token[:8]}",
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key="auth_error_invalid_token",
            )
            LOGGER.error("%s Unauthorized: Check your access token", log_prefix)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            )

        if status == 403:
            ir.async_create_issue(
                self._hass,
                DOMAIN,
                f"auth_error_403_{self._token[:8]}",
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key="auth_error_insufficient_permissions",
            )
            LOGGER.error("%s Forbidden: Insufficient permissions", log_prefix)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            )

        if status == 404:
            LOGGER.warning("%s Not Found: Device not found", log_prefix)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_not_found",
            )

        if status == 429:
            retry_after: int | None = None
            if headers:
                retry_header = headers.get("Retry-After")
                if retry_header:
                    try:
                        retry_after = int(retry_header)
                    except ValueError:
                        pass

            msg = f"{log_prefix} Too many requests: Rate limit exceeded"
            if retry_after:
                msg += f" – Retry after {retry_after} seconds."
            LOGGER.warning(msg)

            if retry_after:
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="rate_limit",
                    translation_placeholders={"retry_after": str(retry_after)},
                )
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="rate_limit_no_time",
            )

        if 500 <= status <= 599:
            msg = error_message or "Internal server error"
            LOGGER.warning("%s Server error %s: %s", log_prefix, status, msg)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="server_error",
                translation_placeholders={"error": msg},
            )

        # Fallback for other HTTP errors
        msg = error_message or "Unknown error"
        LOGGER.warning("%s Unexpected HTTP %s: %s", log_prefix, status, msg)
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="unknown_error",
            translation_placeholders={"error": msg},
        )

    def _handle_connection_error(self, log_prefix: str, err: BaseException) -> None:
        if isinstance(err, asyncio.TimeoutError):
            LOGGER.error(
                "%s Request timed out after %s seconds",
                log_prefix,
                REQUEST_TIMEOUT,
            )
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="timeout",
            ) from err

        if isinstance(err, ClientError):
            LOGGER.error("%s Network error: %s", log_prefix, str(err))
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="network_error",
            ) from err

        LOGGER.error("%s Unexpected error: %s", log_prefix, str(err))
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="connection_failed",
        ) from err

    async def _parse_error_message(self, resp: aiohttp.ClientResponse) -> str | None:
        """Parse error message from API response.

        Args:
            resp: The HTTP response object.

        Returns:
            Parsed error message string, or None if parsing failed.
        """
        try:
            data = await resp.json()
            if isinstance(data, dict):
                message = data.get("message")
                if isinstance(message, list):
                    return "; ".join(str(m) for m in message if m)
                if isinstance(message, str):
                    return message
        except Exception:
            pass

        return None

    async def send_meter_reading(
        self,
        *,
        source_entity_id: str,
        device_id: str,
        value: float,
        timestamp: datetime,
        allow_rounding: bool = False,
    ) -> None:
        """Send a single meter reading to the Energy Tracker backend.

        Args:
            source_entity_id: Entity ID for logging purposes.
            device_id: The standard device ID in Energy Tracker.
            value: The meter reading value.
            timestamp: Timestamp for the reading.
            allow_rounding: Allow rounding to match meter precision.

        Raises:
            HomeAssistantError: If the API request fails.
        """
        log_prefix = f"[{source_entity_id}]"
        ts = timestamp.isoformat(timespec="milliseconds")

        payload: dict[str, Any] = {"value": value, "timestamp": ts}

        url = f"{DEFAULT_API_BASE_URL}/v1/devices/standard/{device_id}/meter-readings"
        params = (
            {"allowRounding": str(allow_rounding).lower()} if allow_rounding else None
        )

        session = async_get_clientsession(self._hass)
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

        try:
            async with session.post(
                url,
                json=payload,
                headers=self._get_headers(),
                params=params,
                timeout=timeout,
                raise_for_status=False,
            ) as resp:
                if resp.status >= 400:
                    error_message = await self._parse_error_message(resp)
                    self._handle_error_response(
                        log_prefix, resp.status, error_message, resp.headers
                    )

                LOGGER.info("%s Reading sent: %g", log_prefix, value)

        except (asyncio.TimeoutError, ClientError) as err:
            self._handle_connection_error(log_prefix, err)
