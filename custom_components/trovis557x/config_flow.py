"""Config flow for Trovis 557x."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from custom_components.modbus_connection import async_get_unit
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)
from homeassistant.util import slugify
from modbus_connection import ModbusError
from trovis_modbus import DEFAULT_WRITE_ACCESS_CODE, Trovis557x

from .const import (
    CONF_ACCESS_CODE,
    CONF_CONNECTION_ENTRY_ID,
    CONF_DETECTED_SENSORS,
    CONF_MODEL,
    CONF_SLUG,
    CONF_UNIT_ID,
    DEFAULT_SLUG,
    DEFAULT_UNIT_ID,
    DOMAIN,
    MODBUS_CONNECTION_DOMAIN,
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


def _connection_options(hass: HomeAssistant) -> dict[str, str]:
    """Return selectable Modbus Connection config entries."""
    entries = sorted(
        hass.config_entries.async_entries(MODBUS_CONNECTION_DOMAIN),
        key=lambda entry: entry.title.casefold(),
    )

    return {
        entry.entry_id: entry.title or entry.entry_id
        for entry in entries
        if entry.disabled_by is None
    }


def _user_schema(hass: HomeAssistant) -> vol.Schema:
    """Return the initial setup schema."""
    return vol.Schema(
        {
            vol.Required(CONF_CONNECTION_ENTRY_ID): vol.In(_connection_options(hass)),
            vol.Required(
                CONF_UNIT_ID,
                default=DEFAULT_UNIT_ID,
            ): _UNIT,
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


def _reconfigure_schema(hass: HomeAssistant) -> vol.Schema:
    """Return the schema for an existing config entry."""
    return vol.Schema(
        {
            vol.Required(CONF_CONNECTION_ENTRY_ID): vol.In(_connection_options(hass)),
            vol.Required(CONF_UNIT_ID): _UNIT,
            vol.Required(CONF_NAME): TextSelector(),
            vol.Required(CONF_ACCESS_CODE): _ACCESS_CODE,
        }
    )


async def _async_probe(
    hass: HomeAssistant,
    data: dict[str, Any],
) -> tuple[int, tuple[str, ...]] | None:
    """Probe a controller through an existing shared connection."""
    try:
        unit = async_get_unit(
            hass,
            str(data[CONF_CONNECTION_ENTRY_ID]),
            int(data[CONF_UNIT_ID]),
        )
        probe = await Trovis557x.async_probe(unit)
    except (ConfigEntryNotReady, ModbusError, OSError, ValueError):
        return None

    return probe.model, probe.detected_sensors


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
        """Select a shared Modbus connection and probe the controller."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                CONF_CONNECTION_ENTRY_ID: str(user_input[CONF_CONNECTION_ENTRY_ID]),
                CONF_UNIT_ID: int(user_input[CONF_UNIT_ID]),
            }

            probe = await _async_probe(self.hass, data)

            if probe is None:
                errors["base"] = "cannot_connect"
            else:
                model, detected_sensors = probe

                self._pending_data = data
                self._detected_model = model
                self._detected_sensors = detected_sensors

                return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(self.hass),
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
        """Update shared connection and controller settings."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            name = _normalize_name(
                user_input.get(CONF_NAME),
                entry.title,
            )

            probe_data = {
                CONF_CONNECTION_ENTRY_ID: str(user_input[CONF_CONNECTION_ENTRY_ID]),
                CONF_UNIT_ID: int(user_input[CONF_UNIT_ID]),
            }

            probe = await _async_probe(
                self.hass,
                probe_data,
            )

            if probe is None:
                errors["base"] = "cannot_connect"
            else:
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

                data_updates: dict[str, Any] = {
                    **probe_data,
                    CONF_NAME: name,
                    CONF_ACCESS_CODE: int(
                        user_input.get(
                            CONF_ACCESS_CODE,
                            DEFAULT_WRITE_ACCESS_CODE,
                        )
                    ),
                    CONF_MODEL: model,
                    CONF_DETECTED_SENSORS: sorted(known_sensors),
                }

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
                _reconfigure_schema(self.hass),
                suggested_values,
            ),
            errors=errors,
        )
