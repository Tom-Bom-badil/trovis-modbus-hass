"""DataUpdateCoordinator that polls the Trovis controller."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from modbus_connection import ModbusError
from trovis_modbus import DEFAULT_WRITE_ACCESS_CODE, Trovis557x

from .const import CONF_ACCESS_CODE, DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

type TrovisConfigEntry = ConfigEntry[TrovisCoordinator]


class TrovisCoordinator(DataUpdateCoordinator[Trovis557x]):
    """Poll a TROVIS controller through its Modbus unit."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: TrovisConfigEntry,
        device: Trovis557x,
    ) -> None:
        """Initialize the TROVIS coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=SCAN_INTERVAL,
        )

        self.device = device

    @property
    def access_code(self) -> int:
        """Return the configured TROVIS write access code."""
        return int(
            self.config_entry.data.get(
                CONF_ACCESS_CODE,
                DEFAULT_WRITE_ACCESS_CODE,
            )
        )

    async def _async_update_data(self) -> Trovis557x:
        """Refresh all TROVIS data."""
        try:
            await self.device.async_update()
        except ModbusError as err:
            raise UpdateFailed(f"Error communicating with Trovis: {err}") from err

        return self.device
