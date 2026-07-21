"""Select entities for enum-backed TROVIS values."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from trovis_modbus.metadata import EnumMetadata

from .coordinator import TrovisConfigEntry, TrovisCoordinator
from .entity import TrovisEntity
from .metadata import component_supports_datapoint, require_enum_metadata


@dataclass(frozen=True, kw_only=True)
class TrovisSelectDescription(SelectEntityDescription):
    """Describe a Trovis select entity.

    Options and enum values come from trovis-modbus. This description only
    selects the field and stores Home Assistant presentation values.
    """

    component: str
    field: str
    translation_placeholders: dict[str, str] | None = None


def _operation_mode(
    component: str,
    key: str,
    placeholder: str,
) -> TrovisSelectDescription:
    """Return an operation-mode select description."""
    return TrovisSelectDescription(
        key=key,
        translation_key="operation_mode",
        name=f"{placeholder} operation mode",
        component=component,
        field="mode",
        entity_category=EntityCategory.CONFIG,
        translation_placeholders={"component": placeholder},
    )


_SELECTS: tuple[TrovisSelectDescription, ...] = (
    _operation_mode("hk1", "hk1_operation_mode", "Hk1"),
    _operation_mode("hk2", "hk2_operation_mode", "Hk2"),
    _operation_mode("hk3", "hk3_operation_mode", "Hk3"),
    _operation_mode("ww", "ww_operation_mode", "WW"),
    TrovisSelectDescription(
        key="ww_disinfection_weekday",
        translation_key="disinfection_weekday",
        name="WW disinfection weekday",
        component="ww",
        field="disinfection_weekday",
        entity_category=EntityCategory.CONFIG,
        translation_placeholders={"component": "WW"},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TrovisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Trovis select entities."""
    coordinator = entry.runtime_data

    active_components = {
        f"hk{index}" for index in coordinator.device.heating_circuit_indices
    }
    active_components.add("ww")

    async_add_entities(
        TrovisSelect(coordinator, description)
        for description in _SELECTS
        if description.component in active_components
        and component_supports_datapoint(
            getattr(coordinator.device, description.component),
            description.field,
        )
    )


class TrovisSelect(TrovisEntity, SelectEntity):
    """Trovis select entity."""

    entity_description: TrovisSelectDescription

    def __init__(
        self,
        coordinator: TrovisCoordinator,
        description: TrovisSelectDescription,
    ) -> None:
        super().__init__(
            coordinator,
            description.key,
            description.component,
            "select",
            translation_key=description.translation_key,
            translation_placeholders=description.translation_placeholders,
        )
        self.entity_description = description

        enum_metadata = require_enum_metadata(self._subsystem, description.field)
        self._enum_metadata: EnumMetadata = enum_metadata

        self._option_by_key = {option.key: option for option in enum_metadata.options}
        self._key_by_value = {
            int(option.value): option.key for option in enum_metadata.options
        }

        self._attr_options = list(self._option_by_key)
        self._attr_entity_category = description.entity_category
        self._attr_entity_registry_enabled_default = (
            description.entity_registry_enabled_default
        )

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        value = getattr(self._subsystem, self.entity_description.field)
        if value is None:
            return None

        try:
            return self._key_by_value.get(int(value))
        except (TypeError, ValueError):
            return None

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        try:
            selected = self._option_by_key[option]
        except KeyError as err:
            raise HomeAssistantError(f"Unsupported TROVIS option: {option}") from err

        await self._async_write_datapoint(
            self.entity_description.field,
            self._enum_metadata.enum_type(selected.value),
        )
