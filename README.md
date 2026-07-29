# SAMSON TROVIS 557x – Home Assistant Custom Integration

[![CI](https://github.com/Tom-Bom-badil/trovis-modbus-hass/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/Tom-Bom-badil/trovis-modbus-hass/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Tom-Bom-badil/trovis-modbus-hass?include_prereleases)](https://github.com/Tom-Bom-badil/trovis-modbus-hass/releases)
[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom%20(not%20listed)-41BDF5.svg)](https://www.hacs.xyz/docs/faq/custom_repositories/)
[![License](https://img.shields.io/github/license/Tom-Bom-badil/trovis-modbus-hass.svg)](LICENSE)

<img width="100%" alt="SAMSON TROVIS controllers" src="https://github.com/user-attachments/assets/2afe0be0-614a-4dbd-9fdc-4132434ffd36" />

<br/>

`trovis-modbus-hass` is a Home Assistant custom integration for monitoring and
adjusting SAMSON TROVIS 557x heating and district heating controllers over
Modbus, including compatible OEM variants recognized by the underlying
[`trovis-modbus`](https://github.com/Tom-Bom-badil/trovis-modbus) library.

The integration automatically detects the controller model, configured hydronic
system, technical control-circuit roles, and available physical sensor inputs.
It then creates a matching Home Assistant device and entity structure without
requiring Modbus YAML configuration.

The TROVIS controller continues to perform the actual heating control. Home
Assistant reads its operating state and, when explicitly enabled, writes
supported settings back to it. The integration is intended primarily for
monitoring an already commissioned system and for occasional fine adjustment;
it does not attempt to reproduce the complete TROVIS user interface.

Physical Modbus connections are configured and managed by the separate Home
Assistant `modbus_connection` integration. `trovis-modbus-hass` selects an
existing connection and uses the shared Modbus unit provided by it.

## Features

Depending on the detected controller and hydronic configuration, the integration
provides:

- UI-based setup without Modbus YAML,
- support for multiple controllers and shared Modbus connections,
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

| Controller                | Rk1-Rk3 / Heating | Rk4 / DHW | Hydronic systems | Comments                             |
| :------------------------ | :--------------: | :-----: | :--------------: | :------------------------------------|
| SAMSON TROVIS 5573        |                2 |    x    |               29 |                                      |
| SAMSON TROVIS 5573-1      |                2 |    x    |               29 |                                      |
| SAMSON TROVIS 5575        |                2 |    x    |               33 |                                      |
| SAMSON TROVIS 5576        |                2 |    x    |               52 |                                      |
| SAMSON TROVIS 5578        |                3 |    x    |               90 |                                      |
| SAMSON TROVIS 5578-E      |                3 |    x    |               95 |                                      |
| SAMSON TROVIS 5579        |                3 |    x    |               85 |                                      |
| SAUTER EQJW126F001        |                1 |         |                1 | TROVIS 5573, Rk1 and Anlage 1.0 only |
| SAUTER EQJW146F001        |                2 |    x    |               29 | TROVIS 5573                          |
| SAUTER EQJW146F002        |                2 |    x    |               29 | TROVIS 5573-1                        |
| SAUTER EQJW246F002        |                3 |    x    |               90 | TROVIS 5578                          |
| SAUTER EQJW246F003        |                3 |    x    |               95 | TROVIS 5578-E                        |
| YADOS YADO\|MATIC 01      |                2 |    x    |               33 | TROVIS 5575                          |
| YADOS YADO\|MATIC 01-0003 |                2 |    x    |               33 | TROVIS 5575                          |
| YADOS YADO\|MATIC 03      |                2 |    x    |               29 | TROVIS 5573                          |
| YADOS YADO\|MATIC 03-1003 |                2 |    x    |               29 | TROVIS 5573-1                        |
| YADOS YADO\|MATIC 08      |                3 |    x    |               90 | TROVIS 5578-1114                     |
| PEWO PCR06                |                2 |    x    |               33 | TROVIS 5575                          |

<sup>Note: The non-SAMSON models have not yet been tested. The figures are based on the currently available documentation.</sup>

Compatible SAUTER, YADOS, PEWO, and other OEM controllers may use the
corresponding TROVIS model profile. See the
[project wiki](https://github.com/Tom-Bom-badil/trovis-modbus-hass/wiki) and the
[`trovis-modbus` documentation](https://github.com/Tom-Bom-badil/trovis-modbus/wiki)
for model-specific details and current testing status.

## Installation

A configured `modbus_connection` entry is required before adding a TROVIS
controller.

[![Open your Home Assistant instance and add this repository to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Tom-Bom-badil&repository=trovis-modbus-hass&category=integration)

Install the integration through HACS or copy
`custom_components/trovis557x` to `/config/custom_components/trovis557x`, restart
Home Assistant, and add **SAMSON TROVIS 557x** from **Settings → Devices &
services**.

Detailed installation instructions, connection framing, device and entity
structure, write behavior, troubleshooting, development setup, and contribution
guidance are documented in the
[project wiki](https://github.com/Tom-Bom-badil/trovis-modbus-hass/wiki).

## Related projects

- [`trovis-modbus`](https://github.com/Tom-Bom-badil/trovis-modbus) –
  controller-specific data model and read/write logic
- [`modbus-connection`](https://github.com/home-assistant-libs/modbus-connection) –
  shared backend-neutral Modbus connection API

## License

Apache-2.0
