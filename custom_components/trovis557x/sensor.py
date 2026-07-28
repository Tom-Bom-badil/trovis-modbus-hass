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
from .entity import TrovisEntity, rk1_to_rk3_indices
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
        key="system_code",
        translation_key="system_code",
        name="System code number",
        component="info",
        field="system_code",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    _number_sensor(
        "sensors",
        "af1",
        "AF1 outdoor sensor 1",
        key="sensor_af1",
        translation_key="outdoor_temperature_1",
    ),
    _number_sensor(
        "sensors",
        "af2",
        "AF2 outdoor sensor 2",
        key="sensor_af2",
        translation_key="outdoor_temperature_2",
    ),
    _number_sensor(
        "sensors",
        "vf1",
        "VF1 flow sensor 1",
        key="sensor_vf1",
        translation_key="flow_temperature_1",
    ),
    _number_sensor(
        "sensors",
        "vf2",
        "VF2 flow sensor 2",
        key="sensor_vf2",
        translation_key="flow_temperature_2",
    ),
    _number_sensor(
        "sensors",
        "vf3",
        "VF3 flow sensor 3",
        key="sensor_vf3",
        translation_key="flow_temperature_3",
    ),
    _number_sensor(
        "sensors",
        "vf4",
        "VF4 flow sensor 4",
        key="sensor_vf4",
        translation_key="flow_temperature_4",
    ),
    _number_sensor(
        "sensors",
        "ruef1",
        "RüF1 return flow sensor 1",
        key="sensor_ruef1",
        translation_key="return_temperature_1",
    ),
    _number_sensor(
        "sensors",
        "ruef2",
        "RüF2 return flow sensor 2",
        key="sensor_ruef2",
        translation_key="return_temperature_2",
    ),
    _number_sensor(
        "sensors",
        "ruef3",
        "RüF3 return flow sensor 3",
        key="sensor_ruef3",
        translation_key="return_temperature_3",
    ),
    _number_sensor(
        "sensors",
        "rf1",
        "RF1 room sensor 1",
        key="sensor_rf1",
        translation_key="room_temperature_1",
    ),
    _number_sensor(
        "sensors",
        "rf2",
        "RF2 room sensor 2",
        key="sensor_rf2",
        translation_key="room_temperature_2",
    ),
    _number_sensor(
        "sensors",
        "rf3",
        "RF3 room sensor 3",
        key="sensor_rf3",
        translation_key="room_temperature_3",
    ),
    _number_sensor(
        "sensors",
        "sf1",
        "SF1 storage tank sensor 1",
        key="sensor_sf1",
        translation_key="ww_storage_temperature",
    ),
    _number_sensor(
        "sensors",
        "sf2",
        "SF2 storage tank sensor 2",
        key="sensor_sf2",
        translation_key="ww_storage_temperature_lower",
    ),
    _number_sensor(
        "sensors",
        "sf3",
        "SF3 storage tank sensor 3",
        key="sensor_sf3",
        translation_key="sf3",
    ),
    _number_sensor(
        "sensors",
        "ae1",
        "AE1 analog input 1",
        key="sensor_ae1",
        translation_key="ae1",
    ),
    _number_sensor(
        "sensors",
        "fg1",
        "FG1 potentiometer 1",
        key="sensor_fg1",
        translation_key="fg1",
    ),
    _number_sensor(
        "sensors",
        "ae2",
        "AE2 analog input 2",
        key="sensor_ae2",
        translation_key="ae2",
    ),
    _number_sensor(
        "sensors",
        "fg2",
        "FG2 potentiometer 2",
        key="sensor_fg2",
        translation_key="fg2",
    ),
    _number_sensor(
        "sensors",
        "ae3",
        "AE3 analog input 3",
        key="sensor_ae3",
        translation_key="ae3",
    ),
    _number_sensor(
        "sensors",
        "fg3",
        "FG3 potentiometer 3",
        key="sensor_fg3",
        translation_key="fg3",
    ),
    _number_sensor(
        "sensors",
        "pulse_rate",
        "IMP pulse rate",
        key="sensor_imp",
        translation_key="pulse_rate",
    ),
    _number_sensor(
        "sensors",
        "analog_input_voltage",
        "AE analog input voltage",
        key="sensor_ae_voltage",
        translation_key="analog_input_voltage",
    ),
    _number_sensor(
        "sensors",
        "analog_input_current",
        "AE analog input current",
        key="sensor_ae_current",
        translation_key="analog_input_current",
    ),
    _number_sensor(
        "sensors",
        "summer_outdoor_temperature_average",
        "Summer outdoor-temperature average",
        key="summer_outdoor_temperature_average",
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
    component = f"rk{index}"
    prefix = f"rk{index}"
    placeholders = {"component": f"Rk{index}"}

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
            "return_flow_gradient",
            f"Rk{index} return gradient",
            key=f"{prefix}_return_flow_gradient",
            translation_key="return_flow_gradient",
            state_class=None,
            translation_placeholders=placeholders,
        ),
        _number_sensor(
            component,
            "return_flow_level",
            f"Rk{index} return level",
            key=f"{prefix}_return_flow_level",
            translation_key="return_flow_level",
            state_class=None,
            translation_placeholders=placeholders,
        ),
        _number_sensor(
            component,
            "return_flow_base_point",
            f"Rk{index} return base point",
            key=f"{prefix}_return_flow_base_point",
            translation_key="return_flow_base_point",
            state_class=None,
            translation_placeholders=placeholders,
        ),
        _number_sensor(
            component,
            "return_flow_temperature_setpoint",
            f"Rk{index} return setpoint",
            key=f"{prefix}_return_flow_temperature_setpoint",
            translation_key="return_flow_temperature_setpoint",
            state_class=None,
            translation_placeholders=placeholders,
        ),
        _number_sensor(
            component,
            "flow_control_deviation",
            f"Rk{index} flow deviation",
            key=f"{prefix}_flow_control_deviation",
            translation_key="flow_control_deviation",
            translation_placeholders=placeholders,
        ),
    )


_RK4: tuple[TrovisSensorDescription, ...] = (
    _number_sensor(
        "rk4",
        "setpoint_active",
        "Rk4 active domestic hot-water setpoint",
        key="rk4_setpoint_active",
        translation_key="rk4_setpoint_active",
        entity_category=None,
        state_class=None,
        translation_placeholders={"component": "Rk4"},
    ),
    _enum_sensor(
        "rk4",
        "storage_status",
        "Rk4 storage status",
        key="rk4_storage_status",
        translation_key="storage_status",
        translation_placeholders={"component": "Rk4"},
    ),
    _number_sensor(
        "rk4",
        "active_charging_setpoint",
        "Rk4 active charging set point",
        key="rk4_active_charging_setpoint",
        translation_key="active_charging_setpoint",
        state_class=None,
        translation_placeholders={"component": "Rk4"},
    ),
    _number_sensor(
        "rk4",
        "control_deviation",
        "Rk4 control deviation",
        key="rk4_control_deviation",
        translation_key="control_deviation",
        translation_placeholders={"component": "Rk4"},
    ),
)


_SOLAR: tuple[TrovisSensorDescription, ...] = (
    _number_sensor(
        "solar",
        "operating_hours",
        "Solar operating hours",
        key="solar_operating_hours",
        translation_key="solar_operating_hours",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
)


def _description_supported(
    coordinator: TrovisCoordinator,
    description: TrovisSensorDescription,
) -> bool:
    """Return whether a sensor description applies to this device."""
    if description.component == "sensors":
        if description.field not in coordinator.device.available_sensor_keys:
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
    for index in rk1_to_rk3_indices(coordinator):
        descriptions.extend(_rk_sensor_descriptions(index))
    if coordinator.device.has_rk4:
        descriptions.extend(_RK4)
    if coordinator.device.has_solar:
        descriptions.extend(_SOLAR)

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
