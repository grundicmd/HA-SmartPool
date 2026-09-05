# Zodiac Pool Robot for Home Assistant

Custom Home Assistant integration for Zodiac / iAquaLink connected pool-cleaning robots.

> This project is community-maintained and is not affiliated with or endorsed by Zodiac, Fluidra, or iAquaLink.

## Features

- UI configuration through **Settings → Devices & services**
- Uses your own iAquaLink account credentials; credentials are not hard-coded in the integration
- Supports multiple compatible robots on one iAquaLink account
- Start and stop cleaning from Home Assistant
- Robot availability / cloud connection status
- Remaining cleaning time
- Total runtime
- Canister/filter status
- Error reporting
- Firmware and diagnostic attributes

## Supported device families

The current implementation recognizes these iAquaLink device types:

- `cyclonext` — newer Zodiac cloud/WebSocket API
- `i2d_robot` — legacy iAquaLink robot API

Because Zodiac uses several regional names and product families, compatibility is determined by the device type returned by iAquaLink rather than by marketing model name alone. If your robot is not detected, please open an issue and include the model name and sanitized diagnostics (never include passwords or tokens).

## Installation with HACS

### Custom repository

1. Install HACS in Home Assistant.
2. Open **HACS → Integrations**.
3. Open the menu and choose **Custom repositories**.
4. Add this repository URL and select category **Integration**.
5. Search for **Zodiac Pool Robot** and install it.
6. Restart Home Assistant.
7. Open **Settings → Devices & services → Add integration**.
8. Search for **Zodiac Pool Robot**.
9. Enter the same email address and password you use in the iAquaLink app.

## Manual installation

Copy:

`custom_components/zodiac_pool_robot`

to:

`/config/custom_components/zodiac_pool_robot`

Restart Home Assistant and add the integration from **Settings → Devices & services**.

## Authentication and privacy

The integration asks for your iAquaLink email and password in Home Assistant's config flow. They are stored by Home Assistant in the config entry and are used to authenticate directly to the Zodiac/iAquaLink cloud services.

The repository does **not** contain user email addresses, passwords, Home Assistant tokens, robot serial numbers, or account tokens.

## Entities

For each supported robot the integration creates:

- a vacuum entity with start/stop controls;
- a connectivity binary sensor;
- total runtime sensor;
- remaining time sensor;
- last error sensor;
- canister/filter status sensor.

The vacuum entity also exposes useful diagnostics such as cleaning cycle, error code and firmware versions.

## Cloud dependency

This integration uses Zodiac/iAquaLink cloud endpoints and therefore requires Internet connectivity. The cloud API is not a documented public API and may change without notice.

## Troubleshooting

If setup fails:

1. Confirm the same credentials work in the official iAquaLink app.
2. Confirm the robot is visible in the official app.
3. Restart Home Assistant after installation or upgrade.
4. Enable debug logging for `custom_components.zodiac_pool_robot` if needed.
5. Open a GitHub issue with the Home Assistant version, robot model, device type if known, and sanitized logs.

Do not post passwords, authentication tokens, full cloud responses containing account information, or private Home Assistant configuration.

## Development

The repository includes parser tests and CI validation using HACS and Home Assistant hassfest.

## License

MIT License. See [LICENSE](LICENSE).
