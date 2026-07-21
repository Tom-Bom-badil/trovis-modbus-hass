"""Number entities for writable TROVIS values."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import TrovisConfigEntry, TrovisCoordinator
from .entity import TrovisEntity
from .metadata import (
    component_supports_datapoint,
    ha_unit_from_number,
    number_device_class_from_number,
    require_number_metadata,
)


@dataclass(frozen=True, kw_only=True)
class TrovisNumberDescription(NumberEntityDescription):
    """Describe a writable number entity.

    Min/max/step/unit/writeability come from trovis-modbus. This description
    only selects the Lib field and stores Home Assistant presentation choices.
    """

    component: str
    field: str
    translation_placeholders: dict[str, str] | None = None


def _number(
    component: str,
    field: str,
    name: str,
    *,
    key: str | None = None,
    translation_key: str | None = None,
    translation_placeholders: dict[str, str] | None = None,
    enabled: bool = True,
) -> TrovisNumberDescription:
    """Return a metadata-driven number description."""
    return TrovisNumberDescription(
        key=key or field,
        translation_key=translation_key,
        translation_placeholders=translation_placeholders,
        name=name,
        component=component,
        field=field,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=enabled,
    )


_CONTROLLER: tuple[TrovisNumberDescription, ...] = (
    _number("clock", "year", "Controller year"),
    _number("controller", "summer_days_on", "Summer mode activation days"),
    _number("controller", "summer_days_off", "Summer mode deactivation days"),
    _number(
        "controller",
        "summer_outdoor_temperature_limit",
        "Summer outdoor-temperature limit",
    ),
    _number("controller", "outdoor_temperature_delay", "Outdoor-temperature delay"),
    _number("controller", "frost_protection_limit", "Frost-protection limit"),
    _number(
        "controller",
        "temperature_monitoring_deviation",
        "Temperature-monitoring deviation",
        enabled=False,
    ),
    _number(
        "controller",
        "temperature_monitoring_window",
        "Temperature-monitoring window",
        enabled=False,
    ),
    _number(
        "controller",
        "outdoor_temperature_input_range_start",
        "Outdoor-temperature input range start",
        enabled=False,
    ),
    _number(
        "controller",
        "outdoor_temperature_input_range_end",
        "Outdoor-temperature input range end",
        enabled=False,
    ),
)


def _hk_number_descriptions(index: int) -> tuple[TrovisNumberDescription, ...]:
    """Return number descriptions for one heating circuit."""
    component = f"hk{index}"
    prefix = f"hk{index}"
    placeholders = {"component": f"Hk{index}"}

    def description(field: str, name: str) -> TrovisNumberDescription:
        return _number(
            component,
            field,
            f"Hk{index} {name}",
            key=f"{prefix}_{field}",
            translation_key=field,
            translation_placeholders=placeholders,
        )

    return (
        description("room_setpoint_day", "room setpoint day"),
        description("room_setpoint_night", "room setpoint night"),
        description("gradient", "gradient"),
        description("level", "level"),
        description("minimum_flow_temperature", "minimum flow setpoint"),
        description("maximum_flow_temperature", "maximum flow setpoint"),
        description("maximum_return_flow_temperature", "maximum return temperature"),
        description("fixed_setpoint_day", "fixed setpoint day"),
        description("fixed_setpoint_night", "fixed setpoint night"),
    )


_WW_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("setpoint_day", "ww_setpoint", "ww_setpoint"),
    ("setpoint_night", "ww_setpoint_night", "ww_setpoint_night"),
    ("setpoint_min", "ww_setpoint_min", "ww_setpoint_min"),
    ("setpoint_max", "ww_setpoint_max", "ww_setpoint_max"),
    ("hysteresis", "ww_hysteresis", "hysteresis"),
    (
        "charging_temperature_boost",
        "ww_charging_temperature_boost",
        "charging_temperature_boost",
    ),
    (
        "storage_tank_charging_pump_lag_factor",
        "ww_storage_tank_charging_pump_lag_factor",
        "storage_tank_charging_pump_lag_factor",
    ),
    (
        "maximum_charging_temperature",
        "ww_maximum_charging_temperature",
        "maximum_charging_temperature",
    ),
    (
        "maximum_return_flow_temperature",
        "ww_maximum_return_flow_temperature",
        "ww_maximum_return_flow_temperature",
    ),
    (
        "disinfection_temperature",
        "ww_disinfection_temperature",
        "disinfection_temperature",
    ),
    (
        "disinfection_hold_time",
        "ww_disinfection_hold_time",
        "disinfection_hold_time",
    ),
    ("special_setpoint", "ww_special_setpoint", "special_setpoint"),
)

_WW: tuple[TrovisNumberDescription, ...] = tuple(
    _number(
        "ww",
        field,
        f"WW {field.replace('_', ' ')}",
        key=key,
        translation_key=translation_key,
        translation_placeholders={"component": "WW"},
    )
    for field, key, translation_key in _WW_FIELDS
)


def _description_supported(
    coordinator: TrovisCoordinator,
    description: TrovisNumberDescription,
) -> bool:
    """Return whether a number field exists on this device profile."""
    component = getattr(coordinator.device, description.component)
    return component_supports_datapoint(component, description.field)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TrovisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Trovis number entities."""
    coordinator = entry.runtime_data

    descriptions = list(_CONTROLLER)
    for index in coordinator.device.heating_circuit_indices:
        descriptions.extend(_hk_number_descriptions(index))
    descriptions.extend(_WW)

    async_add_entities(
        TrovisNumber(coordinator, description)
        for description in descriptions
        if _description_supported(coordinator, description)
    )


class TrovisNumber(TrovisEntity, NumberEntity):
    """Trovis number entity."""

    entity_description: TrovisNumberDescription

    def __init__(
        self,
        coordinator: TrovisCoordinator,
        description: TrovisNumberDescription,
    ) -> None:
        super().__init__(
            coordinator,
            description.key,
            description.component,
            "number",
            translation_key=description.translation_key,
            translation_placeholders=description.translation_placeholders,
        )
        self.entity_description = description

        number = require_number_metadata(self._subsystem, description.field)

        self._attr_native_min_value = number.min_value
        self._attr_native_max_value = number.max_value
        self._attr_native_step = number.step
        self._attr_native_unit_of_measurement = (
            description.native_unit_of_measurement or ha_unit_from_number(number)
        )
        self._attr_device_class = (
            description.device_class or number_device_class_from_number(number)
        )
        self._attr_mode = description.mode
        self._attr_entity_category = description.entity_category
        self._attr_entity_registry_enabled_default = (
            description.entity_registry_enabled_default
        )

    @property
    def native_value(self) -> float | int | None:
        """Return the current value."""
        return getattr(self._subsystem, self.entity_description.field)

    async def async_set_native_value(self, value: float) -> None:
        """Set a new value through the shared library write path."""
        await self._async_write_datapoint(self.entity_description.field, value)
