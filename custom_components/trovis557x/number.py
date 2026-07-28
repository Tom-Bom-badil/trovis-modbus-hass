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
from .entity import TrovisEntity, rk1_to_rk3_indices
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


def _rk_number_descriptions(index: int) -> tuple[TrovisNumberDescription, ...]:
    """Return number descriptions for one heating circuit."""
    component = f"rk{index}"
    prefix = f"rk{index}"
    placeholders = {"component": f"Rk{index}"}

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
        description("gradient", "gradient"),
        description("level", "level"),
        description("minimum_flow_temperature", "minimum flow setpoint"),
        description("maximum_flow_temperature", "maximum flow setpoint"),
        description("maximum_return_flow_temperature", "maximum return temperature"),
        description("fixed_setpoint_day", "fixed setpoint day"),
        description("fixed_setpoint_night", "fixed setpoint night"),
    )


_RK4_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("setpoint_day", "rk4_setpoint", "rk4_setpoint"),
    ("setpoint_night", "rk4_setpoint_night", "rk4_setpoint_night"),
    ("setpoint_min", "rk4_setpoint_min", "rk4_setpoint_min"),
    ("setpoint_max", "rk4_setpoint_max", "rk4_setpoint_max"),
    ("hysteresis", "rk4_hysteresis", "hysteresis"),
    (
        "charging_temperature_boost",
        "rk4_charging_temperature_boost",
        "charging_temperature_boost",
    ),
    (
        "storage_tank_charging_pump_lag_factor",
        "rk4_storage_tank_charging_pump_lag_factor",
        "storage_tank_charging_pump_lag_factor",
    ),
    (
        "maximum_charging_temperature",
        "rk4_maximum_charging_temperature",
        "maximum_charging_temperature",
    ),
    (
        "maximum_return_flow_temperature",
        "rk4_maximum_return_flow_temperature",
        "rk4_maximum_return_flow_temperature",
    ),
    (
        "disinfection_temperature",
        "rk4_disinfection_temperature",
        "disinfection_temperature",
    ),
    (
        "disinfection_hold_time",
        "rk4_disinfection_hold_time",
        "disinfection_hold_time",
    ),
    ("special_setpoint", "rk4_special_setpoint", "special_setpoint"),
)

_RK4: tuple[TrovisNumberDescription, ...] = tuple(
    _number(
        "rk4",
        field,
        f"Rk4 {field.replace('_', ' ')}",
        key=key,
        translation_key=translation_key,
        translation_placeholders={"component": "Rk4"},
    )
    for field, key, translation_key in _RK4_FIELDS
)


_BUFFER_TANK: tuple[TrovisNumberDescription, ...] = (
    _number(
        "buffer_tank",
        "minimum_charging_setpoint",
        "Rk1 minimum buffer charging setpoint",
        key="rk1_buffer_tank_minimum_charging_setpoint",
        translation_key="buffer_tank_minimum_charging_setpoint",
    ),
    _number(
        "buffer_tank",
        "charging_end_temperature",
        "Rk1 buffer charging end temperature",
        key="rk1_buffer_tank_charging_end_temperature",
        translation_key="buffer_tank_charging_end_temperature",
    ),
    _number(
        "buffer_tank",
        "charging_temperature_boost",
        "Rk1 buffer charging temperature boost",
        key="rk1_buffer_tank_charging_temperature_boost",
        translation_key="buffer_tank_charging_temperature_boost",
    ),
    _number(
        "buffer_tank",
        "charging_pump_lag_factor",
        "Rk1 buffer charging pump lag factor",
        key="rk1_buffer_tank_charging_pump_lag_factor",
        translation_key="buffer_tank_charging_pump_lag_factor",
    ),
)


_SOLAR: tuple[TrovisNumberDescription, ...] = (
    _number(
        "solar",
        "pump_on_temperature_difference",
        "Solar pump-on temperature difference",
        key="solar_pump_on_temperature_difference",
        translation_key="solar_pump_on_temperature_difference",
    ),
    _number(
        "solar",
        "pump_off_temperature_difference",
        "Solar pump-off temperature difference",
        key="solar_pump_off_temperature_difference",
        translation_key="solar_pump_off_temperature_difference",
    ),
    _number(
        "solar",
        "maximum_storage_temperature",
        "Solar maximum storage temperature",
        key="solar_maximum_storage_temperature",
        translation_key="solar_maximum_storage_temperature",
    ),
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
    for index in rk1_to_rk3_indices(coordinator):
        descriptions.extend(_rk_number_descriptions(index))
    if coordinator.device.has_rk4:
        descriptions.extend(_RK4)
    if coordinator.device.has_buffer_tank_charging_parameters:
        descriptions.extend(_BUFFER_TANK)
    if coordinator.device.has_solar:
        descriptions.extend(_SOLAR)

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
