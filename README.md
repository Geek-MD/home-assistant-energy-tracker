# Energy Tracker Integration for Home Assistant

[![GitHub Release](https://img.shields.io/github/release/Geek-MD/home-assistant-energy-tracker.svg)](https://github.com/Geek-MD/home-assistant-energy-tracker/releases)
[![HACS](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![License](https://img.shields.io/github/license/Geek-MD/home-assistant-energy-tracker.svg)](LICENSE)

Integrate your [Energy Tracker](https://www.energy-tracker.best-ios-apps.de) account with Home Assistant to automatically sync meter readings and create sensors for all your Energy Tracker devices.

## Features

- ✅ **Automatic Sensor Creation**: Creates sensors in Home Assistant for all your Energy Tracker devices
- ✅ **Automatic Synchronization**: Keeps sensor values synchronized with Energy Tracker (updates every 15 minutes)
- ✅ **Historical Data**: Sensor values are stored in Home Assistant's database for long-term tracking
- ✅ **Rich Attributes**: Additional device information (last update time, meter type, location) available as sensor attributes
- ✅ **Smart Device Classes**: Automatically assigns appropriate device class (energy, gas, water) based on meter type
- ✅ **Config Flow Setup**: Easy configuration through the Home Assistant UI
- ✅ **Multi-Account Support**: Connect multiple Energy Tracker accounts
- ✅ **Send Meter Readings**: Send sensor values to Energy Tracker via automations
- ✅ **Optional Value Rounding**: Automatic rounding to match your meter's precision
- ✅ **Full Localization**: 26 languages supported
- ✅ **Comprehensive Error Handling**: Clear error messages and repair flows
- ✅ **Cloud Integration**: Direct API connection to Energy Tracker service

## Installation

> **Note**: This integration is currently available via HACS only. Home Assistant Core integration is planned for the future.

### Step 1: Install the Integration

#### Option A: Via HACS (Recommended)

1. Open [HACS](https://hacs.xyz/) in Home Assistant
2. Go to **Integrations**
3. Click **+ Explore & Download Repositories**
4. Search for "Energy Tracker"
5. Click **Download**
6. Restart Home Assistant

#### Option B: Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/Geek-MD/home-assistant-energy-tracker/releases)
2. Copy the `custom_components/energy_tracker/` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

### Step 2: Configure the Integration

Before configuring, you need an API token from your [Energy Tracker account](https://www.energy-tracker.best-ios-apps.de):

1. Log in at [www.energy-tracker.best-ios-apps.de](https://www.energy-tracker.best-ios-apps.de)
2. Navigate to **API** → **Access Tokens**
3. Create a new **Personal Access Token**
4. Copy the token

Then in Home Assistant:

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Energy Tracker"
4. Enter a name for this account (e.g., "My Energy Tracker")
5. Paste your personal access token
6. Click **Submit**

After configuration, the integration will automatically:
- Fetch all your devices from Energy Tracker
- Create a sensor entity for each device in Home Assistant
- Update sensor values every 15 minutes to stay synchronized with Energy Tracker

You'll find your devices under **Settings** → **Devices & Services** → **Energy Tracker**.

## Usage

### Automatic Sensors

Once configured, the integration automatically creates sensor entities for all devices in your Energy Tracker account. These sensors:

- **Display Current Values**: Show the latest meter reading from Energy Tracker
- **Have Persistence**: Historical values are stored in Home Assistant's database for long-term tracking
- **Update Automatically**: Refresh every 15 minutes to stay in sync with Energy Tracker
- **Include Rich Attributes**: Additional information like last update time, meter type, meter number, and location

#### Sensor Attributes

Each sensor includes the following attributes (when available):
- `last_updated`: Timestamp of the last update
- `last_reading_date`: Date of the last meter reading
- `meter_type`: Type of meter (electricity, gas, water, etc.)
- `meter_number`: Physical meter number
- `location`: Device location
- `device_id`: Energy Tracker device identifier

#### Using Sensors in Dashboards and Automations

The sensors can be used like any other Home Assistant sensor:
- Add to dashboards for visualization
- Use in automations and scripts
- Track in the Energy dashboard
- Create statistics and analytics

### Sending Meter Readings (Optional)

In addition to automatic synchronization, you can also send meter readings from Home Assistant sensors to Energy Tracker using automations.

#### Step 3: Get Your Standard Measuring Device ID

You need the device ID to send meter readings. There are two ways to get it:

##### Option A: Via Energy Tracker Web Interface

1. Log into your Energy Tracker account
2. Go to your device details
3. Copy the **Standard Measuring Device ID** 
4. **Important**: Remove the `std-` prefix! The ID should be in UUID format like `deadbeef-dead-beef-dead-beefdeadbeef`

##### Option B: Via API (Recommended)

1. Log into your Energy Tracker account
2. Navigate to **API** → **Documentation**
3. Use the API endpoint to retrieve your devices
4. The IDs returned are already in the correct format (without `std-` prefix)

#### Step 4: Create an Automation

1. Go to **Settings** → **Automations & Scenes**
2. Click **+ Create Automation**
3. Add a **Trigger** (e.g., time-based: daily at 23:55)
4. Click **Add action** and search for **Energy Tracker: Send meter reading**
5. Fill in the required fields
6. Save the automation

## Reference

### Action `energy_tracker.send_meter_reading`

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `entry_id` | Yes | config_entry | Your Energy Tracker account (select from dropdown) |
| `device_id` | Yes | string | Standard measuring device ID from Energy Tracker (UUID format) |
| `source_entity_id` | Yes | entity_id | Home Assistant sensor providing the meter reading |
| `allow_rounding` | No | boolean | Round value to meter precision (default: `true`) |

### Example Automation (YAML)

```yaml
- alias: "Send daily electricity reading"
  triggers:
    - trigger: time
      at: "23:55:00"
  actions:
    - action: energy_tracker.send_meter_reading
      data:
        entry_id: <select from dropdown>
        device_id: "deadbeef-dead-beef-dead-beefdeadbeef"
        source_entity_id: <select from dropdown>
        allow_rounding: true
```

### Supported Entity Types

The integration accepts meter readings from:

- **Sensors** (`sensor.*`) - e.g., `sensor.electricity_meter`, `sensor.gas_meter`
- **Input Numbers** (`input_number.*`) - Manual input helpers
- **Number Entities** (`number.*`) - Numeric device values

### Requirements

- Entity state must be numeric
- Entity must have a valid timestamp (`last_updated`)
- Entity state must not be `unavailable` or `unknown`

## Error Handling

The integration provides comprehensive error handling with localized error messages.

## Troubleshooting

### Enable Debug Logging

Add to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.energy_tracker: debug
```

Then check **Settings** → **System** → **Logs** for detailed information.

### Common Issues

**Q: "Standard measuring device not found" error**  
A: Verify the device ID is correct. It should be a UUID format like `deadbeef-dead-beef-dead-beefdeadbeef`. Find it in your Energy Tracker account under device details.

**Q: "Entity unavailable" error in automation**  
A: Add a condition to check entity state before sending:

```yaml
conditions:
  - "{{ states('sensor.electricity_meter') not in ['unavailable', 'unknown'] }}"
```

**Q: Integration shows authentication error after setup**  
A: Your token may be invalid. Go to **Settings** → **Devices & Services** → **Energy Tracker** → **Reconfigure** to update your token.

**Q: How do I update my token?**  
A: Click the **⋮** menu on your Energy Tracker integration and select **Reconfigure**. Leave the token field empty to keep the existing token, or enter a new one.

## Support

- **Energy Tracker Support**: [Contact Energy Tracker](https://www.energy-tracker.best-ios-apps.de/contact)
- **Home Assistant Community**: [Community Forum](https://community.home-assistant.io/)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2015-2025 energy-tracker support@best-ios-apps.de

## Related Links

- [Energy Tracker Website](https://www.energy-tracker.best-ios-apps.de)
- [Home Assistant Documentation](https://www.home-assistant.io/)
- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
