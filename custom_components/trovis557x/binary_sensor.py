"""Binary sensors for read-only TROVIS operating and control states."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import TrovisConfigEntry, TrovisCoordinator
from .entity import TrovisEntity
from .metadata import component_supports_datapoint


@dataclass(frozen=True, kw_only=True)
class TrovisBinaryDescription(BinarySensorEntityDescription):
    """Describe a binary sensor reading one boolean Lib field."""

    component: str
    field: str


def _binary(
    component: str,
    field: str,
    name: str,
    device_class: BinarySensorDeviceClass | None = None,
    *,
    key: str | None = None,
    translation_key: str | None = None,
    translation_placeholders: dict[str, str] | None = None,
    enabled: bool = True,
) -> TrovisBinaryDescription:
    """Return a binary-sensor description."""
    return TrovisBinaryDescription(
        key=key or f"{component}_{field}",
        translation_key=translation_key,
        translation_placeholders=translation_placeholders,
        name=name,
        component=component,
        field=field,
        device_class=device_class,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=enabled,
    )


_CONTROLLER: tuple[TrovisBinaryDescription, ...] = (
    _binary(
        "controller",
        "general_fault",
        "Fault",
        BinarySensorDeviceClass.PROBLEM,
        key="general_fault",
    ),
    _binary("controller", "summer_active", "Summer mode", key="summer_active"),
    _binary(
        "controller",
        "data_entry_active",
        "Data entry active",
        key="data_entry_active",
        enabled=False,
    ),
    _binary(
        "controller",
        "data_entry_performed",
        "Data entry performed",
        key="data_entry_performed",
        enabled=False,
    ),
    _binary(
        "controller",
        "global_level_autark",
        "Global control autonomous",
        key="global_level_autark",
        enabled=False,
    ),
    _binary(
        "controller",
        "outdoor_temperature_control_autonomous",
        "Outdoor-temperature control autonomous",
        key="outdoor_temperature_control_autonomous",
        enabled=False,
    ),
    _binary(
        "controller",
        "any_circuit_not_automatic",
        "At least one circuit not automatic",
        key="any_circuit_not_automatic",
    ),
    _binary(
        "controller",
        "rotary_switch_not_automatic",
        "At least one rotary switch not automatic",
        key="rotary_switch_not_automatic",
    ),
)


_CIRCUIT_STATES: tuple[tuple[str, str, BinarySensorDeviceClass | None, bool], ...] = (
    ("pump_running", "Pump", BinarySensorDeviceClass.RUNNING, True),
    ("frost_protection", "Frost protection", BinarySensorDeviceClass.COLD, True),
    ("standby", "Standby", None, True),
    ("manual_active", "Manual operation", None, True),
    ("automatic", "Automatic operation", None, True),
    ("day_active", "Day operation", None, True),
    ("night_active", "Night operation", None, True),
    ("hold_active", "Hold operation", None, True),
    ("setback_active", "Setback operation", None, True),
    ("heat_up_active", "Heat-up operation", BinarySensorDeviceClass.HEAT, True),
    ("return_limit_active", "Return-temperature limit", None, True),
    ("outdoor_temperature_deactivation", "Outdoor-temperature shutdown", None, True),
    ("valve_closing", "Valve closing", BinarySensorDeviceClass.MOVING, True),
    ("valve_opening", "Valve opening", BinarySensorDeviceClass.MOVING, True),
    ("mode_control_autonomous", "Mode control autonomous", None, False),
    ("valve_control_autonomous", "Valve control autonomous", None, False),
    ("pump_control_autonomous", "Pump control autonomous", None, False),
    (
        "flow_setpoint_control_autonomous",
        "Flow-setpoint control autonomous",
        None,
        False,
    ),
    (
        "return_flow_temperature_setpoint_control_autonomous",
        "Return-setpoint control autonomous",
        None,
        False,
    ),
    (
        "room_setpoint_control_autonomous",
        "Room-setpoint control autonomous",
        None,
        False,
    ),
)


_WW: tuple[TrovisBinaryDescription, ...] = (
    _binary(
        "ww",
        "storage_tank_charging_pump_running",
        "Storage tank charging pump",
        BinarySensorDeviceClass.HEAT,
        key="ww_storage_tank_charging_pump_running",
        translation_key="storage_tank_charging_pump_running",
        translation_placeholders={"component": "WW"},
    ),
    _binary(
        "ww",
        "disinfection_active",
        "Disinfection",
        BinarySensorDeviceClass.RUNNING,
        key="ww_disinfection_active",
        translation_key="disinfection_active",
        translation_placeholders={"component": "WW"},
    ),
    _binary(
        "ww",
        "circulation_pump_running",
        "Circulation pump",
        BinarySensorDeviceClass.RUNNING,
        key="ww_circulation_pump_running",
        translation_key="circulation_pump_running",
        translation_placeholders={"component": "WW"},
    ),
    _binary(
        "ww",
        "manual_active",
        "Manual operation",
        key="ww_manual_active",
        translation_key="manual_active",
        translation_placeholders={"component": "WW"},
    ),
    _binary(
        "ww",
        "automatic",
        "Automatic operation",
        key="ww_automatic",
        translation_key="automatic",
        translation_placeholders={"component": "WW"},
    ),
    _binary(
        "ww",
        "priority",
        "Domestic hot-water priority",
        key="ww_priority",
        translation_key="priority",
        translation_placeholders={"component": "WW"},
    ),
    _binary(
        "ww",
        "maximum_charging_temperature_limit_active",
        "Maximum charging-temperature limit",
        key="ww_maximum_charging_temperature_limit_active",
        translation_key="maximum_charging_temperature_limit_active",
        translation_placeholders={"component": "WW"},
    ),
    _binary(
        "ww",
        "return_limit_active",
        "Return-temperature limit",
        key="ww_return_limit_active",
        translation_key="return_limit_active",
        translation_placeholders={"component": "WW"},
    ),
    _binary(
        "ww",
        "standby",
        "Standby",
        key="ww_standby",
        translation_key="standby",
        translation_placeholders={"component": "WW"},
    ),
    _binary(
        "ww",
        "frost_protection",
        "Frost protection",
        BinarySensorDeviceClass.COLD,
        key="ww_frost_protection",
        translation_key="frost_protection",
        translation_placeholders={"component": "WW"},
    ),
    _binary(
        "ww",
        "solar_circuit_pump_running",
        "Solar circuit pump",
        BinarySensorDeviceClass.RUNNING,
        key="ww_solar_circuit_pump_running",
        translation_key="solar_circuit_pump_running",
        translation_placeholders={"component": "WW"},
    ),
    _binary(
        "ww",
        "storage_tank_charging_active",
        "Storage charging active",
        BinarySensorDeviceClass.RUNNING,
        key="ww_storage_tank_charging_active",
        translation_key="storage_tank_charging_active",
        translation_placeholders={"component": "WW"},
    ),
    _binary(
        "ww",
        "storage_tank_charging_locked",
        "Storage charging locked",
        key="ww_storage_tank_charging_locked",
        translation_key="storage_tank_charging_locked",
        translation_placeholders={"component": "WW"},
    ),
    _binary(
        "ww",
        "mode_control_autonomous",
        "Mode control autonomous",
        key="ww_mode_control_autonomous",
        translation_key="mode_control_autonomous",
        translation_placeholders={"component": "WW"},
        enabled=False,
    ),
    _binary(
        "ww",
        "storage_tank_charging_pump_control_autonomous",
        "Storage-tank-charging-pump control autonomous",
        key="ww_storage_tank_charging_pump_control_autonomous",
        translation_key="storage_tank_charging_pump_control_autonomous",
        translation_placeholders={"component": "WW"},
        enabled=False,
    ),
    _binary(
        "ww",
        "circulation_pump_control_autonomous",
        "Circulation-pump control autonomous",
        key="ww_circulation_pump_control_autonomous",
        translation_key="circulation_pump_control_autonomous",
        translation_placeholders={"component": "WW"},
        enabled=False,
    ),
    _binary(
        "ww",
        "special_setpoint_control_autonomous",
        "Special-setpoint control autonomous",
        key="ww_special_setpoint_control_autonomous",
        translation_key="special_setpoint_control_autonomous",
        translation_placeholders={"component": "WW"},
        enabled=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TrovisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Trovis binary sensors."""
    coordinator = entry.runtime_data
    descriptions = [*_CONTROLLER, *_WW]

    for index in coordinator.device.heating_circuit_indices:
        component = f"hk{index}"
        placeholders = {"component": f"Hk{index}"}
        descriptions.extend(
            _binary(
                component,
                field,
                name,
                device_class,
                key=f"hk{index}_{field}",
                translation_key=field,
                translation_placeholders=placeholders,
                enabled=enabled,
            )
            for field, name, device_class, enabled in _CIRCUIT_STATES
        )

    async_add_entities(
        TrovisBinarySensor(coordinator, description)
        for description in descriptions
        if component_supports_datapoint(
            getattr(coordinator.device, description.component),
            description.field,
        )
    )


class TrovisBinarySensor(TrovisEntity, BinarySensorEntity):
    """A single read-only boolean value."""

    entity_description: TrovisBinaryDescription

    def __init__(
        self,
        coordinator: TrovisCoordinator,
        description: TrovisBinaryDescription,
    ) -> None:
        super().__init__(
            coordinator,
            description.key,
            description.component,
            "binary_sensor",
            translation_key=description.translation_key,
            translation_placeholders=description.translation_placeholders,
        )
        self.entity_description = description
        self._attr_entity_category = description.entity_category
        self._attr_entity_registry_enabled_default = (
            description.entity_registry_enabled_default
        )

    @property
    def is_on(self) -> bool | None:
        """Return the current boolean state."""
        return getattr(self._subsystem, self.entity_description.field)
