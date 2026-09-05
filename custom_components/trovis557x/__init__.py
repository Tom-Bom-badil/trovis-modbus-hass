"""The Samson Trovis 557x integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, cast

import voluptuous as vol
from homeassistant.components.modbus import async_get_unit
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, UnitOfTemperature
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv, service
from homeassistant.helpers.entity import DeviceInfo, async_generate_entity_id
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify
from modbus_connection import ModbusSerialParams, ModbusTcpParams

from .const import (
    CONF_BAUDRATE,
    CONF_BYTESIZE,
    CONF_CONNECTION_TYPE,
    CONF_DETECTED_SENSORS,
    CONF_DEVICE,
    CONF_EXCLUDED_COILS,
    CONF_EXCLUDED_REGISTERS,
    CONF_FRAMER,
    CONF_HOST,
    CONF_MODEL,
    CONF_PARITY,
    CONF_PORT,
    CONF_SLUG,
    CONF_STOPBITS,
    CONF_UNIT_ID,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    DEFAULT_SLUG,
    DOMAIN,
    FRAMER_RTU,
    FRAMER_SOCKET,
)
from .read_exclusions import parse_address_list

if TYPE_CHECKING:
    from trovis_modbus.metadata import (
        BooleanMetadata,
        DatapointMetadata,
        EnumMetadata,
        NumberMetadata,
    )

    from .coordinator import TrovisCoordinator


SERVICE_SET_SIMULATION_VALUE = "set_simulation_value"
SERVICE_RESET_SIMULATION = "reset_simulation"
ATTR_SIMULATION_FIELD = "field"
ATTR_SIMULATION_VALUE = "value"
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def create_modbus_params(
    data: Mapping[str, Any],
) -> ModbusSerialParams | ModbusTcpParams:
    """Build Modbus connection parameters for the Home Assistant shared stack."""
    connection_type = str(data[CONF_CONNECTION_TYPE])
    if connection_type == CONNECTION_TYPE_TCP:
        return ModbusTcpParams(
            host=str(data[CONF_HOST]),
            port=int(data[CONF_PORT]),
            framer=cast(
                Literal["socket", "rtu"],
                str(data.get(CONF_FRAMER, FRAMER_SOCKET)),
            ),
        )
    if connection_type == CONNECTION_TYPE_SERIAL:
        return ModbusSerialParams(
            device=str(data[CONF_DEVICE]),
            baudrate=int(data[CONF_BAUDRATE]),
            bytesize=cast(
                Literal[7, 8],
                int(data[CONF_BYTESIZE]),
            ),
            parity=cast(
                Literal["N", "E", "O"],
                str(data[CONF_PARITY]),
            ),
            stopbits=cast(
                Literal[1, 2],
                int(data[CONF_STOPBITS]),
            ),
            framer=FRAMER_RTU,
        )
    raise ValueError(f"Unsupported Modbus connection type: {connection_type!r}")


def require_datapoint_metadata(
    component: Any,
    field: str,
) -> DatapointMetadata:
    """Return neutral TROVIS metadata for a component field."""
    if hasattr(component, "metadata_for"):
        metadata = component.metadata_for(field)
        if metadata is not None:
            return metadata
    if hasattr(component, "require_metadata_for"):
        try:
            return component.require_metadata_for(field)
        except (AttributeError, KeyError) as err:
            raise ValueError(f"TROVIS field {field!r} has no metadata") from err

    raise ValueError(f"TROVIS field {field!r} has no metadata")


def component_supports_datapoint(
    component: Any,
    field: str,
) -> bool:
    """Return whether a component exposes metadata for a datapoint."""
    try:
        require_datapoint_metadata(component, field)
    except ValueError:
        return False

    return True


def require_number_metadata(
    component: Any,
    field: str,
) -> NumberMetadata:
    """Return number metadata for a component field."""
    metadata = require_datapoint_metadata(component, field)
    if metadata.number is None:
        raise ValueError(f"TROVIS field {field!r} is not numeric")

    return metadata.number


def require_enum_metadata(
    component: Any,
    field: str,
) -> EnumMetadata:
    """Return enum metadata for a component field."""
    metadata = require_datapoint_metadata(component, field)

    if metadata.enum is None:
        raise ValueError(f"TROVIS field {field!r} is not an enum")

    return metadata.enum


def require_boolean_metadata(
    component: Any,
    field: str,
) -> BooleanMetadata:
    """Return boolean metadata for a component field."""
    metadata = require_datapoint_metadata(component, field)

    if metadata.boolean is None:
        raise ValueError(f"TROVIS field {field!r} is not boolean")

    return metadata.boolean


def ha_unit_from_number(number: NumberMetadata) -> str | None:
    """Map a neutral TROVIS unit to a Home Assistant unit."""
    if number.unit == "°C":
        return UnitOfTemperature.CELSIUS

    if number.unit == "K":
        return UnitOfTemperature.KELVIN

    if number.unit is None or number.unit.strip() == "":
        return None

    return number.unit


## this is relevant for developers only
try:
    from ._local_dev_overrides import (
        DEVELOPER_MODE,
        apply_local_function_overrides,
        apply_local_log_overrides,
    )
except ModuleNotFoundError:
    DEVELOPER_MODE = False
else:
    if DEVELOPER_MODE:
        apply_local_function_overrides()
        apply_local_log_overrides()


def rk1_to_rk3_indices(coordinator: TrovisCoordinator) -> tuple[int, ...]:
    """Return active technical Rk1-Rk3 slots for this hydronic system."""
    return tuple(
        index for index in coordinator.device.control_circuit_indices if index <= 3
    )


def _rk_sub_device(
    coordinator: TrovisCoordinator,
    index: int,
) -> tuple[str, str, str]:
    """Return identity and role-aware presentation for one Rk sub-device."""
    from trovis_modbus import ControlCircuitRole

    role = coordinator.device.control_circuit_role(index)
    component = f"rk{index}"

    if role is ControlCircuitRole.HEATING:
        return (
            component,
            f"Rk{index} – Heating circuit {index}",
            f"{component}_heating",
        )

    if role is ControlCircuitRole.PRECONTROL:
        return (
            component,
            f"Rk{index} – Precontrol circuit",
            f"{component}_precontrol",
        )
    if role is ControlCircuitRole.BUFFER_TANK:
        return (
            component,
            f"Rk{index} – Buffer tank circuit",
            f"{component}_buffer_tank",
        )

    if role is ControlCircuitRole.DOMESTIC_HOT_WATER:
        return (
            component,
            "Rk4 – Domestic hot water",
            "rk4_dhw",
        )

    return (
        component,
        f"Rk{index} – Control circuit {index}",
        component,
    )


def _sub_device(
    coordinator: TrovisCoordinator,
    component: str,
) -> tuple[str, str, str] | None:
    """Return (sub-device id, fallback name, translation key), or None."""
    if component == "sensors":
        return "measurements", "Measurements", "measurements"

    if component == "solar":
        return "solar", "Solar – Solar circuit", "solar"

    if component == "pumps_and_valves":
        return "pumps_and_valves", "Pumps and Valves", "pumps_and_valves"
    if component == "buffer_tank":
        return _rk_sub_device(coordinator, 1)

    if component.startswith("rk") and component[2:].isdigit():
        index = int(component[2:])
        if 1 <= index <= 4:
            return _rk_sub_device(coordinator, index)

    return None


def _entry_slug(value: object) -> str:
    """Return a Home Assistant friendly entity prefix."""
    return slugify(str(value or "")) or DEFAULT_SLUG


class TrovisEntity(CoordinatorEntity["TrovisCoordinator"]):
    """Common identity + device-info for every TROVIS entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TrovisCoordinator,
        key: str,
        component: str,
        platform: str,
        translation_key: str | None = None,
        translation_placeholders: Mapping[str, str] | None = None,
        device_component: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._component = component
        entry = coordinator.config_entry

        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = translation_key or key
        self._attr_translation_placeholders = dict(translation_placeholders or {})

        entity_slug = _entry_slug(entry.data.get(CONF_SLUG, entry.title))
        object_id = f"{entity_slug}_{key}"
        self._attr_suggested_object_id = object_id
        self.entity_id = async_generate_entity_id(
            f"{platform}.{{}}",
            object_id,
            hass=coordinator.hass,
        )

        info = coordinator.device.info
        sub = _sub_device(coordinator, device_component or component)
        if sub is None:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, entry.entry_id)},
                manufacturer=info.manufacturer,
                model=info.model,
                name=entry.title,
                sw_version=info.firmware_version,
                hw_version=info.hardware_version,
                serial_number=info.serial_number,
            )
        else:
            sub_id, sub_name, sub_translation_key = sub
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{entry.entry_id}_{sub_id}")},
                manufacturer=info.manufacturer,
                name=sub_name,
                translation_key=sub_translation_key,
                via_device=(DOMAIN, entry.entry_id),
            )

    @property
    def _subsystem(self) -> Any:
        """Return the shared library component used by this entity."""
        return getattr(
            self.coordinator.device,
            self._component,
        )

    async def _async_write_datapoint(
        self,
        field: str,
        value: object,
    ) -> None:
        """Write one library datapoint and refresh the shared coordinator."""
        from trovis_modbus import (
            TrovisValueValidationError,
            TrovisWriteAccessDisabledError,
            TrovisWriteAccessError,
            TrovisWriteNotImplementedError,
        )

        if not self.coordinator.device.writing_enabled:
            raise HomeAssistantError("Please enable writing for changes!")
        try:
            await self._subsystem.async_write_datapoint(
                field,
                value,
                access_code=self.coordinator.access_code,
            )
        except (
            TrovisWriteAccessDisabledError,
            TrovisWriteAccessError,
            TrovisValueValidationError,
        ) as err:
            raise HomeAssistantError(str(err)) from err
        except TrovisWriteNotImplementedError as err:
            raise HomeAssistantError(
                "Writing TROVIS data points is not implemented yet"
            ) from err
        await self.coordinator.async_request_refresh()


async def _async_set_simulation_value(
    entity: Any,
    service_call: ServiceCall,
) -> None:
    """Route a local simulation-value action to a simulation helper entity."""
    from .simulation import TrovisHeatingCurveSimulationSensor

    if not isinstance(entity, TrovisHeatingCurveSimulationSensor):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="not_simulation_entity",
            translation_placeholders={"entity_id": entity.entity_id},
        )

    await entity.async_set_simulation_value(
        field=str(service_call.data[ATTR_SIMULATION_FIELD]),
        value=float(service_call.data[ATTR_SIMULATION_VALUE]),
    )


async def _async_reset_simulation(
    entity: Any,
    _service_call: ServiceCall,
) -> None:
    """Route a reset action to a simulation helper entity."""
    from .simulation import TrovisHeatingCurveSimulationSensor

    if not isinstance(entity, TrovisHeatingCurveSimulationSensor):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="not_simulation_entity",
            translation_placeholders={"entity_id": entity.entity_id},
        )
    await entity.async_reset_simulation()


async def async_setup(
    hass: HomeAssistant,
    _config: Mapping[str, Any],
) -> bool:
    """Set up integration-wide TROVIS entity actions."""
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_SET_SIMULATION_VALUE,
        entity_domain="sensor",
        schema={
            vol.Required(ATTR_SIMULATION_FIELD): cv.string,
            vol.Required(ATTR_SIMULATION_VALUE): vol.Coerce(float),
        },
        func=_async_set_simulation_value,
    )
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_RESET_SIMULATION,
        entity_domain="sensor",
        schema=None,
        func=_async_reset_simulation,
    )
    return True


PLATFORMS = [
    Platform.BINARY_SENSOR,
    # Temporarily disabled; dedicated redesign pending - this is NOT a thermostat!
    # Platform.CLIMATE,
    Platform.DATE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
    Platform.TIME,
    Platform.WATER_HEATER,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[TrovisCoordinator],
) -> bool:
    """Set up Trovis 557x from a config entry."""

    from trovis_modbus import Trovis557x

    from .coordinator import TrovisCoordinator

    settings = {
        **entry.data,
        **entry.options,
    }
    try:
        unit_id = int(settings[CONF_UNIT_ID])
        model = int(settings[CONF_MODEL])
        detected_sensors = tuple(settings[CONF_DETECTED_SENSORS])
        excluded_registers = parse_address_list(
            str(settings.get(CONF_EXCLUDED_REGISTERS, "") or "")
        )
        excluded_coils = parse_address_list(
            str(settings.get(CONF_EXCLUDED_COILS, "") or "")
        )
        params = create_modbus_params(settings)
        unit = async_get_unit(hass, entry, params, unit_id)
    except (KeyError, TypeError, ValueError) as err:
        raise ConfigEntryNotReady(
            "The TROVIS config entry does not contain valid connection or probe data"
        ) from err
    except HomeAssistantError as err:
        raise ConfigEntryNotReady(str(err)) from err

    try:
        device = Trovis557x(
            unit,
            model=model,
            detected_sensors=detected_sensors,
            excluded_registers=excluded_registers,
            excluded_coils=excluded_coils,
        )
    except ValueError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = TrovisCoordinator(
        hass,
        entry,
        device,
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[TrovisCoordinator],
) -> bool:
    """Unload a Trovis 557x config entry."""
    return await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )
