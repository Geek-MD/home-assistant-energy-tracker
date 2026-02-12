"""Home Assistant wrapper for Energy Tracker API client."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from energy_tracker_api import (
    AuthenticationError,
    ConflictError,
    CreateMeterReadingDto,
    EnergyTrackerAPIError,
    EnergyTrackerClient,
    ForbiddenError,
    NetworkError,
    RateLimitError,
    ResourceNotFoundError,
    TimeoutError,
    ValidationError,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

LOGGER = logging.getLogger(__name__)


class EnergyTrackerApi:
    """Home Assistant wrapper for the Energy Tracker API client.

    Handles sending meter readings and error translation to Home Assistant exceptions.
    """

    def __init__(self, hass: HomeAssistant, token: str) -> None:
        """Initialize the EnergyTrackerApi wrapper.

        Args:
            hass: The Home Assistant instance.
            token: The Energy Tracker API access token.
        """
        self._hass = hass
        self._token = token
        self._client = EnergyTrackerClient(access_token=token)

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
        meter_reading = CreateMeterReadingDto(
            value=value,
            timestamp=timestamp,
        )

        try:
            await self._client.meter_readings.create(
                device_id=device_id,
                meter_reading=meter_reading,
                allow_rounding=allow_rounding,
            )
            LOGGER.info("Reading sent: %g", value)

        except ValidationError as err:
            # HTTP 400 - Bad Request
            LOGGER.warning("Validation error: %s", err)
            msg = "; ".join(err.api_message) if err.api_message else "Invalid input"
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="bad_request",
                translation_placeholders={"error": msg},
            ) from err

        except AuthenticationError as err:
            # HTTP 401 - Unauthorized
            LOGGER.error("Authentication failed: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err

        except ForbiddenError as err:
            # HTTP 403 - Forbidden
            LOGGER.error("Access forbidden: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err

        except ResourceNotFoundError as err:
            # HTTP 404 - Not Found
            LOGGER.warning("Device not found: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_not_found",
            ) from err

        except ConflictError as err:
            # HTTP 409 - Conflict
            LOGGER.warning("Conflict: %s", err)
            msg = "; ".join(err.api_message) if err.api_message else str(err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="conflict",
                translation_placeholders={"error": msg},
            ) from err

        except RateLimitError as err:
            # HTTP 429 - Rate Limit
            LOGGER.warning("Rate limit exceeded: %s", err)

            if err.retry_after:
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="rate_limit",
                    translation_placeholders={"retry_after": str(err.retry_after)},
                ) from err
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="rate_limit_no_time",
            ) from err

        except TimeoutError as err:
            # Request timeout
            LOGGER.error("Request timeout: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="timeout",
            ) from err

        except NetworkError as err:
            # Network/connection errors
            LOGGER.error("Network error: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="network_error",
            ) from err

        except EnergyTrackerAPIError as err:
            # Other API errors
            LOGGER.error("API error: %s", err)
            msg = "; ".join(err.api_message) if err.api_message else str(err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="server_error",
                translation_placeholders={"error": msg},
            ) from err

        except Exception as err:
            # Unexpected errors
            LOGGER.exception("Unexpected error")
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unknown_error",
                translation_placeholders={"error": str(err)},
            ) from err

    async def get_devices(self) -> list[dict[str, Any]]:
        """Fetch all standard measuring devices from Energy Tracker.

        Returns:
            List of device dictionaries containing basic device information:
            - id (str): UUID of the device
            - name (str): Device name
            - folderPath (str): Logical folder path for grouping
            - lastUpdatedAt (str): ISO 8601 timestamp of last update

        Raises:
            HomeAssistantError: If the API request fails.
        """
        try:
            # Make direct API request to get device list
            endpoint = "/v1/devices/standard"
            response = await self._client._make_request(
                method="GET",
                endpoint=endpoint,
            )
            devices = await response.json()
            LOGGER.debug("Fetched %d devices from Energy Tracker", len(devices))
            return devices

        except AuthenticationError as err:
            LOGGER.error("Authentication failed: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err

        except ForbiddenError as err:
            LOGGER.error("Access forbidden: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err

        except TimeoutError as err:
            LOGGER.error("Request timeout: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="timeout",
            ) from err

        except NetworkError as err:
            LOGGER.error("Network error: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="network_error",
            ) from err

        except EnergyTrackerAPIError as err:
            LOGGER.error("API error: %s", err)
            msg = "; ".join(err.api_message) if err.api_message else str(err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="server_error",
                translation_placeholders={"error": msg},
            ) from err

        except Exception as err:
            LOGGER.exception("Unexpected error fetching devices")
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unknown_error",
                translation_placeholders={"error": str(err)},
            ) from err

    async def get_device_details(self, device_id: str) -> dict[str, Any]:
        """Fetch detailed information for a specific device.

        Args:
            device_id: UUID of the device to fetch details for.

        Returns:
            Dictionary containing detailed device information.

        Raises:
            HomeAssistantError: If the API request fails.
        """
        try:
            # Make direct API request to get device details
            endpoint = f"/v1/devices/standard/{device_id}"
            response = await self._client._make_request(
                method="GET",
                endpoint=endpoint,
            )
            device_details = await response.json()
            LOGGER.debug("Fetched details for device %s", device_id)
            return device_details

        except ResourceNotFoundError as err:
            LOGGER.warning("Device %s not found: %s", device_id, err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_not_found",
            ) from err

        except AuthenticationError as err:
            LOGGER.error("Authentication failed: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err

        except ForbiddenError as err:
            LOGGER.error("Access forbidden: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err

        except TimeoutError as err:
            LOGGER.error("Request timeout: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="timeout",
            ) from err

        except NetworkError as err:
            LOGGER.error("Network error: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="network_error",
            ) from err

        except EnergyTrackerAPIError as err:
            LOGGER.error("API error: %s", err)
            msg = "; ".join(err.api_message) if err.api_message else str(err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="server_error",
                translation_placeholders={"error": msg},
            ) from err

        except Exception as err:
            LOGGER.exception("Unexpected error fetching device details")
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unknown_error",
                translation_placeholders={"error": str(err)},
            ) from err

    async def get_meter_readings(
        self, device_id: str, limit: int = 1, sort: str = "desc"
    ) -> list[dict[str, Any]]:
        """Fetch meter readings for a specific device.

        Args:
            device_id: UUID of the device to fetch readings for.
            limit: Maximum number of readings to return (not supported by API,
                   but we can slice the result).
            sort: Sort order - 'desc' for newest first, 'asc' for oldest first.

        Returns:
            List of meter reading dictionaries containing:
            - timestamp (str): ISO 8601 timestamp of the reading
            - value (str): Reading value as decimal string
            - rolloverOffset (int): Offset applied after meter rollover
            - note (str|None): Optional note about the reading
            - meterId (str): UUID of the associated meter
            - meterNumber (str|None): Optional external meter number

        Raises:
            HomeAssistantError: If the API request fails.
        """
        try:
            # Make direct API request to get meter readings
            endpoint = f"/v3/devices/standard/{device_id}/meter-readings"
            params = {"sort": sort}

            response = await self._client._make_request(
                method="GET",
                endpoint=endpoint,
                params=params,
            )
            readings = await response.json()

            # Limit the results if needed
            if limit and len(readings) > limit:
                readings = readings[:limit]

            LOGGER.debug(
                "Fetched %d meter reading(s) for device %s", len(readings), device_id
            )
            return readings

        except ResourceNotFoundError as err:
            LOGGER.warning("Device %s not found: %s", device_id, err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_not_found",
            ) from err

        except AuthenticationError as err:
            LOGGER.error("Authentication failed: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err

        except ForbiddenError as err:
            LOGGER.error("Access forbidden: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err

        except TimeoutError as err:
            LOGGER.error("Request timeout: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="timeout",
            ) from err

        except NetworkError as err:
            LOGGER.error("Network error: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="network_error",
            ) from err

        except EnergyTrackerAPIError as err:
            LOGGER.error("API error: %s", err)
            msg = "; ".join(err.api_message) if err.api_message else str(err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="server_error",
                translation_placeholders={"error": msg},
            ) from err

        except Exception as err:
            LOGGER.exception("Unexpected error fetching meter readings")
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unknown_error",
                translation_placeholders={"error": str(err)},
            ) from err
