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
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import DeviceSummary, EnergyTrackerApi, MeterReading
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

LOGGER = logging.getLogger(__name__)


class EnergyTrackerDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Energy Tracker data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: EnergyTrackerApi,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            LOGGER.debug("Starting data synchronization with Energy Tracker API")

            # Fetch all devices
            devices = await self.api.get_devices()
            LOGGER.info("Synchronized %d devices from Energy Tracker API", len(devices))

            # Fetch latest reading for each device
            device_data: dict[str, dict[str, Any]] = {}
            for device in devices:
                try:
                    readings = await self.api.get_meter_readings(device.id, sort="desc")
                    latest_reading = readings[0] if readings else None

                    device_data[device.id] = {
                        "device": device,
                        "latest_reading": latest_reading,
                    }

                    if latest_reading:
                        LOGGER.debug(
                            "Device '%s' (%s): Latest reading %.2f at %s",
                            device.name,
                            device.id,
                            float(latest_reading.value),
                            latest_reading.timestamp,
                        )
                    else:
                        LOGGER.debug(
                            "Device '%s' (%s): No readings available",
                            device.name,
                            device.id,
                        )

                except HomeAssistantError as err:
                    LOGGER.warning(
                        "Failed to fetch readings for device %s: %s", device.id, err
                    )
                    # Still include device even if readings fail
                    device_data[device.id] = {
                        "device": device,
                        "latest_reading": None,
                    }

            LOGGER.info("Data synchronization completed successfully")
            return device_data

        except HomeAssistantError as err:
            LOGGER.error("Failed to synchronize data from Energy Tracker API: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Energy Tracker sensors from a config entry."""
    LOGGER.info(
        "Setting up Energy Tracker sensor platform for entry %s", entry.entry_id
    )

    token = entry.runtime_data
    api = EnergyTrackerApi(hass=hass, token=token)

    # Create coordinator
    coordinator = EnergyTrackerDataUpdateCoordinator(
        hass=hass,
        api=api,
        update_interval=DEFAULT_SCAN_INTERVAL,
    )

    # Fetch initial data
    LOGGER.debug("Performing initial data fetch")
    await coordinator.async_config_entry_first_refresh()

    # Create sensors for each device
    entities: list[SensorEntity] = []
    for device_id, data in coordinator.data.items():
        device: DeviceSummary = data["device"]

        LOGGER.info(
            "Creating sensors for device '%s' (ID: %s, Folder: %s)",
            device.name,
            device.id,
            device.folder_path,
        )

        # Create status sensor
        entities.append(EnergyTrackerDeviceStatusSensor(coordinator, device_id, entry))

        # Create latest reading sensor
        entities.append(EnergyTrackerLatestReadingSensor(coordinator, device_id, entry))

        # Create last updated sensor
        entities.append(EnergyTrackerLastUpdatedSensor(coordinator, device_id, entry))

    LOGGER.info(
        "Created %d sensors for %d devices",
        len(entities),
        len(coordinator.data),
    )

    async_add_entities(entities)


class EnergyTrackerSensorBase(
    CoordinatorEntity[EnergyTrackerDataUpdateCoordinator], SensorEntity
):
    """Base class for Energy Tracker sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EnergyTrackerDataUpdateCoordinator,
        device_id: str,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._entry = entry

        device: DeviceSummary = coordinator.data[device_id]["device"]

        # Device info for grouping
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device.name,
            manufacturer="Energy Tracker",
            model="Standard Measuring Device",
            configuration_url="https://www.energy-tracker.best-ios-apps.de",
        )

    @property
    def device_data(self) -> dict[str, Any]:
        """Return the device data from coordinator."""
        return self.coordinator.data[self._device_id]

    @property
    def device(self) -> DeviceSummary:
        """Return the device summary."""
        return self.device_data["device"]

    @property
    def latest_reading(self) -> MeterReading | None:
        """Return the latest meter reading."""
        return self.device_data.get("latest_reading")


class EnergyTrackerDeviceStatusSensor(EnergyTrackerSensorBase):
    """Sensor for device status."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:information"

    def __init__(
        self,
        coordinator: EnergyTrackerDataUpdateCoordinator,
        device_id: str,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, entry)
        self._attr_unique_id = f"{device_id}_status"
        self._attr_translation_key = "device_status"

    @property
    def native_value(self) -> str:
        """Return the status of the device."""
        if self.latest_reading:
            return "active"
        return "no_readings"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = {
            "device_id": self._device_id,
            "folder_path": self.device.folder_path,
            "last_updated_at": self.device.last_updated_at,
        }

        if self.latest_reading:
            attrs["meter_id"] = self.latest_reading.meter_id
            if self.latest_reading.meter_number:
                attrs["meter_number"] = self.latest_reading.meter_number

        return attrs


class EnergyTrackerLatestReadingSensor(EnergyTrackerSensorBase):
    """Sensor for latest meter reading."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: EnergyTrackerDataUpdateCoordinator,
        device_id: str,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, entry)
        self._attr_unique_id = f"{device_id}_latest_reading"
        self._attr_translation_key = "latest_reading"

    @property
    def native_value(self) -> float | None:
        """Return the latest reading value."""
        if self.latest_reading:
            try:
                return float(self.latest_reading.value)
            except (ValueError, TypeError):
                LOGGER.warning(
                    "Invalid reading value for device %s: %s",
                    self._device_id,
                    self.latest_reading.value,
                )
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes."""
        if not self.latest_reading:
            return None

        attrs: dict[str, Any] = {
            "timestamp": self.latest_reading.timestamp,
            "rollover_offset": self.latest_reading.rollover_offset,
        }

        if self.latest_reading.note:
            attrs["note"] = self.latest_reading.note

        return attrs


class EnergyTrackerLastUpdatedSensor(EnergyTrackerSensorBase):
    """Sensor for last update timestamp."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: EnergyTrackerDataUpdateCoordinator,
        device_id: str,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, entry)
        self._attr_unique_id = f"{device_id}_last_updated"
        self._attr_translation_key = "last_updated"

    @property
    def native_value(self) -> str | None:
        """Return the last updated timestamp."""
        return self.device.last_updated_at
