# Samson TROVIS 557x – Home Assistant integration

> [!IMPORTANT]
> The [project wiki](https://github.com/Tom-Bom-badil/trovis-modbus-hass/wiki) contains the detailed setup guide, current entity structure, architecture notes, and [instructions for contributors](https://github.com/Tom-Bom-badil/trovis-modbus-hass/wiki/Contributions).

This repository contains a native Home Assistant custom integration for Samson TROVIS 557x heating controllers.

The integration exposes TROVIS controllers as Home Assistant devices and entities. Physical Modbus connections are configured and owned by the separate Home Assistant `modbus_connection` integration. No YAML Modbus configuration is required.

## Features

- UI-based setup
- Shared Modbus connections
- Multiple controllers
- Automatic model and physical-sensor detection
- Model-specific two- or three-heating-circuit profiles
- Network, local serial, and serial-URL connections
- Range-aware grouped reads
- Register and coil writes
- Write-access safety switch
- Reconfiguration without changing existing entity IDs
- German and English translations

## Supported model profiles

| Models | Heating circuits | Profile |
| --- | ---: | --- |
| TROVIS 5573, 5573-1, 5575, 5576 | Rk1 and Rk2 | TROVIS 5573 |
| TROVIS 5578, 5578-E, 5579 | Rk1, Rk2, and Rk3 | TROVIS 5578 |

The domestic-hot-water circuit is represented as Rk4.

## Prerequisite

Before adding a TROVIS controller, create at least one connection in the Home Assistant `modbus_connection` integration.

Use:

- **Network** for native Modbus TCP or a gateway that translates Modbus TCP to Modbus RTU
- **Serial** with a URL such as `socket://192.168.1.50:502` for transparent RTU over TCP
- **Serial** with `/dev/ttyUSB0`, `rfc2217://...`, or another supported serial URL for local or forwarded serial connections

A `socket://` URL is transparent serial forwarding over TCP. It is not native Modbus TCP.

## Installation

1. Install and configure the Home Assistant `modbus_connection` integration.
2. Create the required Network or Serial connection entries.
3. Copy `custom_components/trovis557x` to `/config/custom_components/trovis557x`.
4. Restart Home Assistant.
5. Open `Settings → Devices & services → Add integration`.
6. Search for `Samson Trovis 557x`.
7. Select an existing Modbus Connection entry and enter the controller's Modbus unit ID.

The default TROVIS unit ID is `246`.

## Entity platforms

The integration currently provides:

- `sensor`
- `binary_sensor`
- `number`
- `select`
- `switch`
- `climate`
- `water_heater`

Writable values are protected by the controller-level **Write access** switch. Limits, options, scaling, and TROVIS-specific write rules are provided by the [`trovis-modbus`](https://github.com/Tom-Bom-badil/trovis-modbus) library.

## Architecture

```text
Home Assistant entities
        │
        ▼
trovis-modbus-hass
        │
        ▼
trovis-modbus
        │
        ▼
Home Assistant modbus_connection integration
        │
        ▼
modbus-connection / tmodbus / serialx
        │
        ▼
Physical TROVIS device or gateway
```

The TROVIS integration does not open or close the physical connection. It selects an existing `modbus_connection` config entry and obtains a shared Modbus unit from it.

## Development

Install the local device library when required:

```bash
cd /config/dev/trovis-modbus
python -m pip install -e .
```

Install the local checking tools:

```bash
python -m pip install --upgrade ruff pytest pytest-asyncio
```

Run the checks supported by the HAOS / VS Code development shell:

```bash
cd /config/dev/trovis-modbus-hass
python -m ruff format --check .
python -m ruff check .
python -m compileall custom_components tests
```

The complete Home Assistant integration test suite requires a prepared Home Assistant development environment and is also executed by GitHub Actions.
