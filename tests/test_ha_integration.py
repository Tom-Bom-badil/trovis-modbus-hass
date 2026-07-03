"""Home Assistant tests for the shared-connection TROVIS integration."""

from __future__ import annotations

import pytest
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry
from trovis_modbus import DEFAULT_WRITE_ACCESS_CODE

from custom_components.trovis557x.const import (
    CONF_ACCESS_CODE,
    CONF_CONNECTION_ENTRY_ID,
    CONF_DETECTED_SENSORS,
    CONF_MODEL,
    CONF_SLUG,
    CONF_UNIT_ID,
    DOMAIN,
)

from .conftest import UNIT_ID, MockProvider

MODEL = 5579
NAME = "Test Trovis"
SLUG = "test_trovis"

DETECTED_SENSORS = [
    "af1",
    "vf1",
    "rf1",
    "sf1",
]


def _entry_data(provider: MockProvider) -> dict[str, object]:
    """Return a complete shared-connection TROVIS config entry."""
    return {
        CONF_CONNECTION_ENTRY_ID: provider.entry.entry_id,
        CONF_UNIT_ID: UNIT_ID,
        CONF_NAME: NAME,
        CONF_SLUG: SLUG,
        CONF_ACCESS_CODE: DEFAULT_WRITE_ACCESS_CODE,
        CONF_MODEL: MODEL,
        CONF_DETECTED_SENSORS: DETECTED_SENSORS,
    }


async def _setup(
    hass: HomeAssistant,
    provider: MockProvider,
) -> MockConfigEntry:
    """Set up one TROVIS config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        data=_entry_data(provider),
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    return entry


async def test_setup_entry_creates_entities(
    hass: HomeAssistant,
    modbus_provider: MockProvider,
) -> None:
    """Set up entities from the unit supplied by Modbus Connection."""
    entry = await _setup(hass, modbus_provider)

    assert entry.state is ConfigEntryState.LOADED

    outside = hass.states.get(f"sensor.{SLUG}_outside_temperature_1")
    assert outside is not None
    assert float(outside.state) == pytest.approx(12.3)

    pump = hass.states.get(f"binary_sensor.{SLUG}_rk1_pump_running")
    assert pump is not None
    assert pump.state == "on"

    climate = hass.states.get(f"climate.{SLUG}_rk1")
    assert climate is not None
    assert climate.state == "auto"
    assert climate.attributes["temperature"] == pytest.approx(21.0)

    water_heater = hass.states.get(f"water_heater.{SLUG}_rk4dhw")
    assert water_heater is not None
    assert water_heater.attributes["temperature"] == pytest.approx(50.0)
    assert water_heater.attributes["current_temperature"] == pytest.approx(45.0)


async def test_subdevices_are_linked_to_controller(
    hass: HomeAssistant,
    modbus_provider: MockProvider,
) -> None:
    """Link circuits, hot water and measurements to the controller."""
    entry = await _setup(hass, modbus_provider)
    registry = dr.async_get(hass)

    controller = registry.async_get_device({(DOMAIN, entry.entry_id)})
    assert controller is not None

    circuit_1 = registry.async_get_device({(DOMAIN, f"{entry.entry_id}_rk1")})
    assert circuit_1 is not None
    assert circuit_1.via_device_id == controller.id

    hot_water = registry.async_get_device({(DOMAIN, f"{entry.entry_id}_rk4dhw")})
    assert hot_water is not None
    assert hot_water.via_device_id == controller.id

    measurements = registry.async_get_device(
        {(DOMAIN, f"{entry.entry_id}_measurements")}
    )
    assert measurements is not None
    assert measurements.via_device_id == controller.id


async def test_register_and_coil_writes(
    hass: HomeAssistant,
    modbus_provider: MockProvider,
) -> None:
    """Write a register and a coil through Home Assistant entities."""
    entry = await _setup(hass, modbus_provider)

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": f"switch.{SLUG}_write_access"},
        blocking=True,
    )

    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": f"number.{SLUG}_year",
            "value": 2027,
        },
        blocking=True,
    )

    # The write itself happens immediately. The coordinator refresh requested
    # by the entity may be debounced because write access was enabled directly
    # beforehand.
    assert modbus_provider.unit.holding[101] == 2027

    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    year = hass.states.get(f"number.{SLUG}_year")
    assert year is not None
    assert float(year.state) == pytest.approx(2027)

    coils_before = dict(modbus_provider.unit.coils)

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": (f"switch.{SLUG}_automatic_daylight_saving_time")},
        blocking=True,
    )

    assert modbus_provider.unit.coils != coils_before

    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    daylight_saving = hass.states.get(f"switch.{SLUG}_automatic_daylight_saving_time")
    assert daylight_saving is not None
    assert daylight_saving.state == "on"


async def test_config_flow_uses_existing_connection(
    hass: HomeAssistant,
    modbus_provider: MockProvider,
) -> None:
    """Probe a controller through an existing provider config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_CONNECTION_ENTRY_ID: modbus_provider.entry.entry_id,
            CONF_UNIT_ID: UNIT_ID,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "device"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Living room controller",
            CONF_SLUG: "living_room_trovis",
            CONF_ACCESS_CODE: DEFAULT_WRITE_ACCESS_CODE,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Living room controller"
    assert result["data"][CONF_CONNECTION_ENTRY_ID] == modbus_provider.entry.entry_id
    assert result["data"][CONF_UNIT_ID] == UNIT_ID
    assert result["data"][CONF_MODEL] == MODEL
    assert result["data"][CONF_SLUG] == "living_room_trovis"


async def test_config_flow_cannot_get_unit(
    hass: HomeAssistant,
    modbus_provider: MockProvider,
) -> None:
    """Show a connection error when the provider has no matching unit."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_CONNECTION_ENTRY_ID: modbus_provider.entry.entry_id,
            CONF_UNIT_ID: UNIT_ID + 1,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}
