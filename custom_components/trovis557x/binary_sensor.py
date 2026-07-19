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
        "outside_temperature_control_autonomous",
        "Outside-temperature control autonomous",
        key="outside_temperature_control_autonomous",
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
    ("outside_shutdown", "Outside-temperature shutdown", None, True),
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
        "return_setpoint_control_autonomous",
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


_HOT_WATER: tuple[TrovisBinaryDescription, ...] = (
    _binary(
        "hot_water",
        "charge_pump_running",
        "Charge pump",
        BinarySensorDeviceClass.HEAT,
        key="rk4dhw_charge_pump_running",
        translation_key="charge_pump_running",
        translation_placeholders={"rk": "Rk4"},
    ),
    _binary(
        "hot_water",
        "disinfection_active",
        "Disinfection",
        BinarySensorDeviceClass.RUNNING,
        key="rk4dhw_disinfection_active",
        translation_key="disinfection_active",
        translation_placeholders={"rk": "Rk4"},
    ),
    _binary(
        "hot_water",
        "circulation_pump_running",
        "Circulation pump",
        BinarySensorDeviceClass.RUNNING,
        key="rk4dhw_circulation_pump_running",
        translation_key="circulation_pump_running",
        translation_placeholders={"rk": "Rk4"},
    ),
    _binary(
        "hot_water",
        "manual_active",
        "Manual operation",
        key="rk4dhw_manual_active",
        translation_key="manual_active",
        translation_placeholders={"rk": "Rk4"},
    ),
    _binary(
        "hot_water",
        "automatic",
        "Automatic operation",
        key="rk4dhw_automatic",
        translation_key="automatic",
        translation_placeholders={"rk": "Rk4"},
    ),
    _binary(
        "hot_water",
        "priority",
        "Domestic-hot-water priority",
        key="rk4dhw_priority",
        translation_key="priority",
        translation_placeholders={"rk": "Rk4"},
    ),
    _binary(
        "hot_water",
        "max_charge_limit_active",
        "Maximum charge-temperature limit",
        key="rk4dhw_max_charge_limit_active",
        translation_key="max_charge_limit_active",
        translation_placeholders={"rk": "Rk4"},
    ),
    _binary(
        "hot_water",
        "return_limit_active",
        "Return-temperature limit",
        key="rk4dhw_return_limit_active",
        translation_key="return_limit_active",
        translation_placeholders={"rk": "Rk4"},
    ),
    _binary(
        "hot_water",
        "standby",
        "Standby",
        key="rk4dhw_standby",
        translation_key="standby",
        translation_placeholders={"rk": "Rk4"},
    ),
    _binary(
        "hot_water",
        "frost_protection",
        "Frost protection",
        BinarySensorDeviceClass.COLD,
        key="rk4dhw_frost_protection",
        translation_key="frost_protection",
        translation_placeholders={"rk": "Rk4"},
    ),
    _binary(
        "hot_water",
        "solar_pump_running",
        "Solar pump",
        BinarySensorDeviceClass.RUNNING,
        key="rk4dhw_solar_pump_running",
        translation_key="solar_pump_running",
        translation_placeholders={"rk": "Rk4"},
    ),
    _binary(
        "hot_water",
        "storage_charging_active",
        "Storage charging active",
        BinarySensorDeviceClass.RUNNING,
        key="rk4dhw_storage_charging_active",
        translation_key="storage_charging_active",
        translation_placeholders={"rk": "Rk4"},
    ),
    _binary(
        "hot_water",
        "storage_charging_locked",
        "Storage charging locked",
        key="rk4dhw_storage_charging_locked",
        translation_key="storage_charging_locked",
        translation_placeholders={"rk": "Rk4"},
    ),
    _binary(
        "hot_water",
        "mode_control_autonomous",
        "Mode control autonomous",
        key="rk4dhw_mode_control_autonomous",
        translation_key="mode_control_autonomous",
        translation_placeholders={"rk": "Rk4"},
        enabled=False,
    ),
    _binary(
        "hot_water",
        "charge_pump_control_autonomous",
        "Charge-pump control autonomous",
        key="rk4dhw_charge_pump_control_autonomous",
        translation_key="charge_pump_control_autonomous",
        translation_placeholders={"rk": "Rk4"},
        enabled=False,
    ),
    _binary(
        "hot_water",
        "circulation_pump_control_autonomous",
        "Circulation-pump control autonomous",
        key="rk4dhw_circulation_pump_control_autonomous",
        translation_key="circulation_pump_control_autonomous",
        translation_placeholders={"rk": "Rk4"},
        enabled=False,
    ),
    _binary(
        "hot_water",
        "special_setpoint_control_autonomous",
        "Special-setpoint control autonomous",
        key="rk4dhw_special_setpoint_control_autonomous",
        translation_key="special_setpoint_control_autonomous",
        translation_placeholders={"rk": "Rk4"},
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
    descriptions = [*_CONTROLLER, *_HOT_WATER]

    for index in coordinator.device.heating_circuit_indices:
        component = f"heating_circuit_{index}"
        placeholders = {"rk": f"Rk{index}"}
        descriptions.extend(
            _binary(
                component,
                field,
                name,
                device_class,
                key=f"rk{index}_{field}",
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
