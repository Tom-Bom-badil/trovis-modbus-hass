"""Config flow for Trovis 557x."""

from __future__ import annotations

from contextlib import suppress
import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_DEVICE, CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SerialPortSelector,
    TextSelector,
)
from homeassistant.util import slugify

from modbus_connection import ModbusConnection, ModbusError
from modbus_connection.tmodbus import connect_serial, connect_tcp

from ._local_dev import apply_local_trovis_modbus_override

apply_local_trovis_modbus_override()

from trovis_modbus import DEFAULT_WRITE_ACCESS_CODE, Trovis557x

from .const import (
    CONF_ACCESS_CODE,
    CONF_CONNECTION_TYPE,
    CONF_DETECTED_SENSORS,
    CONF_MODEL,
    CONF_NETWORK_FRAMER,
    CONF_SLUG,
    CONF_UNIT_ID,
    CONNECTION_SERIAL,
    CONNECTION_TCP,
    DEFAULT_PORT,
    DEFAULT_SLUG,
    DEFAULT_UNIT_ID,
    DOMAIN,
    NETWORK_FRAMER_RTU,
    NETWORK_FRAMER_SOCKET,
    SERIAL_BAUDRATE,
    SERIAL_BYTESIZE,
    SERIAL_PARITY,
    SERIAL_STOPBITS,
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


def _normalize_slug(value: object) -> str:
    """Return a Home Assistant friendly entity prefix."""
    slug = slugify(str(value or ""))
    return re.sub(r"_+", "_", slug).strip("_") or DEFAULT_SLUG


def _normalize_name(value: object, fallback: str) -> str:
    """Return a non-empty display name."""
    name = str(value or "").strip()
    return name or fallback


STEP_NETWORK = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): _UNIT,
    }
)

STEP_SERIAL = vol.Schema(
    {
        vol.Required(CONF_DEVICE): SerialPortSelector(),
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): _UNIT,
    }
)


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


def _reconfigure_schema(
    connection_type: str,
    current_device: str | None = None,
) -> vol.Schema:
    """Return the schema for an existing config entry."""
    common = {
        vol.Required(CONF_UNIT_ID): _UNIT,
        vol.Required(CONF_NAME): TextSelector(),
        vol.Required(CONF_ACCESS_CODE): _ACCESS_CODE,
    }

    if connection_type == CONNECTION_SERIAL:
        custom_url = bool(
            current_device
            and current_device.startswith(
                (
                    "socket://",
                    "rfc2217://",
                    "esphome://",
                )
            )
        )

        return vol.Schema(
            {
                vol.Required(CONF_DEVICE): (
                    TextSelector()
                    if custom_url
                    else SerialPortSelector()
                ),
                **common,
            }
        )

    return vol.Schema(
        {
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT): vol.Coerce(int),
            **common,
        }
    )


async def open_connection(data: dict[str, Any]) -> ModbusConnection:
    """Open the connection described by a config entry."""
    if data[CONF_CONNECTION_TYPE] == CONNECTION_SERIAL:
        return await connect_serial(
            data[CONF_DEVICE],
            baudrate=SERIAL_BAUDRATE,
            bytesize=SERIAL_BYTESIZE,
            parity=SERIAL_PARITY,
            stopbits=SERIAL_STOPBITS,
        )

    return await connect_tcp(
        data[CONF_HOST],
        port=int(data[CONF_PORT]),
        framer=data.get(
            CONF_NETWORK_FRAMER,
            NETWORK_FRAMER_RTU,
        ),
    )


async def _async_probe_once(
    data: dict[str, Any],
) -> tuple[int, tuple[str, ...]] | None:
    """Probe one specific connection configuration."""
    connection: ModbusConnection | None = None

    try:
        connection = await open_connection(data)
        probe = await Trovis557x.async_probe(
            connection.for_unit(int(data[CONF_UNIT_ID]))
        )
        return probe.model, probe.detected_sensors
    except (ModbusError, ValueError):
        return None
    finally:
        if connection is not None:
            with suppress(ModbusError):
                await connection.close()


async def _async_probe(
    data: dict[str, Any],
) -> tuple[int, tuple[str, ...], str | None] | None:
    """Probe the controller and detect network framing when required."""
    if data[CONF_CONNECTION_TYPE] == CONNECTION_SERIAL:
        result = await _async_probe_once(data)

        if result is None:
            return None

        model, detected_sensors = result
        return model, detected_sensors, None

    stored_framer = data.get(CONF_NETWORK_FRAMER)

    if stored_framer in (
        NETWORK_FRAMER_RTU,
        NETWORK_FRAMER_SOCKET,
    ):
        framers = (stored_framer,)
    else:
        framers = (
            NETWORK_FRAMER_RTU,
            NETWORK_FRAMER_SOCKET,
        )

    for framer in framers:
        result = await _async_probe_once(
            {
                **data,
                CONF_NETWORK_FRAMER: framer,
            }
        )

        if result is not None:
            model, detected_sensors = result
            return model, detected_sensors, framer

    return None


class TrovisConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Trovis 557x."""

    VERSION = 1

    _pending_data: dict[str, Any] | None = None
    _detected_model: int | None = None
    _detected_sensors: tuple[str, ...] = ()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Let the user choose the transport."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["network", "serial"],
        )

    async def async_step_network(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure a network connection."""
        return await self._connection_step(
            CONNECTION_TCP,
            "network",
            STEP_NETWORK,
            user_input,
        )

    async def async_step_serial(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure a Modbus serial RTU connection."""
        return await self._connection_step(
            CONNECTION_SERIAL,
            "serial",
            STEP_SERIAL,
            user_input,
        )

    async def _connection_step(
        self,
        connection_type: str,
        step_id: str,
        schema: vol.Schema,
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        """Validate connection data and continue setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                CONF_CONNECTION_TYPE: connection_type,
                **user_input,
            }

            probe = await _async_probe(data)

            if probe is None:
                errors["base"] = "cannot_connect"
            else:
                model, detected_sensors, network_framer = probe

                if network_framer is not None:
                    data[CONF_NETWORK_FRAMER] = network_framer

                self._pending_data = data
                self._detected_model = model
                self._detected_sensors = detected_sensors

                return await self.async_step_device()

        return self.async_show_form(
            step_id=step_id,
            data_schema=schema,
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
            slug = _normalize_slug(
                user_input.get(CONF_SLUG) or name
            )

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
                CONF_DETECTED_SENSORS: list(
                    self._detected_sensors
                ),
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
        """Update connection and controller settings."""
        entry = self._get_reconfigure_entry()
        connection_type = entry.data[CONF_CONNECTION_TYPE]
        errors: dict[str, str] = {}

        if user_input is not None:
            name = _normalize_name(
                user_input.get(CONF_NAME),
                entry.title,
            )

            # Deliberately omit the previously detected network framer here.
            # Reconfiguration must test both RTU-over-TCP and native Modbus TCP
            # again in case the gateway configuration has changed.
            probe_data = {
                CONF_CONNECTION_TYPE: connection_type,
                **user_input,
            }

            probe = await _async_probe(probe_data)

            if probe is None:
                errors["base"] = "cannot_connect"
            else:
                model, detected_sensors, network_framer = probe

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

                data_updates: dict[str, Any] = {
                    **user_input,
                    CONF_CONNECTION_TYPE: connection_type,
                    CONF_NAME: name,
                    CONF_ACCESS_CODE: int(
                        user_input.get(
                            CONF_ACCESS_CODE,
                            DEFAULT_WRITE_ACCESS_CODE,
                        )
                    ),
                    CONF_MODEL: model,
                    CONF_DETECTED_SENSORS: sorted(
                        known_sensors
                    ),
                }

                if network_framer is not None:
                    data_updates[CONF_NETWORK_FRAMER] = network_framer

                return self.async_update_reload_and_abort(
                    entry,
                    title=name,
                    data_updates=data_updates,
                    options={},
                )

        suggested_values = {
            **entry.data,
            **entry.options,
            CONF_NAME: entry.data.get(
                CONF_NAME,
                entry.title,
            ),
            CONF_ACCESS_CODE: entry.data.get(
                CONF_ACCESS_CODE,
                DEFAULT_WRITE_ACCESS_CODE,
            ),
        }

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                _reconfigure_schema(
                    connection_type,
                    entry.data.get(CONF_DEVICE),
                ),
                suggested_values,
            ),
            errors=errors,
        )
