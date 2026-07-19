"""Primary read-only entities and diagnostic readings for TROVIS datapoints.

Normal Home Assistant entities are the complete primary representation of
library values. Climate and water-heater entities are convenience views over
the same shared components and never own exclusive datapoints.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Literal

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from trovis_modbus import MonthDay
from trovis_modbus.metadata import EnumMetadata

from .coordinator import TrovisConfigEntry, TrovisCoordinator
from .entity import TrovisEntity
from .metadata import (
    component_supports_datapoint,
    ha_unit_from_number,
    require_enum_metadata,
    require_number_metadata,
    sensor_device_class_from_number,
)

SensorValueKind = Literal["plain", "number", "enum", "month_day"]


@dataclass(frozen=True, kw_only=True)
class TrovisSensorDescription(SensorEntityDescription):
    """Describe a sensor reading one field of one component."""

    component: str
    field: str
    value_kind: SensorValueKind = "plain"


def _number_sensor(
    component: str,
    field: str,
    name: str,
    *,
    key: str | None = None,
    translation_key: str | None = None,
    enabled: bool = True,
    entity_category: EntityCategory | None = EntityCategory.DIAGNOSTIC,
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT,
    device_class: SensorDeviceClass | None = None,
    translation_placeholders: dict[str, str] | None = None,
) -> TrovisSensorDescription:
    """Return a numeric sensor description backed by Lib metadata."""
    return TrovisSensorDescription(
        key=key or field,
        translation_key=translation_key,
        translation_placeholders=translation_placeholders,
        name=name,
        component=component,
        field=field,
        value_kind="number",
        device_class=device_class,
        state_class=state_class,
        entity_category=entity_category,
        entity_registry_enabled_default=enabled,
    )


def _enum_sensor(
    component: str,
    field: str,
    name: str,
    *,
    key: str | None = None,
    translation_key: str | None = None,
    enabled: bool = True,
    translation_placeholders: dict[str, str] | None = None,
) -> TrovisSensorDescription:
    """Return an enum sensor description backed by Lib metadata."""
    return TrovisSensorDescription(
        key=key or field,
        translation_key=translation_key,
        translation_placeholders=translation_placeholders,
        name=name,
        component=component,
        field=field,
        value_kind="enum",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=enabled,
    )


def _month_day_sensor(
    field: str,
    name: str,
    *,
    key: str | None = None,
    translation_key: str | None = None,
) -> TrovisSensorDescription:
    """Return a read-only representation of a recurring month/day value."""
    return TrovisSensorDescription(
        key=key or field,
        translation_key=translation_key,
        name=name,
        component="controller",
        field=field,
        value_kind="month_day",
        entity_category=EntityCategory.DIAGNOSTIC,
    )


_GLOBAL: tuple[TrovisSensorDescription, ...] = (
    TrovisSensorDescription(
        key="system",
        translation_key="system",
        name="Hydraulic system",
        component="info",
        field="system",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    _number_sensor(
        "sensors", "af1", "AF1 outside sensor 1", key="outside_temperature_1"
    ),
    _number_sensor(
        "sensors", "af2", "AF2 outside sensor 2", key="outside_temperature_2"
    ),
    _number_sensor("sensors", "vf1", "VF1 flow sensor 1", key="flow_temperature_1"),
    _number_sensor("sensors", "vf2", "VF2 flow sensor 2", key="flow_temperature_2"),
    _number_sensor("sensors", "vf3", "VF3 flow sensor 3", key="flow_temperature_3"),
    _number_sensor("sensors", "vf4", "VF4 flow sensor 4", key="flow_temperature_4"),
    _number_sensor(
        "sensors", "ruef1", "RüF1 return sensor 1", key="return_temperature_1"
    ),
    _number_sensor(
        "sensors", "ruef2", "RüF2 return sensor 2", key="return_temperature_2"
    ),
    _number_sensor(
        "sensors", "ruef3", "RüF3 return sensor 3", key="return_temperature_3"
    ),
    _number_sensor("sensors", "rf1", "RF1 room sensor 1", key="room_temperature_1"),
    _number_sensor("sensors", "rf2", "RF2 room sensor 2", key="room_temperature_2"),
    _number_sensor("sensors", "rf3", "RF3 room sensor 3", key="room_temperature_3"),
    _number_sensor(
        "sensors", "sf1", "SF1 hot water sensor 1", key="dhw_storage_temperature"
    ),
    _number_sensor(
        "sensors",
        "sf2",
        "SF2 hot water sensor 2",
        key="dhw_storage_temperature_lower",
    ),
    _number_sensor("sensors", "fg1", "FG1 remote control 1", key="remote_adjustment_1"),
    _number_sensor("sensors", "fg2", "FG2 remote control 2", key="remote_adjustment_2"),
    _number_sensor(
        "sensors",
        "sf3_fg3",
        "SF3/FG3 hot water sensor / remote control 3",
        key="storage_remote_temperature",
    ),
    _number_sensor(
        "sensors",
        "ae3_fg3",
        "AE3/FG3 analog input / remote control 3",
        key="analog_remote_input_3",
    ),
    _number_sensor(
        "sensors",
        "pulse_rate",
        "Pulse rate",
        key="pulse_rate",
    ),
    _number_sensor(
        "sensors",
        "analog_input_voltage",
        "Analog input voltage",
        key="analog_input_voltage",
    ),
    _number_sensor(
        "sensors",
        "summer_outside_average",
        "Summer outside-temperature average",
        key="summer_outside_average",
    ),
    _number_sensor(
        "controller",
        "max_flow_setpoint",
        "Max flow setpoint",
        enabled=False,
        state_class=None,
    ),
    _enum_sensor("controller", "switch_top", "Switch top"),
    _enum_sensor("controller", "switch_middle", "Switch middle"),
    _enum_sensor("controller", "switch_bottom", "Switch bottom"),
    _number_sensor(
        "controller",
        "error_status",
        "Error status",
        state_class=None,
    ),
    _number_sensor(
        "controller",
        "special_functions",
        "Special functions",
        enabled=False,
        state_class=None,
    ),
    _number_sensor(
        "controller",
        "station_address",
        "Station address",
        state_class=None,
    ),
    _number_sensor(
        "controller",
        "error_count",
        "Error count",
        state_class=None,
    ),
    _month_day_sensor("summer_start", "Summer period start"),
    _month_day_sensor("summer_end", "Summer period end"),
)


def _rk_sensor_descriptions(index: int) -> tuple[TrovisSensorDescription, ...]:
    """Return read-only sensor descriptions for one heating circuit."""
    component = f"heating_circuit_{index}"
    prefix = f"rk{index}"
    placeholders = {"rk": f"Rk{index}"}

    return (
        _number_sensor(
            component,
            "valve_setpoint",
            f"Rk{index} valve setpoint",
            key=f"{prefix}_valve_setpoint",
            translation_key="valve_setpoint",
            translation_placeholders=placeholders,
        ),
        _number_sensor(
            component,
            "room_setpoint_active",
            f"Rk{index} active room setpoint",
            key=f"{prefix}_room_setpoint_active",
            translation_key="room_setpoint_active",
            entity_category=None,
            state_class=None,
            translation_placeholders=placeholders,
        ),
        _number_sensor(
            component,
            "flow_setpoint",
            f"Rk{index} flow setpoint",
            key=f"{prefix}_flow_setpoint",
            translation_key="flow_setpoint",
            state_class=None,
            translation_placeholders=placeholders,
        ),
        _number_sensor(
            component,
            "return_slope",
            f"Rk{index} return slope",
            key=f"{prefix}_return_slope",
            translation_key="return_slope",
            state_class=None,
            translation_placeholders=placeholders,
        ),
        _number_sensor(
            component,
            "return_level",
            f"Rk{index} return level",
            key=f"{prefix}_return_level",
            translation_key="return_level",
            state_class=None,
            translation_placeholders=placeholders,
        ),
        _number_sensor(
            component,
            "return_base_point",
            f"Rk{index} return base point",
            key=f"{prefix}_return_base_point",
            translation_key="return_base_point",
            state_class=None,
            translation_placeholders=placeholders,
        ),
        _number_sensor(
            component,
            "return_setpoint",
            f"Rk{index} return setpoint",
            key=f"{prefix}_return_setpoint",
            translation_key="return_setpoint",
            state_class=None,
            translation_placeholders=placeholders,
        ),
        _number_sensor(
            component,
            "flow_deviation",
            f"Rk{index} flow deviation",
            key=f"{prefix}_flow_deviation",
            translation_key="flow_deviation",
            translation_placeholders=placeholders,
        ),
    )


_HOT_WATER: tuple[TrovisSensorDescription, ...] = (
    _number_sensor(
        "hot_water",
        "setpoint_active",
        "Rk4 active domestic-hot-water setpoint",
        key="rk4dhw_setpoint_active",
        translation_key="dhw_setpoint_active",
        entity_category=None,
        state_class=None,
        translation_placeholders={"rk": "Rk4"},
    ),
    _number_sensor(
        "hot_water",
        "solar_operating_hours",
        "Rk4 solar operating hours",
        key="rk4dhw_solar_operating_hours",
        translation_key="solar_operating_hours",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        translation_placeholders={"rk": "Rk4"},
    ),
    _enum_sensor(
        "hot_water",
        "storage_status",
        "Rk4 storage status",
        key="rk4dhw_storage_status",
        translation_key="storage_status",
        translation_placeholders={"rk": "Rk4"},
    ),
    _number_sensor(
        "hot_water",
        "active_charge_setpoint",
        "Rk4 active charge setpoint",
        key="rk4dhw_active_charge_setpoint",
        translation_key="active_charge_setpoint",
        state_class=None,
        translation_placeholders={"rk": "Rk4"},
    ),
    _number_sensor(
        "hot_water",
        "control_deviation",
        "Rk4 control deviation",
        key="rk4dhw_control_deviation",
        translation_key="control_deviation",
        translation_placeholders={"rk": "Rk4"},
    ),
)


def _description_supported(
    coordinator: TrovisCoordinator,
    description: TrovisSensorDescription,
) -> bool:
    """Return whether a sensor description applies to this device."""
    if description.component == "sensors":
        if description.field not in coordinator.device.detected_sensors:
            return False

    if description.value_kind == "plain":
        return True

    component = getattr(coordinator.device, description.component)
    return component_supports_datapoint(component, description.field)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TrovisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Trovis sensors."""
    coordinator = entry.runtime_data

    descriptions = list(_GLOBAL)
    for index in coordinator.device.heating_circuit_indices:
        descriptions.extend(_rk_sensor_descriptions(index))
    descriptions.extend(_HOT_WATER)

    async_add_entities(
        TrovisSensor(coordinator, description)
        for description in descriptions
        if _description_supported(coordinator, description)
    )


class TrovisSensor(TrovisEntity, SensorEntity):
    """A single value read from a component field."""

    entity_description: TrovisSensorDescription

    def __init__(
        self,
        coordinator: TrovisCoordinator,
        description: TrovisSensorDescription,
    ) -> None:
        super().__init__(
            coordinator,
            description.key,
            description.component,
            "sensor",
            translation_key=description.translation_key,
            translation_placeholders=description.translation_placeholders,
        )
        self.entity_description = description
        self._enum_metadata: EnumMetadata | None = None
        self._key_by_value: dict[int, str] = {}

        if description.value_kind == "number":
            number = require_number_metadata(self._subsystem, description.field)
            self._attr_native_unit_of_measurement = (
                description.native_unit_of_measurement or ha_unit_from_number(number)
            )
            self._attr_device_class = (
                description.device_class or sensor_device_class_from_number(number)
            )

        elif description.value_kind == "enum":
            self._enum_metadata = require_enum_metadata(
                self._subsystem,
                description.field,
            )
            self._key_by_value = {
                int(option.value): option.key for option in self._enum_metadata.options
            }
            self._attr_options = [option.key for option in self._enum_metadata.options]
            self._attr_device_class = SensorDeviceClass.ENUM

        self._attr_state_class = description.state_class
        self._attr_entity_category = description.entity_category
        self._attr_entity_registry_enabled_default = (
            description.entity_registry_enabled_default
        )

    @property
    def native_value(self) -> object:
        """Return the current value in Home Assistant form."""
        value = getattr(self._subsystem, self.entity_description.field)

        if value is None:
            return None

        if self.entity_description.value_kind == "month_day":
            if not isinstance(value, MonthDay):
                return None
            return f"{value.month:02d}-{value.day:02d}"

        if self.entity_description.value_kind == "enum":
            try:
                return self._key_by_value.get(int(value))
            except (TypeError, ValueError):
                return None

        if isinstance(value, IntEnum):
            return value.name.lower()

        return value

    @property
    def extra_state_attributes(self) -> dict[str, int] | None:
        """Expose month and day separately for recurring dates."""
        if self.entity_description.value_kind != "month_day":
            return None

        value = getattr(self._subsystem, self.entity_description.field)
        if not isinstance(value, MonthDay):
            return None

        return {"month": value.month, "day": value.day}
