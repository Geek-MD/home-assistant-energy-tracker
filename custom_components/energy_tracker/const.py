"""Constants for the Energy Tracker integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "energy_tracker"

CONF_API_TOKEN = "api_token"

DEFAULT_API_BASE_URL = "https://public-api.energy-tracker.best-ios-apps.de"

SERVICE_SEND_METER_READING = "send_meter_reading"

# Platforms
PLATFORMS: list[Platform] = [Platform.SENSOR]

# Update interval for sensor data
DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)
