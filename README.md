# SAMSON TROVIS 557x – Home Assistant Custom Integration

> [!IMPORTANT]
> This project is still under development. Functions, device identities, and
> entity coverage may change between beta releases.
>
> The [project wiki](https://github.com/Tom-Bom-badil/trovis-modbus-hass/wiki)
> contains the detailed setup guide, current entity structure, architecture
> notes, and
> [instructions for contributors](https://github.com/Tom-Bom-badil/trovis-modbus-hass/wiki/Contributions).

This repository contains a native Home Assistant custom integration for SAMSON
TROVIS 557x heating controllers. It can also be usable with some OEM Sauter and
Pewo controllers derived from the same platform.

The integration detects the controller model, hydronic system, active
control-circuit roles, and physical sensors. It then creates a matching Home
Assistant device structure without requiring Modbus YAML configuration.

Physical Modbus connections are currently configured and owned by the separate
Home Assistant `modbus_connection` integration.

## Scope

The integration is designed primarily for monitoring an already commissioned
heating system and for occasional fine adjustment, for example:

- checking temperatures, pumps, operating modes, and controller state
- changing an Rk operating mode
- fine-tuning setpoints, heating curves, or temperature limits
- adjusting selected domestic-hot-water, solar, or buffer-tank parameters
- correcting controller date and time

It does not attempt to reproduce the complete TROVIS user interface or expose
every possible CO/PA parameter and special function.

## Features

- UI-based setup without Modbus YAML
- Shared Modbus connections
- Multiple TROVIS controllers
- Automatic controller-model detection
- Automatic hydronic-system identification
- Automatic physical-sensor detection
- Role-aware `Rk1` through `Rk4` sub-devices
- Heating, pre-control, buffer-tank, and domestic-hot-water roles
- Domestic-hot-water entities only when `Rk4` is present
- Climate entities only for actual heating circuits
- Dedicated Solar sub-device for solar-thermal systems
- Buffer-tank status and selected charging controls under `Rk1`
- Model- and hydronic-system-aware entity selection
- Network, local serial, and serial-URL connections
- Range-aware grouped reads
- Register and coil writes
- Controller-level write-access safety switch
- Native date and time entities
- German and English translations

## Supported controllers

| Controller | Technical slots Rk1-Rk3 | Documented hydronic systems |
| --- | ---: | ---: |
| TROVIS 5573 | 2 | 29 |
| TROVIS 5573-1 | 2 | 29 |
| TROVIS 5575 | 2 | 33 |
| TROVIS 5576 | 2 | 52 |
| TROVIS 5578 | 3 | 90 |
| TROVIS 5578-E | 3 | 95 |
| TROVIS 5579 | 3 | 85 |

The integration uses the model and hydronic metadata provided by
[`trovis-modbus`](https://github.com/Tom-Bom-badil/trovis-modbus).

## Device structure

The physical controller is the main Home Assistant device. Functional areas are
created as linked sub-devices only when they are relevant:

```text
SAMSON TROVIS 557x
├── Controller
├── Measurements
├── Rk1 – role-dependent name
│   └── Buffer-tank extensions when Rk1 has the BUFFER_TANK role
├── Rk2 – role-dependent name
├── Rk3 – role-dependent name
├── Rk4 – DHW / domestic hot water, when present
└── Solar – solar circuit, when present
```

Examples of role-dependent names include:

```text
Rk1 – Heating circuit 1
Rk1 – Pre-control circuit
Rk1 – Buffer-tank circuit
Rk2 – Heating circuit 2
Rk3 – Heating circuit 3
Rk4 – DHW / domestic hot water
```

The Rk number always identifies the technical controller slot. Slots are never
renumbered according to their role.

## Physical sensor identities

Physical measurement entities use the documented TROVIS abbreviations in both
their entity IDs and visible names. A unique, user-definable device slug (entered during setup) and the original manufacturer sensor abbreviations are used to make identification easy: `platform`.`<device_slug>`\_sensor\_`abbreviation`.

Examples:

```text
sensor.t5579_sensor_af1
AF1 Outside sensor 1

sensor.t5579_sensor_sf1
SF1 Storage sensor 1

sensor.t5579_sensor_ruef1
RüF1 Return-flow sensor 1

sensor.t5579_sensor_imp
IMP Pulse rate
```

Note: German `RüF` (return sensor) is written as ASCII `ruef` in technical IDs.

Sensor entities remain in the separate **Measurements** sub-device. Their
identity is independent of the Rk role that may use the measured value.

## Entity platforms

The integration currently provides:

- `sensor`
- `binary_sensor`
- `number`
- `select`
- `switch`
- `date`
- `time`
- `climate`
- `water_heater`

Standard Home Assistant entities are the primary representation of the TROVIS
data model. `climate` and `water_heater` provide convenience views over the same
library-backed values.

Writable values are protected by the controller-level **Write access** switch.
Limits, options, scaling, model availability, and TROVIS-specific write rules
are provided by the
[`trovis-modbus`](https://github.com/Tom-Bom-badil/trovis-modbus) library.

## Prerequisite

Before adding a TROVIS controller, install the Home Assistant
`modbus_connection` integration and create at least one connection entry.

Use:

- **Network** for native Modbus TCP or a gateway that translates Modbus TCP to
  Modbus RTU
- **Serial** with a URL such as `socket://192.168.1.50:502` for transparent RTU
  over TCP using a ser2net-style adapter
- **Serial** with a URL such as `esphome://192.168.1.50` for supported
  ESP-based serial forwarding
- **Serial** with `/dev/ttyUSB0`, `rfc2217://...`, or another supported serial
  URL for local or forwarded serial connections

A serial URL uses transparent serial forwarding over TCP. It is not native
Modbus TCP.

The shared Modbus connection architecture in Home Assistant Core is still under
development. TROVIS currently keeps this connection layer separate so the
controller model, entity model, and hydronic logic can evolve independently.

## Installation

### HACS

[![Open your Home Assistant instance and add this repository to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Tom-Bom-badil&repository=trovis-modbus-hass&category=integration)

1. Make sure [HACS](https://www.hacs.xyz/) is installed in Home Assistant.
2. Click the badge above and add this repository as an **Integration**.
3. Return to HACS, search for **SAMSON TROVIS 557x**, and download the
   integration.
4. Restart Home Assistant.
5. Open **Settings → Devices & services → Add integration**.
6. Search for **SAMSON TROVIS 557x**.
7. Select an existing Modbus Connection entry and enter the controller's
   Modbus unit ID.

The default TROVIS unit ID is `246`, but may be different in your device.

### Manual installation

1. Download the latest release from the
   [GitHub releases page](https://github.com/Tom-Bom-badil/trovis-modbus-hass/releases).
2. Copy `custom_components/trovis557x` to
   `/config/custom_components/trovis557x`.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Add integration**.
5. Search for **SAMSON TROVIS 557x**.
6. Select an existing Modbus Connection entry and enter the controller's
   Modbus unit ID.

## Breaking changes in this beta

This beta changes the technical identities of control-circuit and physical
sensor entities:

- former `hk1` to `hk3` identities are replaced by `rk1` to `rk3`
- former `ww` identities are replaced by `rk4`
- physical sensor IDs now consistently include their TROVIS abbreviation

Existing dashboards, automations, scripts, and history references may therefore
require adjustment.

For a clean beta test:

1. Remove the existing **SAMSON TROVIS 557x** config entries.
2. Keep the existing `modbus_connection` entries.
3. Update the integration and its required `trovis-modbus` version.
4. Restart Home Assistant.
5. Add the TROVIS controllers again through the config flow.
6. Check dashboards and automations for changed entity IDs.

An automatic migration for the former beta identities is intentionally not
provided.

## Architecture

```text
Home Assistant entities and devices
                │
                ▼
trovis-modbus-hass (this integration)
  Config flow, coordinator, translations,
  device registry, entity platforms
                │
                ▼
trovis-modbus (the trovis library on pypi)
  TROVIS models, hydronic roles, sensors,
  metadata, validation, read/write logic
                │
                ▼
Home Assistant modbus_connection integration
                │
                ▼
modbus-connection and the selected backend
                │
                ▼
Physical TROVIS controller or gateway
```

The TROVIS integration does not open or close the physical connection. It
selects an existing `modbus_connection` config entry and obtains a shared
Modbus unit from it.

Future outlook: A future migration to the shared API planned for
`homeassistant.components.modbus` should be limited mainly to the connection
provider, config flow, manifest, and stored connection parameters. The TROVIS
device model and entity logic are intentionally kept independent of that
migration.

## Development

Install the local device library when required:

```bash
cd /config/dev/trovis-modbus
python -m pip install -e .
```

Format the integration and run the local checks:

```bash
cd /config/dev/trovis-modbus-hass
script/format.sh
script/hasscheck.sh
```

- `format.sh` applies safe Ruff fixes and formats the repository.
- `hasscheck.sh` verifies formatting and linting, compiles the integration and
  tests, and validates JSON files.

After local checks, restart Home Assistant and perform a live test with a real
controller. The complete Home Assistant integration test suite requires a
prepared Home Assistant development environment and is also executed by GitHub
Actions.

## License

Apache-2.0
