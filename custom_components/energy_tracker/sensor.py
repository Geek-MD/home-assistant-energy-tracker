"""Sensor platform for Energy Tracker integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import EnergyTrackerApi
from .const import DOMAIN

LOGGER = logging.getLogger(__name__)

# Update interval for fetching device data
SCAN_INTERVAL = timedelta(minutes=15)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Energy Tracker sensors from a config entry."""
    LOGGER.debug(
        "Setting up Energy Tracker sensor platform for entry %s", entry.entry_id
    )

    # Get the API token from runtime data
    token = entry.runtime_data

    # Create API instance
    api = EnergyTrackerApi(hass=hass, token=token)

    # Create coordinator for updating device data
    coordinator = DataUpdateCoordinator(
        hass,
        LOGGER,
        name=f"{DOMAIN}_{entry.entry_id}",
        update_method=lambda: _async_update_data(api),
        update_interval=SCAN_INTERVAL,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Create sensor entities for each device
    entities = []
    if coordinator.data:
        for device in coordinator.data:
            entities.append(EnergyTrackerSensor(coordinator, device, entry))

    async_add_entities(entities)
    LOGGER.info("Added %d Energy Tracker sensor(s)", len(entities))


async def _async_update_data(api: EnergyTrackerApi) -> list[dict[str, Any]]:
    """Fetch device data from Energy Tracker API.

    Args:
        api: The Energy Tracker API instance.

    Returns:
        List of device dictionaries with detailed information.

    Raises:
        UpdateFailed: If the data update fails.
    """
    try:
        # First, get the list of all devices
        devices = await api.get_devices()

        # Then, fetch detailed information for each device
        detailed_devices = []
        for device in devices:
            device_id = device.get("id")
            if device_id:
                try:
                    details = await api.get_device_details(device_id)
                    # Merge basic info with detailed info
                    details["id"] = device_id
                    details["name"] = device.get("name", details.get("name", "Unknown"))
                    details["folderPath"] = device.get("folderPath", "/")
                    details["lastUpdatedAt"] = device.get("lastUpdatedAt")
                    detailed_devices.append(details)
                except Exception as err:
                    LOGGER.warning(
                        "Failed to fetch details for device %s: %s", device_id, err
                    )
                    # Still add the basic device info even if details fail
                    detailed_devices.append(device)

        return detailed_devices
    except Exception as err:
        raise UpdateFailed(f"Error fetching device data: {err}") from err


class EnergyTrackerSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Energy Tracker sensor."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device: dict[str, Any],
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: The data update coordinator.
            device: Device data from Energy Tracker API.
            entry: The config entry.
        """
        super().__init__(coordinator)

        self._device_id = device.get("id")
        self._attr_unique_id = f"{entry.entry_id}_{self._device_id}"

        # Set device name
        device_name = device.get("name") or device.get("deviceName") or "Unknown Device"
        self._attr_name = device_name

        # Set device class based on meter type
        meter_type = device.get("meterType") or device.get("type")
        self._attr_device_class = self._get_device_class(meter_type)

        # Set unit of measurement
        unit = device.get("unit") or device.get("meterUnit")
        self._attr_native_unit_of_measurement = unit

        LOGGER.debug(
            "Created sensor for device %s (%s) with unit %s",
            device_name,
            self._device_id,
            unit,
        )

    def _get_device_class(self, meter_type: str | None) -> SensorDeviceClass | None:
        """Determine the device class based on meter type.

        Args:
            meter_type: The meter type from Energy Tracker.

        Returns:
            The appropriate SensorDeviceClass or None.
        """
        if not meter_type:
            return None

        meter_type_lower = meter_type.lower()

        if "electric" in meter_type_lower or "strom" in meter_type_lower:
            return SensorDeviceClass.ENERGY
        if "gas" in meter_type_lower:
            return SensorDeviceClass.GAS
        if "water" in meter_type_lower or "wasser" in meter_type_lower:
            return SensorDeviceClass.WATER

        return None

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        for device in self.coordinator.data:
            if device.get("id") == self._device_id:
                # Get the latest meter reading value
                value = (
                    device.get("currentValue")
                    or device.get("lastReading")
                    or device.get("value")
                )
                if value is not None:
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        LOGGER.warning(
                            "Could not convert value %s to float for device %s",
                            value,
                            self._device_id,
                        )
                        return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attributes = {}

        for device in self.coordinator.data:
            if device.get("id") == self._device_id:
                # Add relevant device information as attributes
                if "lastUpdatedAt" in device:
                    attributes["last_updated_at"] = device["lastUpdatedAt"]
                if "folderPath" in device:
                    attributes["folder_path"] = device["folderPath"]
                if "lastUpdated" in device:
                    attributes["last_updated"] = device["lastUpdated"]
                if "lastReadingDate" in device:
                    attributes["last_reading_date"] = device["lastReadingDate"]
                if "meterType" in device or "type" in device:
                    attributes["meter_type"] = device.get("meterType") or device.get(
                        "type"
                    )
                if "meterNumber" in device:
                    attributes["meter_number"] = device["meterNumber"]
                if "location" in device:
                    attributes["location"] = device["location"]
                if "deviceId" in device:
                    attributes["device_id"] = device["deviceId"]

                break

        return attributes

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success
