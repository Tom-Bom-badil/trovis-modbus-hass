"""The Samson Trovis 557x integration using a shared Modbus connection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.modbus_connection import async_get_unit
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from ._local_dev import apply_local_trovis_modbus_override
from .const import (
    CONF_CONNECTION_ENTRY_ID,
    CONF_DETECTED_SENSORS,
    CONF_MODEL,
    CONF_UNIT_ID,
)

if TYPE_CHECKING:
    from .coordinator import TrovisCoordinator

# Apply the optional local library override once, before Home Assistant imports
# config_flow.py, coordinator.py or any entity platform.
apply_local_trovis_modbus_override()


PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.DATE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
    Platform.WATER_HEATER,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[TrovisCoordinator],
) -> bool:
    """Set up Trovis 557x from a config entry."""
    from trovis_modbus import Trovis557x

    from .coordinator import TrovisCoordinator

    settings = {
        **entry.data,
        **entry.options,
    }

    try:
        connection_entry_id = str(settings[CONF_CONNECTION_ENTRY_ID])
        unit_id = int(settings[CONF_UNIT_ID])
        model = int(settings[CONF_MODEL])
        detected_sensors = tuple(settings[CONF_DETECTED_SENSORS])
    except (KeyError, TypeError, ValueError) as err:
        raise ConfigEntryNotReady(
            "The TROVIS config entry does not contain valid probe data"
        ) from err

    unit = async_get_unit(
        hass,
        connection_entry_id,
        unit_id,
    )

    try:
        device = Trovis557x(
            unit,
            model=model,
            detected_sensors=detected_sensors,
        )
    except ValueError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = TrovisCoordinator(
        hass,
        entry,
        device,
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[TrovisCoordinator],
) -> bool:
    """Unload a Trovis 557x config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )
