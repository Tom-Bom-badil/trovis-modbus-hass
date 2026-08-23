"""Config flow for Trovis 557x."""

from __future__ import annotations

import re
from contextlib import suppress
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SerialPortSelector,
    TextSelector,
)
from homeassistant.util import slugify
from modbus_connection import ModbusError
from trovis_modbus import DEFAULT_WRITE_ACCESS_CODE, Trovis557x

from . import create_modbus_connection
from .const import (
    CONF_ACCESS_CODE,
    CONF_BAUDRATE,
    CONF_BYTESIZE,
    CONF_CONNECTION_TYPE,
    CONF_DETECTED_SENSORS,
    CONF_DEVICE,
    CONF_FRAMER,
    CONF_HOST,
    CONF_MODEL,
    CONF_PARITY,
    CONF_PORT,
    CONF_SLUG,
    CONF_STOPBITS,
    CONF_UNIT_ID,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    DEFAULT_BAUDRATE,
    DEFAULT_BYTESIZE,
    DEFAULT_FRAMER,
    DEFAULT_PARITY,
    DEFAULT_PORT,
    DEFAULT_SLUG,
    DEFAULT_STOPBITS,
    DEFAULT_UNIT_ID,
    DOMAIN,
    FRAMER_RTU,
    FRAMER_SOCKET,
)

_UNIT = NumberSelector(
    NumberSelectorConfig(
        min=1,
        max=255,
        step=1,
        mode=NumberSelectorMode.BOX,
    )
)
_ACCESS_CODE = NumberSelector(
    NumberSelectorConfig(
        min=0,
        max=9999,
        step=1,
        mode=NumberSelectorMode.BOX,
    )
)
_PORT = NumberSelector(
    NumberSelectorConfig(
        min=1,
        max=65535,
        step=1,
        mode=NumberSelectorMode.BOX,
    )
)
_TCP_FRAMER = SelectSelector(
    SelectSelectorConfig(
        options=[FRAMER_SOCKET, FRAMER_RTU],
        mode=SelectSelectorMode.DROPDOWN,
        translation_key="tcp_framer",
    )
)


def _network_schema() -> vol.Schema:
    """Return the network connection schema."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST): TextSelector(),
            vol.Required(CONF_PORT, default=DEFAULT_PORT): _PORT,
            vol.Required(CONF_FRAMER, default=DEFAULT_FRAMER): _TCP_FRAMER,
            vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): _UNIT,
        }
    )


def _serial_schema() -> vol.Schema:
    """Return the serial connection schema."""
    return vol.Schema(
        {
            vol.Required(CONF_DEVICE): SerialPortSelector(),
            vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): vol.Coerce(int),
            vol.Required(CONF_PARITY, default=DEFAULT_PARITY): vol.In(["N", "E", "O"]),
            vol.Required(CONF_STOPBITS, default=DEFAULT_STOPBITS): vol.In([1, 2]),
            vol.Required(CONF_BYTESIZE, default=DEFAULT_BYTESIZE): vol.In([7, 8]),
            vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): _UNIT,
        }
    )


def _normalize_slug(value: object) -> str:
    """Return a Home Assistant friendly entity prefix."""
    slug = slugify(str(value or ""))
    return re.sub(r"_+", "_", slug).strip("_") or DEFAULT_SLUG


def _normalize_name(value: object, fallback: str) -> str:
    """Return a non-empty display name."""
    name = str(value or "").strip()
    return name or fallback


def _device_schema(default_name: str, default_slug: str) -> vol.Schema:
    """Return the device setup schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_NAME,
                default=default_name,
            ): TextSelector(),
            vol.Required(
                CONF_SLUG,
                default=default_slug,
            ): TextSelector(),
            vol.Required(
                CONF_ACCESS_CODE,
                default=DEFAULT_WRITE_ACCESS_CODE,
            ): _ACCESS_CODE,
        }
    )


def _reconfigure_network_schema() -> vol.Schema:
    """Return the reconfigure schema for a network connection."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST): TextSelector(),
            vol.Required(CONF_PORT, default=DEFAULT_PORT): _PORT,
            vol.Required(CONF_FRAMER, default=DEFAULT_FRAMER): _TCP_FRAMER,
            vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): _UNIT,
            vol.Required(CONF_NAME): TextSelector(),
            vol.Required(CONF_ACCESS_CODE): _ACCESS_CODE,
        }
    )


def _reconfigure_serial_schema() -> vol.Schema:
    """Return the reconfigure schema for a serial connection."""
    return vol.Schema(
        {
            vol.Required(CONF_DEVICE): SerialPortSelector(),
            vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): vol.Coerce(int),
            vol.Required(CONF_PARITY, default=DEFAULT_PARITY): vol.In(["N", "E", "O"]),
            vol.Required(CONF_STOPBITS, default=DEFAULT_STOPBITS): vol.In([1, 2]),
            vol.Required(CONF_BYTESIZE, default=DEFAULT_BYTESIZE): vol.In([7, 8]),
            vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): _UNIT,
            vol.Required(CONF_NAME): TextSelector(),
            vol.Required(CONF_ACCESS_CODE): _ACCESS_CODE,
        }
    )


async def _async_probe(
    data: dict[str, Any],
) -> tuple[int, tuple[str, ...]] | None:
    """Probe a controller through a temporary TROVIS-owned connection."""
    connection = None
    try:
        connection = create_modbus_connection(data)
        unit = connection.for_unit(int(data[CONF_UNIT_ID]))
        probe = await Trovis557x.async_probe(unit)
    except (ModbusError, OSError, ValueError):
        return None
    finally:
        if connection is not None:
            with suppress(ModbusError, OSError):
                await connection.close()

    return probe.model, probe.detected_sensors


class TrovisConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Trovis 557x."""

    VERSION = 2

    _pending_data: dict[str, Any] | None = None
    _detected_model: int | None = None
    _detected_sensors: tuple[str, ...] = ()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Let the user choose the Modbus transport."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["network", "serial"],
        )

    async def async_step_network(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure and probe a Modbus TCP or RTU-over-TCP controller."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
                CONF_HOST: str(user_input[CONF_HOST]).strip(),
                CONF_PORT: int(user_input[CONF_PORT]),
                CONF_FRAMER: str(user_input[CONF_FRAMER]),
                CONF_UNIT_ID: int(user_input[CONF_UNIT_ID]),
            }

            probe = await _async_probe(data)
            if probe is None:
                errors["base"] = "cannot_connect"
            else:
                model, detected_sensors = probe
                self._pending_data = data
                self._detected_model = model
                self._detected_sensors = detected_sensors
                return await self.async_step_device()

        return self.async_show_form(
            step_id="network",
            data_schema=_network_schema(),
            errors=errors,
        )

    async def async_step_serial(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure and probe a Modbus RTU serial controller."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                CONF_CONNECTION_TYPE: CONNECTION_TYPE_SERIAL,
                CONF_DEVICE: str(user_input[CONF_DEVICE]),
                CONF_BAUDRATE: int(user_input[CONF_BAUDRATE]),
                CONF_PARITY: str(user_input[CONF_PARITY]),
                CONF_STOPBITS: int(user_input[CONF_STOPBITS]),
                CONF_BYTESIZE: int(user_input[CONF_BYTESIZE]),
                CONF_UNIT_ID: int(user_input[CONF_UNIT_ID]),
            }

            probe = await _async_probe(data)
            if probe is None:
                errors["base"] = "cannot_connect"
            else:
                model, detected_sensors = probe
                self._pending_data = data
                self._detected_model = model
                self._detected_sensors = detected_sensors
                return await self.async_step_device()

        return self.async_show_form(
            step_id="serial",
            data_schema=_serial_schema(),
            errors=errors,
        )

    async def async_step_device(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure device name, entity prefix and access code."""
        if self._pending_data is None or self._detected_model is None:
            return await self.async_step_user()

        default_name = f"Trovis {self._detected_model}"
        default_slug = _normalize_slug(default_name)

        if user_input is not None:
            name = _normalize_name(
                user_input.get(CONF_NAME),
                default_name,
            )
            slug = _normalize_slug(user_input.get(CONF_SLUG) or name)
            data = {
                **self._pending_data,
                CONF_NAME: name,
                CONF_SLUG: slug,
                CONF_ACCESS_CODE: int(
                    user_input.get(
                        CONF_ACCESS_CODE,
                        DEFAULT_WRITE_ACCESS_CODE,
                    )
                ),
                CONF_MODEL: self._detected_model,
                CONF_DETECTED_SENSORS: list(self._detected_sensors),
            }
            return self.async_create_entry(
                title=name,
                data=data,
            )

        return self.async_show_form(
            step_id="device",
            data_schema=_device_schema(
                default_name,
                default_slug,
            ),
            errors={},
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Let the user choose the transport for reconfiguration."""
        return self.async_show_menu(
            step_id="reconfigure",
            menu_options=["reconfigure_network", "reconfigure_serial"],
        )

    async def async_step_reconfigure_network(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Reconfigure a controller using TCP or RTU-over-TCP."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            name = _normalize_name(
                user_input.get(CONF_NAME),
                entry.title,
            )
            probe_data = {
                CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
                CONF_HOST: str(user_input[CONF_HOST]).strip(),
                CONF_PORT: int(user_input[CONF_PORT]),
                CONF_FRAMER: str(user_input[CONF_FRAMER]),
                CONF_UNIT_ID: int(user_input[CONF_UNIT_ID]),
            }

            probe = await _async_probe(probe_data)
            if probe is None:
                errors["base"] = "cannot_connect"
            else:
                return self._finish_reconfigure(
                    entry,
                    probe_data,
                    name,
                    int(
                        user_input.get(
                            CONF_ACCESS_CODE,
                            DEFAULT_WRITE_ACCESS_CODE,
                        )
                    ),
                    probe,
                )

        suggested_values = {
            **entry.data,
            **entry.options,
            CONF_NAME: entry.data.get(CONF_NAME, entry.title),
            CONF_ACCESS_CODE: entry.data.get(
                CONF_ACCESS_CODE,
                DEFAULT_WRITE_ACCESS_CODE,
            ),
        }
        return self.async_show_form(
            step_id="reconfigure_network",
            data_schema=self.add_suggested_values_to_schema(
                _reconfigure_network_schema(),
                suggested_values,
            ),
            errors=errors,
        )

    async def async_step_reconfigure_serial(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Reconfigure a controller using Modbus RTU serial."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            name = _normalize_name(
                user_input.get(CONF_NAME),
                entry.title,
            )
            probe_data = {
                CONF_CONNECTION_TYPE: CONNECTION_TYPE_SERIAL,
                CONF_DEVICE: str(user_input[CONF_DEVICE]),
                CONF_BAUDRATE: int(user_input[CONF_BAUDRATE]),
                CONF_PARITY: str(user_input[CONF_PARITY]),
                CONF_STOPBITS: int(user_input[CONF_STOPBITS]),
                CONF_BYTESIZE: int(user_input[CONF_BYTESIZE]),
                CONF_UNIT_ID: int(user_input[CONF_UNIT_ID]),
            }

            probe = await _async_probe(probe_data)
            if probe is None:
                errors["base"] = "cannot_connect"
            else:
                return self._finish_reconfigure(
                    entry,
                    probe_data,
                    name,
                    int(
                        user_input.get(
                            CONF_ACCESS_CODE,
                            DEFAULT_WRITE_ACCESS_CODE,
                        )
                    ),
                    probe,
                )

        suggested_values = {
            **entry.data,
            **entry.options,
            CONF_NAME: entry.data.get(CONF_NAME, entry.title),
            CONF_ACCESS_CODE: entry.data.get(
                CONF_ACCESS_CODE,
                DEFAULT_WRITE_ACCESS_CODE,
            ),
        }
        return self.async_show_form(
            step_id="reconfigure_serial",
            data_schema=self.add_suggested_values_to_schema(
                _reconfigure_serial_schema(),
                suggested_values,
            ),
            errors=errors,
        )

    def _finish_reconfigure(
        self,
        entry,
        probe_data: dict[str, Any],
        name: str,
        access_code: int,
        probe: tuple[int, tuple[str, ...]],
    ) -> ConfigFlowResult:
        """Apply a successful reconfiguration while retaining known sensors."""
        model, detected_sensors = probe
        known_sensors = set(
            entry.data.get(
                CONF_DETECTED_SENSORS,
                (),
            )
        )
        known_sensors.update(
            entry.options.get(
                CONF_DETECTED_SENSORS,
                (),
            )
        )
        known_sensors.update(detected_sensors)

        # Reconfiguration can switch transports. Replace the complete transport
        # block instead of merging it so stale TCP keys do not survive a switch
        # to serial and stale serial keys do not survive a switch to TCP.
        connection_keys = {
            CONF_CONNECTION_TYPE,
            CONF_HOST,
            CONF_PORT,
            CONF_FRAMER,
            CONF_DEVICE,
            CONF_BAUDRATE,
            CONF_PARITY,
            CONF_STOPBITS,
            CONF_BYTESIZE,
            CONF_UNIT_ID,
        }
        data = {
            key: value
            for key, value in entry.data.items()
            if key not in connection_keys
        }
        data.update(probe_data)
        data.update(
            {
                CONF_NAME: name,
                CONF_ACCESS_CODE: access_code,
                CONF_MODEL: model,
                CONF_DETECTED_SENSORS: sorted(known_sensors),
            }
        )

        return self.async_update_reload_and_abort(
            entry,
            title=name,
            data=data,
            options={},
        )
