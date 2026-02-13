"""Home Assistant wrapper for Energy Tracker API client."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass
class DeviceSummary:
    """Represents a summary of a measuring device."""

    id: str
    name: str
    folder_path: str
    last_updated_at: str


@dataclass
class MeterReading:
    """Represents a meter reading."""

    timestamp: str
    value: str
    rollover_offset: int
    note: str | None
    meter_id: str
    meter_number: str | None


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
        LOGGER.info(
            "Sending meter reading to API: device=%s, value=%.2f, timestamp=%s, source=%s",
            device_id,
            value,
            timestamp.isoformat(),
            source_entity_id,
        )
        
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
            LOGGER.info(
                "Successfully sent meter reading: device=%s, value=%.2f",
                device_id,
                value,
            )

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

    async def get_devices(
        self,
        *,
        name: str | None = None,
        folder_path: str | None = None,
        updated_after: str | None = None,
        updated_before: str | None = None,
    ) -> list[DeviceSummary]:
        """Get list of standard measuring devices.

        Args:
            name: Filter by device name (partial match).
            folder_path: Filter devices in or under specified folder path.
            updated_after: Include only devices updated on or after this timestamp (ISO 8601).
            updated_before: Include only devices updated on or before this timestamp (ISO 8601).

        Returns:
            List of DeviceSummary objects.

        Raises:
            HomeAssistantError: If the API request fails.
        """
        LOGGER.info("Fetching devices from Energy Tracker API")

        endpoint = "/v1/devices/standard"
        params: dict[str, str] = {}

        if name:
            params["name"] = name
        if folder_path:
            params["folderPath"] = folder_path
        if updated_after:
            params["updatedAfter"] = updated_after
        if updated_before:
            params["updatedBefore"] = updated_before

        try:
            response = await self._client._make_request(
                method="GET",
                endpoint=endpoint,
                params=params if params else None,
            )

            data = await response.json()
            devices = [
                DeviceSummary(
                    id=device["id"],
                    name=device["name"],
                    folder_path=device["folderPath"],
                    last_updated_at=device["lastUpdatedAt"],
                )
                for device in data
            ]

            LOGGER.info("Successfully fetched %d devices from API", len(devices))
            return devices

        except (AuthenticationError, ForbiddenError) as err:
            LOGGER.error("Authentication error fetching devices: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err

        except ValidationError as err:
            LOGGER.warning("Validation error fetching devices: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="bad_request",
                translation_placeholders={
                    "error": "; ".join(err.api_message) if err.api_message else str(err)
                },
            ) from err

        except RateLimitError as err:
            LOGGER.warning("Rate limit exceeded fetching devices: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="rate_limit_no_time",
            ) from err

        except (NetworkError, TimeoutError) as err:
            LOGGER.error("Network error fetching devices: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="network_error",
            ) from err

        except Exception as err:
            LOGGER.exception("Unexpected error fetching devices")
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unknown_error",
                translation_placeholders={"error": str(err)},
            ) from err

    async def get_meter_readings(
        self,
        device_id: str,
        *,
        meter_id: str | None = None,
        from_timestamp: str | None = None,
        to_timestamp: str | None = None,
        sort: str = "desc",
    ) -> list[MeterReading]:
        """Get meter readings for a standard measuring device.

        Args:
            device_id: The unique ID of the measuring device.
            meter_id: Filter by meter ID.
            from_timestamp: Include only readings on or after this timestamp (ISO 8601).
            to_timestamp: Include only readings on or before this timestamp (ISO 8601).
            sort: Sort direction ('asc' or 'desc', default 'desc').

        Returns:
            List of MeterReading objects.

        Raises:
            HomeAssistantError: If the API request fails.
        """
        LOGGER.debug("Fetching meter readings for device %s", device_id)

        endpoint = f"/v3/devices/standard/{device_id}/meter-readings"
        params: dict[str, str] = {"sort": sort}

        if meter_id:
            params["meterId"] = meter_id
        if from_timestamp:
            params["from"] = from_timestamp
        if to_timestamp:
            params["to"] = to_timestamp

        try:
            response = await self._client._make_request(
                method="GET",
                endpoint=endpoint,
                params=params,
            )

            data = await response.json()
            readings = [
                MeterReading(
                    timestamp=reading["timestamp"],
                    value=reading["value"],
                    rollover_offset=reading["rolloverOffset"],
                    note=reading.get("note"),
                    meter_id=reading["meterId"],
                    meter_number=reading.get("meterNumber"),
                )
                for reading in data
            ]

            LOGGER.debug(
                "Successfully fetched %d readings for device %s", len(readings), device_id
            )
            return readings

        except ResourceNotFoundError as err:
            LOGGER.warning("Device %s not found: %s", device_id, err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_not_found",
            ) from err

        except (AuthenticationError, ForbiddenError) as err:
            LOGGER.error("Authentication error fetching readings: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
            ) from err

        except ValidationError as err:
            LOGGER.warning("Validation error fetching readings: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="bad_request",
                translation_placeholders={
                    "error": "; ".join(err.api_message) if err.api_message else str(err)
                },
            ) from err

        except (NetworkError, TimeoutError) as err:
            LOGGER.error("Network error fetching readings: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="network_error",
            ) from err

        except Exception as err:
            LOGGER.exception("Unexpected error fetching readings for device %s", device_id)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unknown_error",
                translation_placeholders={"error": str(err)},
            ) from err
