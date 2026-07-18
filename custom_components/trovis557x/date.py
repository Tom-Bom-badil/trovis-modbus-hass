"""Date entities for TROVIS controller values."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from homeassistant.components.date import DateEntity, DateEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import TrovisConfigEntry, TrovisCoordinator
from .entity import TrovisEntity


@dataclass(frozen=True, kw_only=True)
class TrovisDateDescription(DateEntityDescription):
    """Description of a native TROVIS date entity."""

    component: str
    field: str


_DATES: tuple[TrovisDateDescription, ...] = (
    TrovisDateDescription(
        key="controller_date",
        translation_key="controller_date",
        name="Controller date",
        component="clock",
        field="date",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TrovisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up native TROVIS date entities."""
    async_add_entities(
        TrovisDate(entry.runtime_data, description) for description in _DATES
    )


class TrovisDate(TrovisEntity, DateEntity):
    """A native date backed by one trovis-modbus datapoint."""

    entity_description: TrovisDateDescription

    def __init__(
        self,
        coordinator: TrovisCoordinator,
        description: TrovisDateDescription,
    ) -> None:
        super().__init__(
            coordinator,
            description.key,
            description.component,
            "date",
            translation_key=description.translation_key,
        )
        self.entity_description = description
        self._attr_entity_category = description.entity_category
        self._attr_entity_registry_enabled_default = (
            description.entity_registry_enabled_default
        )

    @property
    def native_value(self) -> date | None:
        """Return the native controller date."""
        return getattr(self._subsystem, self.entity_description.field)

    async def async_set_value(self, value: date) -> None:
        """Set the controller date through the shared library write path."""
        await self._async_write_datapoint(self.entity_description.field, value)
