"""Switch entities for writable TROVIS boolean values."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from trovis_modbus import TrovisWriteAccessError
from trovis_modbus.metadata import BooleanMetadata

from .coordinator import TrovisConfigEntry, TrovisCoordinator
from .entity import TrovisEntity
from .metadata import component_supports_datapoint, require_boolean_metadata

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TrovisSwitchDescription(SwitchEntityDescription):
    """Describe a Trovis switch entity.

    Boolean semantics and writeability come from trovis-modbus. This
    description only selects the field and stores Home Assistant presentation
    values.
    """

    component: str
    field: str
    translation_placeholders: dict[str, str] | None = None


def _switch(
    component: str,
    field: str,
    name: str,
    *,
    key: str | None = None,
    translation_key: str | None = None,
    translation_placeholders: dict[str, str] | None = None,
    enabled: bool = True,
) -> TrovisSwitchDescription:
    """Return a metadata-driven switch description."""
    return TrovisSwitchDescription(
        key=key or field,
        translation_key=translation_key,
        translation_placeholders=translation_placeholders,
        name=name,
        component=component,
        field=field,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=enabled,
    )


_CONTROLLER: tuple[TrovisSwitchDescription, ...] = (
    _switch(
        "controller",
        "delayed_outdoor_temperature_adaptation_falling",
        "Delayed outdoor-temperature adaptation (falling)",
    ),
    _switch(
        "controller",
        "delayed_outdoor_temperature_adaptation_rising",
        "Delayed outdoor-temperature adaptation (rising)",
    ),
    _switch(
        "controller",
        "automatic_summer_standard_time_switchover",
        "Automatic summer/standard time switchover",
        key="automatic_summer_standard_time_switchover",
        translation_key="automatic_summer_standard_time_switchover",
    ),
    _switch(
        "controller",
        "manual_levels_locked",
        "Manual-operation levels locked",
    ),
    _switch(
        "controller",
        "rotary_switch_locked",
        "Rotary switches locked",
    ),
    _switch(
        "controller",
        "glt_timeout_active",
        "Supervisory-system timeout",
        enabled=False,
    ),
)


def _hk_switch_descriptions(index: int) -> tuple[TrovisSwitchDescription, ...]:
    """Return switch descriptions for one heating circuit."""
    component = f"hk{index}"
    prefix = f"hk{index}"
    placeholders = {"component": f"Hk{index}"}

    return (
        _switch(
            component,
            "optimization",
            f"Hk{index} optimization",
            key=f"{prefix}_optimization",
            translation_key="optimization",
            translation_placeholders=placeholders,
        ),
        _switch(
            component,
            "adaptation",
            f"Hk{index} adaptation",
            key=f"{prefix}_adaptation",
            translation_key="adaptation",
            translation_placeholders=placeholders,
        ),
        _switch(
            component,
            "room_control_unit",
            f"Hk{index} room control unit",
            key=f"{prefix}_room_control_unit",
            translation_key="room_control_unit",
            translation_placeholders=placeholders,
        ),
        _switch(
            component,
            "pump_running",
            f"Hk{index} pump control",
            key=f"{prefix}_pump_control",
            translation_key="pump_control",
            translation_placeholders=placeholders,
        ),
    )


_WW: tuple[TrovisSwitchDescription, ...] = (
    _switch(
        "ww",
        "storage_tank_charging_pump_running",
        "WW storage-tank-charging-pump control",
        key="ww_storage_tank_charging_pump_control",
        translation_key="storage_tank_charging_pump_control",
        translation_placeholders={"component": "WW"},
    ),
    _switch(
        "ww",
        "circulation_pump_running",
        "WW circulation-pump control",
        key="ww_circulation_pump_control",
        translation_key="circulation_pump_control",
        translation_placeholders={"component": "WW"},
    ),
    _switch(
        "ww",
        "intermediate_heating_operation",
        "WW intermediate heating operation",
        key="ww_intermediate_heating_operation",
        translation_key="intermediate_heating_operation",
        translation_placeholders={"component": "WW"},
    ),
    _switch(
        "ww",
        "forced_charging",
        "WW forced charging",
        key="ww_forced_charging",
        translation_key="forced_charging",
        translation_placeholders={"component": "WW"},
    ),
    _switch(
        "ww",
        "forced_charging_uses_storage_tank_sensor_2",
        "WW forced charging using storage tank sensor 2",
        key="ww_forced_charging_uses_storage_tank_sensor_2",
        translation_key="forced_charging_uses_storage_tank_sensor_2",
        translation_placeholders={"component": "WW"},
    ),
    _switch(
        "ww",
        "storage_tank_charging_enabled",
        "WW storage tank charging enabled",
        key="ww_storage_tank_charging_enabled",
        translation_key="storage_tank_charging_enabled",
        translation_placeholders={"component": "WW"},
    ),
    _switch(
        "ww",
        "intermediate_heating_function_enabled",
        "WW intermediate heating function",
        key="ww_intermediate_heating_function_enabled",
        translation_key="intermediate_heating_function_enabled",
        translation_placeholders={"component": "WW"},
        enabled=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TrovisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Trovis switch entities."""
    coordinator = entry.runtime_data

    entities: list[SwitchEntity] = [TrovisWriteAccessSwitch(coordinator)]
    descriptions = list(_CONTROLLER)

    for index in coordinator.device.heating_circuit_indices:
        descriptions.extend(_hk_switch_descriptions(index))

    descriptions.extend(_WW)
    entities.extend(
        TrovisSwitch(coordinator, description)
        for description in descriptions
        if component_supports_datapoint(
            getattr(coordinator.device, description.component),
            description.field,
        )
    )

    async_add_entities(entities)


class TrovisWriteAccessSwitch(TrovisEntity, SwitchEntity):
    """Root switch that enables or disables TROVIS write access."""

    _attr_icon = "mdi:pencil-lock"

    def __init__(self, coordinator: TrovisCoordinator) -> None:
        super().__init__(
            coordinator,
            "write_access",
            "controller",
            "switch",
            translation_key="write_access",
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether TROVIS writing is enabled."""
        return self.coordinator.device.writing_enabled

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable TROVIS writing."""
        try:
            await self.coordinator.device.async_enable_writing(
                access_code=self.coordinator.access_code,
            )
        except TrovisWriteAccessError as err:
            raise HomeAssistantError(str(err)) from err

        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable TROVIS writing."""
        try:
            await self.coordinator.device.async_disable_writing()
        except TrovisWriteAccessError as err:
            _LOGGER.debug(
                "Controller rejected resetting TROVIS write access; "
                "disabling the HA write gate only",
                exc_info=err,
            )

        await self.coordinator.async_request_refresh()


class TrovisSwitch(TrovisEntity, SwitchEntity):
    """Trovis switch entity."""

    entity_description: TrovisSwitchDescription

    def __init__(
        self,
        coordinator: TrovisCoordinator,
        description: TrovisSwitchDescription,
    ) -> None:
        super().__init__(
            coordinator,
            description.key,
            description.component,
            "switch",
            translation_key=description.translation_key,
            translation_placeholders=description.translation_placeholders,
        )
        self.entity_description = description
        self._boolean_metadata: BooleanMetadata = require_boolean_metadata(
            self._subsystem,
            description.field,
        )
        self._attr_entity_category = description.entity_category
        self._attr_entity_registry_enabled_default = (
            description.entity_registry_enabled_default
        )

    def _to_ha_bool(self, value: bool) -> bool:
        """Convert the controller value to Home Assistant switch semantics."""
        result = bool(value)
        if self._boolean_metadata.inverted:
            return not result
        return result

    def _from_ha_bool(self, value: bool) -> bool:
        """Convert Home Assistant switch semantics to controller value."""
        if self._boolean_metadata.inverted:
            return not value
        return value

    @property
    def is_on(self) -> bool | None:
        """Return whether the switch is on."""
        value = getattr(self._subsystem, self.entity_description.field)
        if value is None:
            return None

        return self._to_ha_bool(bool(value))

    async def async_turn_on(self, **kwargs: object) -> None:
        """Turn the switch on."""
        await self._async_set_switch(self._from_ha_bool(True))

    async def async_turn_off(self, **kwargs: object) -> None:
        """Turn the switch off."""
        await self._async_set_switch(self._from_ha_bool(False))

    async def _async_set_switch(self, value: bool) -> None:
        """Set the switch state through the shared library write path."""
        await self._async_write_datapoint(self.entity_description.field, value)
