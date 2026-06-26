"""Sensor platform — diagnostic readings (temperatures, status, valve position).

Setpoints live on the climate / water-heater entities; room and storage
temperatures are those entities' current temperature. What remains here is
diagnostic, and is routed to the controller or the per-circuit / hot-water
sub-device it belongs to.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from ._local_dev import apply_local_trovis_modbus_override

apply_local_trovis_modbus_override()

from trovis_modbus import OperatingMode

from .coordinator import TrovisConfigEntry, TrovisCoordinator
from .entity import TrovisEntity

_MODE_OPTIONS = [mode.name.lower() for mode in OperatingMode]


@dataclass(frozen=True, kw_only=True)
class TrovisSensorDescription(SensorEntityDescription):
    """Describes a sensor reading one attribute of one component."""

    component: str
    attribute: str


def _temp(
    component: str, attribute: str, name: str, *, enabled: bool = True
) -> TrovisSensorDescription:
    return TrovisSensorDescription(
        key=f"{component}_{attribute}",
        name=name,
        component=component,
        attribute=attribute,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=enabled,
    )


def _switch(component: str, attribute: str, name: str) -> TrovisSensorDescription:
    return TrovisSensorDescription(
        key=f"{component}_{attribute}",
        name=name,
        component=component,
        attribute=attribute,
        device_class=SensorDeviceClass.ENUM,
        options=_MODE_OPTIONS,
        entity_category=EntityCategory.DIAGNOSTIC,
    )


# Global sensors.
_GLOBAL: tuple[TrovisSensorDescription, ...] = (
    _temp("sensors", "af1", "AF1 outside sensor 1"),
    _temp("sensors", "af2", "AF2 outside sensor 2"),

    _temp("sensors", "vf1", "VF1 flow sensor 1"),
    _temp("sensors", "vf2", "VF2 flow sensor 2"),
    _temp("sensors", "vf3", "VF3 flow sensor 3"),
    _temp("sensors", "vf4", "VF4 flow sensor 4"),

    _temp("sensors", "ruef1", "RüF1 return sensor 1"),
    _temp("sensors", "ruef2", "RüF2 return sensor 2"),
    _temp("sensors", "ruef3", "RüF3 return sensor 3"),

    _temp("sensors", "rf1", "RF1 room sensor 1"),
    _temp("sensors", "rf2", "RF2 room sensor 2"),
    _temp("sensors", "rf3", "RF3 room sensor 3"),

    _temp("sensors", "sf1", "SF1 hot water sensor 1"),
    _temp("sensors", "sf2", "SF2 hot water sensor 2"),
    _temp("sensors", "sf3_fg3", "SF3/FG3 hot water sensor / remote control 3"),

    _temp("sensors", "fg1", "FG1 remote control 1"),
    _temp("sensors", "fg2", "FG2 remote control 2"),

    # _temp("controller", "max_flow_setpoint", "Max flow setpoint", enabled=False),
    _temp("controller", "max_flow_setpoint", "Max flow setpoint"),
    _switch("controller", "switch_top", "Switch top"),
    _switch("controller", "switch_middle", "Switch middle"),
    _switch("controller", "switch_bottom", "Switch bottom"),

    TrovisSensorDescription(
        key="controller_error_status",
        name="Error status",
        component="controller",
        attribute="error_status",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TrovisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Trovis sensors."""
    coordinator = entry.runtime_data
    entities = [TrovisSensor(coordinator, description) for description in _GLOBAL]

    for index in (1, 2, 3):
        component = f"heating_circuit_{index}"
        entities.append(
            TrovisSensor(
                coordinator,
                TrovisSensorDescription(
                    key=f"{component}_control_signal",
                    name="Valve position",
                    component=component,
                    attribute="control_signal",
                    native_unit_of_measurement=PERCENTAGE,
                    state_class=SensorStateClass.MEASUREMENT,
                    entity_category=EntityCategory.DIAGNOSTIC,
                ),
            )
        )

    async_add_entities(entities)


class TrovisSensor(TrovisEntity, SensorEntity):
    """A single value read from a component attribute."""

    entity_description: TrovisSensorDescription

    def __init__(
        self, coordinator: TrovisCoordinator, description: TrovisSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key, description.component, "sensor")
        self.entity_description = description

    @property
    def native_value(self) -> object:
        value = getattr(self._subsystem, self.entity_description.attribute)
        if isinstance(value, IntEnum):
            return value.name.lower()
        return value
