"""Base entity for Trovis 557x.

Each heating circuit, the hot water tank, and the physical measurement inputs
are their own (sub-)devices, linked to the controller via ``via_device``.
Everything else belongs to the controller.
"""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo, async_generate_entity_id
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import CONF_SLUG, DEFAULT_SLUG, DOMAIN
from .coordinator import TrovisCoordinator


def _sub_device(component: str) -> tuple[str, str] | None:
    """(sub-device id, name) for a component, or None for the controller."""
    if component == "sensors":
        return "measurements", "Measurements"
    if component.startswith("heating_circuit_"):
        number = component.rsplit("_", 1)[1]
        return f"circuit_{number}", f"Heating circuit {number}"
    if component == "hot_water":
        return "hot_water", "Hot water"
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
    ) -> None:
        super().__init__(coordinator)
        self._component = component

        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
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
                name=info.model,
                sw_version=info.firmware_version,
                hw_version=info.hardware_version,
                serial_number=info.serial_number,
            )
        else:
            sub_id, sub_name = sub
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{entry.entry_id}_{sub_id}")},
                manufacturer=info.manufacturer,
                name=sub_name,
                via_device=(DOMAIN, entry.entry_id),
            )

    @property
    def _subsystem(self) -> object:
        """The library sub-system object this entity reads from."""
        return getattr(self.coordinator.device, self._component)