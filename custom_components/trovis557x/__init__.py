"""The Samson Trovis 557x integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .connection import create_modbus_connection
from .const import CONF_DETECTED_SENSORS, CONF_MODEL, CONF_UNIT_ID
from .migration import async_migrate_entry as async_migrate_entry

if TYPE_CHECKING:
    from .coordinator import TrovisCoordinator

## this is relevant for developers only
try:
    from ._local_dev_overrides import (
        DEVELOPER_MODE,
        apply_local_function_overrides,
        apply_local_log_overrides,
    )
except ModuleNotFoundError:
    DEVELOPER_MODE = False
else:
    if DEVELOPER_MODE:
        apply_local_function_overrides()
        apply_local_log_overrides()


PLATFORMS = [
    Platform.BINARY_SENSOR,
    # Temporarily disabled; dedicated redesign pending - this is NOT a thermostat!
    # Platform.CLIMATE,
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
        unit_id = int(settings[CONF_UNIT_ID])
        model = int(settings[CONF_MODEL])
        detected_sensors = tuple(settings[CONF_DETECTED_SENSORS])
        connection = create_modbus_connection(settings)
        unit = connection.for_unit(unit_id)
    except (KeyError, TypeError, ValueError) as err:
        raise ConfigEntryNotReady(
            "The TROVIS config entry does not contain valid connection or probe data"
        ) from err

    entry.async_on_unload(connection.close)

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
