# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2026-02-13

### Fixed
- Energy Tracker sensor fixes

## [1.1.0] - 2026-02-13

### Added
- Initial release of Energy Tracker integration for Home Assistant
- Config Flow Setup for easy configuration through Home Assistant UI
- Multi-account support for connecting multiple Energy Tracker accounts
- Automated meter readings via Home Assistant automations
- Optional value rounding to match meter precision
- Full localization support with 26 languages
- Comprehensive error handling with clear error messages
- Repair flows for configuration issues
- Cloud integration with direct API connection to Energy Tracker service

### Features
- `energy_tracker.send_meter_reading` action for sending meter readings
- Support for sensors, input numbers, and number entities
- Automatic entity validation (numeric state, valid timestamp)
- Debug logging support

[1.1.1]: https://github.com/energy-tracker/home-assistant-energy-tracker/releases/tag/v1.1.1
[1.1.0]: https://github.com/energy-tracker/home-assistant-energy-tracker/releases/tag/v1.1.0
