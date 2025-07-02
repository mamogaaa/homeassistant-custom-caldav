# CalDAV Custom - Home Assistant Custom Component

A custom Home Assistant integration for CalDAV that uses a forked version of the caldav library with fixes for calendar server 400 bad request issues.

## Features

- All features from the standard Home Assistant CalDAV integration
- Fixed compatibility with calendar servers that return 400 bad request errors
- Uses forked caldav library: https://github.com/mamogaaa/caldav/tree/fix-calendar-server-400-bad-request

## Installation

### Via HACS (Recommended)

1. Add this repository as a custom repository in HACS:
   - In Home Assistant, go to HACS > Integrations
   - Click the three dots menu in the top right corner
   - Select "Custom repositories"
   - Add `https://github.com/mamogaaa/ha-custom-caldav` as repository URL
   - Select "Integration" as category
   - Click "ADD"

2. Install the integration:
   - Search for "CalDAV Custom" in HACS
   - Click "Install"
   - Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/caldav_custom` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add the integration through the UI

## Configuration

1. Go to Settings → Devices & Services → Add Integration
2. Search for "CalDAV Custom"
3. Enter your CalDAV server details:
   - URL: Your CalDAV server URL
   - Username: Your username
   - Password: Your password
   - Verify SSL: Whether to verify SSL certificates

## Differences from Core CalDAV Integration

- Uses domain `caldav_custom` instead of `caldav` to avoid conflicts
- Uses the forked caldav library with fixes for server compatibility issues
- Can be installed as a custom component without rebuilding Home Assistant core

## Troubleshooting

If you encounter issues:

1. Check the Home Assistant logs for any error messages
2. Ensure your CalDAV server is accessible and credentials are correct
3. Try disabling SSL verification if you have certificate issues

## Development

This custom component is based on the Home Assistant core CalDAV integration and uses a forked version of the caldav library to fix specific server compatibility issues.

## License

Same as Home Assistant - Apache License 2.0