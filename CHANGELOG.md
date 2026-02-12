# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-02-12

### Added
- **Sensor Platform**: Integration now automatically creates sensors in Home Assistant for each counter/device in Energy Tracker
- **Automatic Synchronization**: Sensors are automatically updated every 15 minutes to reflect the current values from Energy Tracker
- **Persistent Storage**: Sensor values have historical data persistence in Home Assistant's database
- **Device Attributes**: Additional device information (last update time, folder path, meter type, meter number, location) stored as sensor attributes
- **Device Class Detection**: Automatic assignment of appropriate device class (energy, gas, water) based on meter type
- **Device Details API**: Added method to fetch detailed information for individual devices

### Changed
- Extended API wrapper to support fetching devices from Energy Tracker using `/v1/devices/standard` endpoint
- Integration now forwards setup to sensor platform during config entry setup
- Enhanced data coordinator to fetch both device list and detailed information for each device

## [1.0.0] - Initial Release

### Added
- Config flow setup for easy configuration through Home Assistant UI
- Multi-account support for multiple Energy Tracker accounts
- `energy_tracker.send_meter_reading` service for automated meter readings
- Optional value rounding to match meter precision
- Full localization support (26 languages)
- Comprehensive error handling and repair flows
- Direct API connection to Energy Tracker service
