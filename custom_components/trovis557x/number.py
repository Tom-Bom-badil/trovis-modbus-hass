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
    _number("controller", "summer_outside_limit", "Summer outside-temperature limit"),
    _number("controller", "outside_delay", "Outside-temperature delay"),
    _number("controller", "frost_limit", "Frost-protection limit"),
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
        "outside_input_range_start",
        "Outside-temperature input range start",
        enabled=False,
    ),
    _number(
        "controller",
        "outside_input_range_end",
        "Outside-temperature input range end",
        enabled=False,
    ),
)


def _rk_number_descriptions(index: int) -> tuple[TrovisNumberDescription, ...]:
    """Return number descriptions for one heating circuit."""
    component = f"heating_circuit_{index}"
    prefix = f"rk{index}"
    placeholders = {"rk": f"Rk{index}"}

    def description(field: str, name: str) -> TrovisNumberDescription:
        return _number(
            component,
            field,
            f"Rk{index} {name}",
            key=f"{prefix}_{field}",
            translation_key=field,
            translation_placeholders=placeholders,
        )

    return (
        description("room_setpoint_day", "room setpoint day"),
        description("room_setpoint_night", "room setpoint night"),
        description("slope", "slope"),
        description("level", "level"),
        description("flow_min", "minimum flow setpoint"),
        description("flow_max", "maximum flow setpoint"),
        description("return_max", "maximum return temperature"),
        description("fixed_setpoint_day", "fixed setpoint day"),
        description("fixed_setpoint_night", "fixed setpoint night"),
    )


_HOT_WATER_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("setpoint_day", "rk4dhw_setpoint", "dhw_setpoint"),
    ("hold_value", "rk4dhw_hold_value", "dhw_hold_value"),
    ("setpoint_min", "rk4dhw_setpoint_min", "dhw_setpoint_min"),
    ("setpoint_max", "rk4dhw_setpoint_max", "dhw_setpoint_max"),
    ("hysteresis", "rk4dhw_hysteresis", "hysteresis"),
    ("charge_overshoot", "rk4dhw_charge_overshoot", "charge_overshoot"),
    (
        "charge_pump_overrun_factor",
        "rk4dhw_charge_pump_overrun_factor",
        "charge_pump_overrun_factor",
    ),
    ("max_charge_temp", "rk4dhw_max_charge_temp", "max_charge_temp"),
    ("return_max", "rk4dhw_return_max", "dhw_return_max"),
    (
        "disinfection_temp",
        "rk4dhw_disinfection_temp",
        "disinfection_temp",
    ),
    (
        "disinfection_hold",
        "rk4dhw_disinfection_hold",
        "disinfection_hold",
    ),
    ("special_setpoint", "rk4dhw_special_setpoint", "special_setpoint"),
)

_HOT_WATER: tuple[TrovisNumberDescription, ...] = tuple(
    _number(
        "hot_water",
        field,
        f"Rk4 {field.replace('_', ' ')}",
        key=key,
        translation_key=translation_key,
        translation_placeholders={"rk": "Rk4"},
    )
    for field, key, translation_key in _HOT_WATER_FIELDS
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
        descriptions.extend(_rk_number_descriptions(index))
    descriptions.extend(_HOT_WATER)

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
