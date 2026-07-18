"""Base entity for Trovis 557x.

Each heating circuit, the hot water tank, and the physical measurement inputs
are their own (sub-)devices, linked to the controller via ``via_device``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo, async_generate_entity_id
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify
from trovis_modbus import (
    TrovisValueValidationError,
    TrovisWriteAccessDisabledError,
    TrovisWriteAccessError,
    TrovisWriteNotImplementedError,
)

from .const import CONF_SLUG, DEFAULT_SLUG, DOMAIN
from .coordinator import TrovisCoordinator


def _sub_device(component: str) -> tuple[str, str, str] | None:
    """Return (sub-device id, fallback name, translation key), or None."""
    if component == "sensors":
        return "measurements", "Measurements", "measurements"

    if component.startswith("heating_circuit_"):
        number = component.rsplit("_", 1)[1]
        return (
            f"rk{number}",
            f"Rk{number} - Heating circuit {number}",
            f"rk{number}",
        )

    if component == "hot_water":
        return "rk4dhw", "Rk4 - Domestic hot water", "rk4dhw"

    return None


def _entry_slug(value: object) -> str:
    """Return a Home Assistant friendly entity prefix."""
    return slugify(str(value or "")) or DEFAULT_SLUG


class TrovisEntity(CoordinatorEntity[TrovisCoordinator]):
    """Common identity + device-info for every Trovis entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TrovisCoordinator,
        key: str,
        component: str,
        platform: str,
        translation_key: str | None = None,
        translation_placeholders: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._component = component

        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = translation_key or key
        self._attr_translation_placeholders = dict(translation_placeholders or {})

        entity_slug = _entry_slug(entry.data.get(CONF_SLUG, entry.title))
        object_id = f"{entity_slug}_{key}"

        self._attr_suggested_object_id = object_id
        self.entity_id = async_generate_entity_id(
            f"{platform}.{{}}",
            object_id,
            hass=coordinator.hass,
        )

        info = coordinator.device.info
        sub = _sub_device(component)
        if sub is None:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, entry.entry_id)},
                manufacturer=info.manufacturer,
                model=info.model,
                name=entry.title,
                sw_version=info.firmware_version,
                hw_version=info.hardware_version,
                serial_number=info.serial_number,
            )
        else:
            sub_id, sub_name, sub_translation_key = sub
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{entry.entry_id}_{sub_id}")},
                manufacturer=info.manufacturer,
                name=sub_name,
                translation_key=sub_translation_key,
                via_device=(DOMAIN, entry.entry_id),
            )

    @property
    def _subsystem(self) -> Any:
        """Return the shared library component used by this entity."""
        return getattr(self.coordinator.device, self._component)

    async def _async_write_datapoint(self, field: str, value: object) -> None:
        """Write one library datapoint and refresh the shared coordinator."""
        if not self.coordinator.device.writing_enabled:
            raise HomeAssistantError("Please enable writing for changes!")

        try:
            await self._subsystem.async_write_datapoint(
                field,
                value,
                access_code=self.coordinator.access_code,
            )
        except (
            TrovisWriteAccessDisabledError,
            TrovisWriteAccessError,
            TrovisValueValidationError,
        ) as err:
            raise HomeAssistantError(str(err)) from err
        except TrovisWriteNotImplementedError as err:
            raise HomeAssistantError(
                "Writing TROVIS data points is not implemented yet"
            ) from err

        await self.coordinator.async_request_refresh()
