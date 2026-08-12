# SAMSON TROVIS 557x – Home Assistant Custom Integration
[![CI](https://github.com/Tom-Bom-badil/trovis-modbus-hass/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/Tom-Bom-badil/trovis-modbus-hass/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Tom-Bom-badil/trovis-modbus-hass?include_prereleases)](https://github.com/Tom-Bom-badil/trovis-modbus-hass/releases)
[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom%20(not%20listed)-41BDF5.svg)](https://www.hacs.xyz/docs/faq/custom_repositories/)
[![License](https://img.shields.io/github/license/Tom-Bom-badil/trovis-modbus-hass.svg)](LICENSE)
<img width="100%" alt="SAMSON TROVIS controllers" src="https://github.com/user-attachments/assets/2afe0be0-614a-4dbd-9fdc-4132434ffd36" />

<br/>

`trovis-modbus-hass` is a Home Assistant custom integration for monitoring and
adjusting SAMSON TROVIS 557x heating and district heating controllers over
Modbus, including compatible OEM variants from Sauter, Pewo, Yados and others.

The integration automatically detects the controller model, configured hydronic
system, technical control-circuit roles, and available physical sensor inputs.
It then creates a matching Home Assistant device and entity structure without
requiring a Modbus YAML configuration.

The TROVIS controller continues to perform the actual heating control. Home
Assistant reads its operating state and, when explicitly enabled, writes
supported settings back to it.

The integration is intended primarily for simple monitoring of an already
commissioned system and for occasional fine adjustment; it does not attempt
to reproduce all possible configurations and functions.

## Features

Depending on the detected controller and hydronic configuration, the integration
provides:
- UI-based setup without Modbus YAML or a separate Modbus integration,
- native Modbus TCP, RTU over TCP, and serial Modbus RTU connections,
- support for multiple independently configured controllers,
- automatic controller-model and hydronic-system identification,
- model-, role-, and configuration-aware entity selection,
- linked sub-devices for Measurements, Rk1 through Rk4, Solar, and buffer-tank
  functions where applicable,
- Home Assistant `sensor`, `binary_sensor`, `number`, `select`, `switch`, `date`,
  `time`, `climate`, and `water_heater` entities,
- grouped reads and validated register and coil writes,
- a controller-level **Write access** safety switch,
- German and English translations.

## Supported controllers

The folllwoing controllers are currently supported:

- SAMSON TROVIS 5573, 5573-1, 5575, 5576, 5578, 5578-E, 5579
- SAUTER EQJW-126F001, -146F001, -146F002, -246F002, -246F003
- YADOS YADO\|MATIC 01, 01-0003, 03, 03-1003, 08
- PEWO PCR06

<sup>(for detals, see the [project wiki](https://github.com/Tom-Bom-badil/trovis-modbus-hass/wiki))</sup>

## Related projects

- [`trovis-modbus`](https://github.com/Tom-Bom-badil/trovis-modbus) –
  controller-specific data model and read/write logic
- [`modbus-connection`](https://github.com/home-assistant-libs/modbus-connection) –
  backend-neutral Modbus connection API used internally by the integration

## Documentation

Lots of in-depth insights into how everything works, including installation
instructions, adapter configuration and tests, troubleshooting guides and
technical backgrounds can be found on the [project wiki](https://github.com/Tom-Bom-badil/trovis-modbus-hass/wiki).

If any information you are searching for should be missing on this Wiki, check
out the [Wiki](https://github.com/Tom-Bom-badil/samson_trovis_557x/wiki) and the [discussions](https://github.com/Tom-Bom-badil/samson_trovis_557x/discussions) of our 'old' Trovis project, where we have collected information on the
controller and Modbus in general over many years.
