"""Tests for the Energy Tracker sensor platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.energy_tracker.sensor import (
    EnergyTrackerSensor,
    _async_update_data,
)


class TestAsyncUpdateData:
    """Test _async_update_data function."""

    @pytest.mark.asyncio
    async def test_update_data_success(self, api_token):
        """Test successful data update."""
        # Arrange
        mock_api = MagicMock()

        # Mock get_devices response
        devices = [
            {
                "id": "device-1",
                "name": "Electric Meter",
                "folderPath": "/Home/",
                "lastUpdatedAt": "2026-02-12T10:00:00.000Z",
            },
            {
                "id": "device-2",
                "name": "Gas Meter",
                "folderPath": "/",
                "lastUpdatedAt": "2026-02-12T09:00:00.000Z",
            },
        ]
        mock_api.get_devices = AsyncMock(return_value=devices)

        # Mock get_meter_readings response
        readings_device_1 = [
            {
                "timestamp": "2026-02-12T10:00:00.000Z",
                "value": "1234.56",
                "rolloverOffset": 0,
                "note": None,
                "meterId": "meter-1",
                "meterNumber": "M123",
            }
        ]
        readings_device_2 = [
            {
                "timestamp": "2026-02-12T09:00:00.000Z",
                "value": "789.01",
                "rolloverOffset": 0,
                "note": "Test reading",
                "meterId": "meter-2",
                "meterNumber": "M456",
            }
        ]

        mock_api.get_meter_readings = AsyncMock(
            side_effect=[readings_device_1, readings_device_2]
        )

        # Act
        result = await _async_update_data(mock_api)

        # Assert
        assert len(result) == 2

        # Check first device
        assert result[0]["id"] == "device-1"
        assert result[0]["name"] == "Electric Meter"
        assert result[0]["value"] == "1234.56"
        assert result[0]["timestamp"] == "2026-02-12T10:00:00.000Z"
        assert result[0]["meter_id"] == "meter-1"
        assert result[0]["meter_number"] == "M123"

        # Check second device
        assert result[1]["id"] == "device-2"
        assert result[1]["name"] == "Gas Meter"
        assert result[1]["value"] == "789.01"
        assert result[1]["note"] == "Test reading"

        # Verify API calls
        mock_api.get_devices.assert_called_once()
        assert mock_api.get_meter_readings.call_count == 2

    @pytest.mark.asyncio
    async def test_update_data_with_failed_reading(self, api_token):
        """Test data update when reading fetch fails for one device."""
        # Arrange
        mock_api = MagicMock()

        devices = [
            {
                "id": "device-1",
                "name": "Electric Meter",
                "folderPath": "/Home/",
                "lastUpdatedAt": "2026-02-12T10:00:00.000Z",
            },
            {
                "id": "device-2",
                "name": "Gas Meter",
                "folderPath": "/",
                "lastUpdatedAt": "2026-02-12T09:00:00.000Z",
            },
        ]
        mock_api.get_devices = AsyncMock(return_value=devices)

        # First device succeeds, second fails
        readings_device_1 = [
            {
                "timestamp": "2026-02-12T10:00:00.000Z",
                "value": "1234.56",
                "rolloverOffset": 0,
                "note": None,
                "meterId": "meter-1",
                "meterNumber": "M123",
            }
        ]

        mock_api.get_meter_readings = AsyncMock(
            side_effect=[readings_device_1, Exception("API Error")]
        )

        # Act
        result = await _async_update_data(mock_api)

        # Assert
        assert len(result) == 2

        # First device should have reading data
        assert result[0]["id"] == "device-1"
        assert result[0]["value"] == "1234.56"

        # Second device should have basic info only
        assert result[1]["id"] == "device-2"
        assert "value" not in result[1]


class TestEnergyTrackerSensor:
    """Test EnergyTrackerSensor class."""

    def test_sensor_initialization(self, hass):
        """Test sensor initialization."""
        # Arrange
        mock_coordinator = MagicMock()
        mock_coordinator.data = []

        device = {
            "id": "device-1",
            "name": "Electric Meter",
            "folderPath": "/Home/",
            "lastUpdatedAt": "2026-02-12T10:00:00.000Z",
        }

        mock_entry = MagicMock()
        mock_entry.entry_id = "test-entry"

        # Act
        sensor = EnergyTrackerSensor(mock_coordinator, device, mock_entry)

        # Assert
        assert sensor._device_id == "device-1"
        assert sensor._attr_name == "Electric Meter"
        assert sensor._attr_unique_id == "test-entry_device-1"

    def test_sensor_native_value(self, hass):
        """Test sensor native_value property."""
        # Arrange
        device = {
            "id": "device-1",
            "name": "Electric Meter",
            "folderPath": "/Home/",
            "lastUpdatedAt": "2026-02-12T10:00:00.000Z",
            "value": "1234.56",
        }

        mock_coordinator = MagicMock()
        mock_coordinator.data = [device]

        mock_entry = MagicMock()
        mock_entry.entry_id = "test-entry"

        sensor = EnergyTrackerSensor(mock_coordinator, device, mock_entry)

        # Act
        value = sensor.native_value

        # Assert
        assert value == 1234.56

    def test_sensor_extra_state_attributes(self, hass):
        """Test sensor extra_state_attributes property."""
        # Arrange
        device = {
            "id": "device-1",
            "name": "Electric Meter",
            "folderPath": "/Home/",
            "lastUpdatedAt": "2026-02-12T10:00:00.000Z",
            "value": "1234.56",
            "timestamp": "2026-02-12T10:00:00.000Z",
            "meter_id": "meter-1",
            "meter_number": "M123",
            "note": "Test note",
            "rollover_offset": 1,
        }

        mock_coordinator = MagicMock()
        mock_coordinator.data = [device]

        mock_entry = MagicMock()
        mock_entry.entry_id = "test-entry"

        sensor = EnergyTrackerSensor(mock_coordinator, device, mock_entry)

        # Act
        attributes = sensor.extra_state_attributes

        # Assert
        assert attributes["last_updated_at"] == "2026-02-12T10:00:00.000Z"
        assert attributes["folder_path"] == "/Home/"
        assert attributes["reading_timestamp"] == "2026-02-12T10:00:00.000Z"
        assert attributes["meter_id"] == "meter-1"
        assert attributes["meter_number"] == "M123"
        assert attributes["note"] == "Test note"
        assert attributes["rollover_offset"] == 1

    def test_sensor_available(self, hass):
        """Test sensor available property."""
        # Arrange
        mock_coordinator = MagicMock()
        mock_coordinator.last_update_success = True
        mock_coordinator.data = []

        device = {
            "id": "device-1",
            "name": "Electric Meter",
        }

        mock_entry = MagicMock()
        mock_entry.entry_id = "test-entry"

        sensor = EnergyTrackerSensor(mock_coordinator, device, mock_entry)

        # Act & Assert
        assert sensor.available is True

        # Test when coordinator fails
        mock_coordinator.last_update_success = False
        assert sensor.available is False
