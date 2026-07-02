# Samson TROVIS 557x – Home Assistant integration

> [!IMPORTANT]
> The [project wiki](https://github.com/Tom-Bom-badil/trovis-modbus-hass/wiki) contains the current entity structure, design notes, and [instructions for contributors](https://github.com/Tom-Bom-badil/trovis-modbus-hass/wiki/Contributions).

This repository contains a native Home Assistant custom integration for Samson TROVIS 557x heating controllers.

The integration connects directly to the controller over Modbus and exposes its values as Home Assistant devices and entities. No YAML Modbus configuration or separate Home Assistant Modbus integration is required.

The device model is provided by [`trovis-modbus`](https://github.com/Tom-Bom-badil/trovis-modbus). Connections are provided by [`modbus-connection`](https://github.com/home-assistant-libs/modbus-connection) using its `tmodbus` backend.

## Current features

- UI-based setup
- Multiple controllers
- Automatic controller-model detection
- Automatic detection of connected physical sensors
- Automatic selection of the two- or three-heating-circuit profile
- Automatic distinction between transparent RTU over TCP and native Modbus TCP
- Local serial and serial URL support
- Model-aware and range-aware grouped reads
- Fixed 60-second polling interval
- Register and coil writes
- Write-access safety switch
- Config-entry reconfiguration
- German and English translations

## Supported model profiles

| Models | Heating circuits | Profile |
| --- | ---: | --- |
| TROVIS 5573, 5575, 5576 | Rk1 and Rk2 | TROVIS 5573 |
| TROVIS 5578, 5579 | Rk1, Rk2, and Rk3 | TROVIS 5578 |

The domestic-hot-water circuit is represented as Rk4.

## Installation

1. Download or clone this repository.
2. Copy the directory `custom_components/trovis557x` into the Home Assistant configuration directory `/config/custom_components/trovis557x`.
3. Restart Home Assistant.
4. Open `Settings → Devices & services → Add integration`.
5. Search for `Samson Trovis 557x`.

## Connection setup

The setup flow offers two connection paths.

### Network

Enter:

- host or IP address
- TCP port
- Modbus unit ID

The integration automatically tries both network protocols:

1. transparent Modbus RTU over TCP
2. native Modbus TCP with MBAP framing

The successful framing mode is stored with the config entry and reused during normal operation.

### Serial or serial URL

The serial path supports local ports and serial URLs handled by the underlying serial transport, for example:

```text
/dev/ttyUSB0
socket://192.168.1.50:502
rfc2217://192.168.1.50:2217
esphome://...
```

The TROVIS serial line uses 9,600 or 19,200 baud depending on PA6; the TROVIS 5573 is fixed to 19,200 baud. The current integration uses 19,200 baud, 8N1.

A `socket://` URL belongs to the serial setup path and represents transparent serial forwarding. Native Modbus TCP belongs to the network setup path.

## Automatic setup probe

Before the config entry is created, the integration:

1. opens a temporary connection
2. reads the controller model
3. selects the matching register and coil profile
4. detects physical sensors with valid values
5. determines the available heating circuits
6. stores the detected configuration

Only heating circuits supported by the detected model are polled and exposed.

Physical sensor entities are created only for sensors detected during setup. Opening the reconfigure flow runs the detection again and adds newly discovered sensors without removing previously known entities.

## Device and entity structure

The controller is represented as the main Home Assistant device.

Linked functional subdevices are created for:

- Rk1 – Heating circuit 1
- Rk2 – Heating circuit 2
- Rk3 – Heating circuit 3, where supported
- Rk4 – Domestic hot water
- Measurements

Entity platforms currently include:

- `sensor`
- `binary_sensor`
- `number`
- `select`
- `switch`
- `climate`
- `water_heater`

The complete current entity structure is documented in the [wiki](https://github.com/Tom-Bom-badil/trovis-modbus-hass/wiki).

## Writing values

Writable registers and coils are exposed as appropriate Home Assistant entities, including:

- numbers
- selects
- switches
- climate entities
- water-heater entities

Writing is protected by the controller-level **Write access** switch.

When enabled, writes use the configured TROVIS access code. Limits, steps, enum options, scaling, and TROVIS-specific write preconditions are provided by the `trovis-modbus` library.

## Reconfiguration

Use the integration menu and select **Reconfigure** to edit:

- network host and port, or serial port/URL
- Modbus unit ID
- display name
- write-access code

The entity-ID prefix remains unchanged so existing entity IDs stay stable.

After validation, the integration automatically:

- detects the model again
- detects sensors again
- detects network framing again
- updates the config entry
- reloads the integration

## Polling and connection recovery

The controller is polled every 60 seconds.

Reads are grouped by `modbus-connection` while respecting:

- model-specific readable ranges
- manufacturer block boundaries
- known address gaps
- a maximum request span of 50 registers or coils

If the connection is lost, the config entry is reloaded so the connection can be established again.

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
modbus-connection
        │
        ▼
tmodbus / serialx
        │
        ▼
Physical TROVIS device
```

The responsibilities are deliberately separated:

- `trovis-modbus` owns TROVIS datapoints, metadata, validation, ranges, and write semantics.
- `trovis-modbus-hass` maps those datapoints to Home Assistant devices and entities.
- `modbus-connection` provides backend-neutral connection and device-model abstractions.
- `tmodbus` and `serialx` provide the actual transports.

## Development

Install the local device library first:

```bash
cd /config/dev/trovis-modbus
python -m pip install -e .
```

Then prepare and check the integration:

```bash
cd /config/dev/trovis-modbus-hass
python -m compileall custom_components/trovis557x
```

For the repository test and lint environment:

```bash
uv sync
uv run pytest
uvx prek run --all-files
```

Please read the [contributor and branch workflow](https://github.com/Tom-Bom-badil/trovis-modbus-hass/wiki/Contributions) before opening a pull request.
