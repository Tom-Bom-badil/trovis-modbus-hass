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
    "sf3",
    "fg1",
    "fg2",
    "fg3",
    "pulse_rate",
    "analog_input_voltage",
    "summer_outdoor_temperature_average",
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

    outdoor_temperature = hass.states.get(f"sensor.{SLUG}_sensor_af1")
    assert outdoor_temperature is not None
    assert float(outdoor_temperature.state) == pytest.approx(12.3)

    system = hass.states.get(f"sensor.{SLUG}_system_code")
    assert system is not None
    assert float(system.state) == pytest.approx(2.1)
    assert hass.states.get(f"number.{SLUG}_system_code") is None

    sf3 = hass.states.get(f"sensor.{SLUG}_sensor_sf3")
    fg1 = hass.states.get(f"sensor.{SLUG}_sensor_fg1")
    fg2 = hass.states.get(f"sensor.{SLUG}_sensor_fg2")
    fg3 = hass.states.get(f"sensor.{SLUG}_sensor_fg3")

    # SF3, FG3, analog input and IMP are alternative views of the same
    # configurable input on TROVIS 5579. The test fixture selects FG3, so
    # the other alternative views must remain hidden.
    assert sf3 is None
    assert fg3 is not None
    assert float(fg3.state) == pytest.approx(1.5)
    assert "unit_of_measurement" not in fg3.attributes

    assert fg1 is not None
    assert fg2 is not None
    assert float(fg1.state) == pytest.approx(95.2)
    assert float(fg2.state) == pytest.approx(325.0)
    assert "unit_of_measurement" not in fg1.attributes
    assert "unit_of_measurement" not in fg2.attributes

    active_room_setpoint = hass.states.get(f"sensor.{SLUG}_rk1_room_setpoint_active")
    assert active_room_setpoint is not None
    assert float(active_room_setpoint.state) == pytest.approx(21.0)

    active_rk4_setpoint = hass.states.get(f"sensor.{SLUG}_rk4_setpoint_active")
    assert active_rk4_setpoint is not None
    assert float(active_rk4_setpoint.state) == pytest.approx(50.0)

    rk4_min = hass.states.get(f"number.{SLUG}_rk4_setpoint_min")
    rk4_max = hass.states.get(f"number.{SLUG}_rk4_setpoint_max")
    assert rk4_min is not None
    assert rk4_max is not None
    assert float(rk4_min.state) == pytest.approx(45.0)
    assert float(rk4_max.state) == pytest.approx(60.0)

    controller_date = hass.states.get(f"date.{SLUG}_controller_date")
    controller_time = hass.states.get(f"time.{SLUG}_controller_time")
    disinfection_start = hass.states.get(f"time.{SLUG}_rk4_disinfection_start")
    disinfection_stop = hass.states.get(f"time.{SLUG}_rk4_disinfection_stop")
    assert controller_date is not None
    assert controller_date.state == "2026-06-21"
    assert controller_time is not None
    assert controller_time.state == "14:30:00"
    assert disinfection_start is not None
    assert disinfection_start.state == "19:00:00"
    assert disinfection_stop is not None
    assert disinfection_stop.state == "21:00:00"

    summer_start = hass.states.get(f"sensor.{SLUG}_summer_start")
    summer_end = hass.states.get(f"sensor.{SLUG}_summer_end")
    assert summer_start is not None
    assert summer_start.state == "05-15"
    assert summer_start.attributes["month"] == 5
    assert summer_start.attributes["day"] == 15
    assert summer_end is not None
    assert summer_end.state == "09-15"

    analog_input = hass.states.get(f"sensor.{SLUG}_sensor_ae_voltage")
    pulse_rate = hass.states.get(f"sensor.{SLUG}_sensor_imp")
    assert analog_input is None
    assert pulse_rate is None

    flow_setpoint = hass.states.get(f"sensor.{SLUG}_rk1_flow_setpoint")
    return_flow_temperature_setpoint = hass.states.get(
        f"sensor.{SLUG}_rk1_return_flow_temperature_setpoint"
    )
    assert flow_setpoint is not None
    assert float(flow_setpoint.state) == pytest.approx(55.0)
    assert return_flow_temperature_setpoint is not None
    assert float(return_flow_temperature_setpoint.state) == pytest.approx(45.0)

    minimum_flow_temperature = hass.states.get(
        f"number.{SLUG}_rk1_minimum_flow_temperature"
    )
    return_flow_gradient = hass.states.get(f"number.{SLUG}_rk1_return_flow_gradient")
    return_flow_level = hass.states.get(f"number.{SLUG}_rk1_return_flow_level")
    return_flow_base_point = hass.states.get(
        f"number.{SLUG}_rk1_return_flow_base_point"
    )
    maximum_return_flow_temperature = hass.states.get(
        f"number.{SLUG}_rk1_maximum_return_flow_temperature"
    )
    assert minimum_flow_temperature is not None
    assert float(minimum_flow_temperature.state) == pytest.approx(20.0)
    assert return_flow_gradient is not None
    assert float(return_flow_gradient.state) == pytest.approx(0.5)
    assert return_flow_level is not None
    assert float(return_flow_level.state) == pytest.approx(2.0)
    assert return_flow_base_point is not None
    assert float(return_flow_base_point.state) == pytest.approx(30.0)
    assert maximum_return_flow_temperature is not None
    assert float(maximum_return_flow_temperature.state) == pytest.approx(55.0)
    for field in (
        "return_flow_gradient",
        "return_flow_level",
        "return_flow_base_point",
    ):
        assert hass.states.get(f"sensor.{SLUG}_rk1_{field}") is None
    assert hass.states.get(f"number.{SLUG}_rk1_fixed_setpoint_day") is None
    assert hass.states.get(f"number.{SLUG}_rk1_fixed_setpoint_night") is None
    assert (
        hass.states.get(f"number.{SLUG}_rk1_four_point_outdoor_temperature_1") is None
    )

    operating_mode = hass.states.get(f"sensor.{SLUG}_rk1_operating_mode")
    heating_curves = hass.states.get(f"sensor.{SLUG}_rk1_heating_curves")
    assert operating_mode is not None
    assert operating_mode.state == "heating_curve"
    assert heating_curves is not None
    assert heating_curves.state == "1"
    assert heating_curves.attributes["x_values"] == list(range(-20, 21))
    assert heating_curves.attributes["flow_curve"][0] == pytest.approx(78.32)
    assert heating_curves.attributes["flow_curve"][20] == pytest.approx(57.08)
    assert heating_curves.attributes["flow_curve"][-1] == pytest.approx(26.4)
    assert (
        heating_curves.attributes["flow_curve_day"]
        == (heating_curves.attributes["flow_curve"])
    )
    assert heating_curves.attributes["flow_curve_night"][0] == pytest.approx(71.12)
    assert heating_curves.attributes["flow_curve_night"][20] == pytest.approx(49.88)
    assert heating_curves.attributes["flow_curve_night"][-1] == pytest.approx(20.0)
    assert heating_curves.attributes["return_curve"][0] == pytest.approx(55.0)
    assert heating_curves.attributes["return_curve"][20] == pytest.approx(47.3)
    assert heating_curves.attributes["return_curve"][-1] == pytest.approx(33.0)
    assert (
        heating_curves.attributes["return_curve_day"]
        == (heating_curves.attributes["return_curve"])
    )
    assert heating_curves.attributes["return_curve_night"][0] == pytest.approx(54.2)
    assert heating_curves.attributes["return_curve_night"][20] == pytest.approx(44.3)
    assert heating_curves.attributes["return_curve_night"][-1] == pytest.approx(30.0)

    storage_status = hass.states.get(f"sensor.{SLUG}_rk4_storage_status")
    assert storage_status is not None
    assert storage_status.state == "charging"
    assert hass.states.get(f"sensor.{SLUG}_rk4_solar_operating_hours") is None
    assert hass.states.get(f"sensor.{SLUG}_solar_operating_hours") is None

    disinfection_weekday = hass.states.get(f"select.{SLUG}_rk4_disinfection_weekday")
    assert disinfection_weekday is not None
    assert disinfection_weekday.state == "wednesday"

    pump = hass.states.get(f"binary_sensor.{SLUG}_rk1_pump_running")
    assert pump is not None
    assert pump.state == "on"

    automatic = hass.states.get(f"binary_sensor.{SLUG}_rk1_automatic")
    valve_opening = hass.states.get(f"binary_sensor.{SLUG}_rk1_valve_opening")
    rk4_priority = hass.states.get(f"binary_sensor.{SLUG}_rk4_priority")
    assert automatic is not None
    assert automatic.state == "on"
    assert valve_opening is not None
    assert valve_opening.state == "on"
    assert rk4_priority is not None
    assert rk4_priority.state == "on"

    manual_lock = hass.states.get(f"switch.{SLUG}_manual_levels_locked")
    storage_enabled = hass.states.get(
        f"switch.{SLUG}_rk4_storage_tank_charging_enabled"
    )
    heating_pump = hass.states.get(f"switch.{SLUG}_rk1_pump_control")
    storage_tank_charging_pump = hass.states.get(
        f"switch.{SLUG}_rk4_storage_tank_charging_pump_control"
    )
    circulation_pump = hass.states.get(f"switch.{SLUG}_rk4_circulation_pump_control")
    assert manual_lock is not None
    assert manual_lock.state == "off"
    assert storage_enabled is not None
    assert storage_enabled.state == "on"
    assert heating_pump is not None
    assert heating_pump.state == "on"
    assert storage_tank_charging_pump is not None
    assert storage_tank_charging_pump.state == "on"
    assert circulation_pump is not None
    assert circulation_pump.state == "off"

    climate = hass.states.get(f"climate.{SLUG}_rk1")
    assert climate is not None
    assert climate.state == "auto"
    assert climate.attributes["temperature"] == pytest.approx(21.0)

    water_heater = hass.states.get(f"water_heater.{SLUG}_rk4")
    assert water_heater is not None
    assert water_heater.attributes["temperature"] == pytest.approx(50.0)
    assert water_heater.attributes["current_temperature"] == pytest.approx(45.0)

    # Step 5 is a deliberate beta identity cut: no legacy Hk/WW IDs remain.
    assert hass.states.get(f"sensor.{SLUG}_hk1_flow_setpoint") is None
    assert hass.states.get(f"sensor.{SLUG}_ww_setpoint_active") is None
    assert hass.states.get(f"climate.{SLUG}_hk1") is None
    assert hass.states.get(f"water_heater.{SLUG}_ww") is None


async def test_fixed_setpoint_control_uses_fixed_flow_setpoints(
    hass: HomeAssistant,
    modbus_provider: MockProvider,
) -> None:
    """Expose fixed flow setpoints instead of heating-curve controls."""
    modbus_provider.unit.coils[1025] = False  # CL1026 / CO1 -> F02 disabled

    await _setup(hass, modbus_provider)

    fixed_day = hass.states.get(f"number.{SLUG}_rk1_fixed_setpoint_day")
    fixed_night = hass.states.get(f"number.{SLUG}_rk1_fixed_setpoint_night")
    assert fixed_day is not None
    assert float(fixed_day.state) == pytest.approx(60.0)
    assert fixed_night is not None
    assert float(fixed_night.state) == pytest.approx(50.0)

    for field in (
        "room_setpoint_day",
        "room_setpoint_night",
        "gradient",
        "level",
        "four_point_outdoor_temperature_1",
    ):
        assert hass.states.get(f"number.{SLUG}_rk1_{field}") is None

    assert hass.states.get(f"number.{SLUG}_rk1_minimum_flow_temperature") is not None
    assert hass.states.get(f"number.{SLUG}_rk1_maximum_flow_temperature") is not None
    assert (
        hass.states.get(f"number.{SLUG}_rk1_maximum_return_flow_temperature")
        is not None
    )
    assert hass.states.get(f"sensor.{SLUG}_rk1_flow_setpoint") is not None
    assert hass.states.get(f"sensor.{SLUG}_rk1_room_setpoint_active") is not None
    assert hass.states.get(f"climate.{SLUG}_rk1") is None

    operating_mode = hass.states.get(f"sensor.{SLUG}_rk1_operating_mode")
    heating_curves = hass.states.get(f"sensor.{SLUG}_rk1_heating_curves")
    assert operating_mode is not None
    assert operating_mode.state == "fixed_setpoint"
    assert heating_curves is not None
    assert heating_curves.state == "1"
    assert heating_curves.attributes["x_values"] == list(range(-20, 21))
    assert heating_curves.attributes["flow_curve"] == [60.0] * 41
    assert heating_curves.attributes["flow_curve_day"] == [60.0] * 41
    assert heating_curves.attributes["flow_curve_night"] == [50.0] * 41
    assert heating_curves.attributes["return_curve"] == [45.0] * 41
    assert heating_curves.attributes["return_curve_day"] == [45.0] * 41
    assert heating_curves.attributes["return_curve_night"] == [45.0] * 41


async def test_four_point_characteristic_uses_four_point_parameters(
    hass: HomeAssistant,
    modbus_provider: MockProvider,
) -> None:
    """Expose four-point values instead of gradient or fixed controls."""
    modbus_provider.unit.coils[1034] = True  # CL1035 / CO1 -> F11 enabled

    await _setup(hass, modbus_provider)

    expected_values = {
        "four_point_outdoor_temperature_1": -15.0,
        "four_point_outdoor_temperature_4": 15.0,
        "four_point_flow_temperature_day_1": 70.0,
        "four_point_flow_temperature_day_4": 25.0,
        "four_point_flow_temperature_night_1": 60.0,
        "four_point_flow_temperature_night_4": 20.0,
        "four_point_return_flow_temperature_1": 65.0,
        "four_point_return_flow_temperature_4": 65.0,
    }
    for field, expected in expected_values.items():
        state = hass.states.get(f"number.{SLUG}_rk1_{field}")
        assert state is not None
        assert float(state.state) == pytest.approx(expected)

    for prefix in (
        "four_point_outdoor_temperature",
        "four_point_flow_temperature_day",
        "four_point_flow_temperature_night",
        "four_point_return_flow_temperature",
    ):
        for point in range(1, 5):
            assert hass.states.get(f"number.{SLUG}_rk1_{prefix}_{point}") is not None

    for field in (
        "room_setpoint_day",
        "room_setpoint_night",
        "gradient",
        "level",
        "fixed_setpoint_day",
        "fixed_setpoint_night",
    ):
        assert hass.states.get(f"number.{SLUG}_rk1_{field}") is None

    assert hass.states.get(f"number.{SLUG}_rk1_minimum_flow_temperature") is not None
    assert hass.states.get(f"number.{SLUG}_rk1_maximum_flow_temperature") is not None
    assert hass.states.get(f"sensor.{SLUG}_rk1_flow_setpoint") is not None
    assert hass.states.get(f"sensor.{SLUG}_rk1_room_setpoint_active") is not None
    assert hass.states.get(f"climate.{SLUG}_rk1") is None

    operating_mode = hass.states.get(f"sensor.{SLUG}_rk1_operating_mode")
    heating_curves = hass.states.get(f"sensor.{SLUG}_rk1_heating_curves")
    assert operating_mode is not None
    assert operating_mode.state == "four_point"
    assert heating_curves is not None
    assert heating_curves.state == "1"
    assert heating_curves.attributes["x_values"] == list(range(-20, 21))
    assert heating_curves.attributes["flow_curve"][0] == pytest.approx(70.0)
    assert heating_curves.attributes["flow_curve"][5] == pytest.approx(70.0)
    assert heating_curves.attributes["flow_curve"][-1] == pytest.approx(25.0)
    assert (
        heating_curves.attributes["flow_curve_day"]
        == (heating_curves.attributes["flow_curve"])
    )
    assert heating_curves.attributes["flow_curve_night"][0] == pytest.approx(60.0)
    assert heating_curves.attributes["flow_curve_night"][5] == pytest.approx(60.0)
    assert heating_curves.attributes["flow_curve_night"][-1] == pytest.approx(20.0)
    assert heating_curves.attributes["return_curve"] == [65.0] * 41
    assert heating_curves.attributes["return_curve_day"] == [65.0] * 41
    assert heating_curves.attributes["return_curve_night"] == [65.0] * 41


async def test_invalid_four_point_curve_reports_calculation_error(
    hass: HomeAssistant,
    modbus_provider: MockProvider,
) -> None:
    """Expose state 0 and no curve attributes for invalid four-point data."""
    modbus_provider.unit.coils[1034] = True
    modbus_provider.unit.holding[1013] = 0xFF6A  # P2 duplicates P1

    await _setup(hass, modbus_provider)

    operating_mode = hass.states.get(f"sensor.{SLUG}_rk1_operating_mode")
    heating_curves = hass.states.get(f"sensor.{SLUG}_rk1_heating_curves")
    assert operating_mode is not None
    assert operating_mode.state == "four_point"
    assert heating_curves is not None
    assert heating_curves.state == "0"
    for attribute in (
        "x_values",
        "flow_curve",
        "flow_curve_day",
        "flow_curve_night",
        "return_curve",
        "return_curve_day",
        "return_curve_night",
    ):
        assert attribute not in heating_curves.attributes


async def test_subdevices_are_linked_to_controller(
    hass: HomeAssistant,
    modbus_provider: MockProvider,
) -> None:
    """Link circuits, domestic hot water and measurements to the controller."""
    entry = await _setup(hass, modbus_provider)
    registry = dr.async_get(hass)

    controller = registry.async_get_device({(DOMAIN, entry.entry_id)})
    assert controller is not None

    circuit_1 = registry.async_get_device({(DOMAIN, f"{entry.entry_id}_rk1")})
    assert circuit_1 is not None
    assert circuit_1.via_device_id == controller.id

    rk4 = registry.async_get_device({(DOMAIN, f"{entry.entry_id}_rk4")})
    assert rk4 is not None
    assert rk4.via_device_id == controller.id

    measurements = registry.async_get_device(
        {(DOMAIN, f"{entry.entry_id}_measurements")}
    )
    assert measurements is not None
    assert measurements.via_device_id == controller.id

    solar = registry.async_get_device({(DOMAIN, f"{entry.entry_id}_solar")})
    assert solar is None


async def test_solar_system_creates_dedicated_solar_device_and_entities(
    hass: HomeAssistant,
    modbus_provider: MockProvider,
) -> None:
    """Expose solar datapoints only for a hydronic system with solar."""
    modbus_provider.unit.holding[1] = 23  # Anlage 2.3

    entry = await _setup(hass, modbus_provider)

    operating_hours = hass.states.get(f"sensor.{SLUG}_solar_operating_hours")
    pump = hass.states.get(f"binary_sensor.{SLUG}_solar_pump_running")
    pump_on = hass.states.get(f"number.{SLUG}_solar_pump_on_temperature_difference")
    pump_off = hass.states.get(f"number.{SLUG}_solar_pump_off_temperature_difference")
    maximum_storage = hass.states.get(
        f"number.{SLUG}_solar_maximum_storage_temperature"
    )

    assert operating_hours is not None
    assert float(operating_hours.state) == pytest.approx(1234)
    assert pump is not None
    assert pump.state == "on"
    assert pump_on is not None
    assert float(pump_on.state) == pytest.approx(10.0)
    assert pump_off is not None
    assert float(pump_off.state) == pytest.approx(3.0)
    assert maximum_storage is not None
    assert float(maximum_storage.state) == pytest.approx(80.0)

    assert hass.states.get(f"sensor.{SLUG}_rk4_solar_operating_hours") is None
    assert (
        hass.states.get(f"binary_sensor.{SLUG}_rk4_solar_circuit_pump_running") is None
    )

    registry = dr.async_get(hass)
    controller = registry.async_get_device({(DOMAIN, entry.entry_id)})
    solar = registry.async_get_device({(DOMAIN, f"{entry.entry_id}_solar")})
    assert controller is not None
    assert solar is not None
    assert solar.name == "Solar – Solar circuit"
    assert solar.via_device_id == controller.id


async def test_rk_subdevices_use_hydronic_roles(
    hass: HomeAssistant,
    modbus_provider: MockProvider,
) -> None:
    """Name active Rk devices from their hydronic role."""
    modbus_provider.unit.holding[1] = 51  # Anlage 5.1

    entry = await _setup(hass, modbus_provider)
    registry = dr.async_get(hass)

    rk1 = registry.async_get_device({(DOMAIN, f"{entry.entry_id}_rk1")})
    rk2 = registry.async_get_device({(DOMAIN, f"{entry.entry_id}_rk2")})
    rk3 = registry.async_get_device({(DOMAIN, f"{entry.entry_id}_rk3")})
    rk4 = registry.async_get_device({(DOMAIN, f"{entry.entry_id}_rk4")})

    assert rk1 is not None
    assert rk1.name == "Rk1 – Precontrol circuit"
    assert rk2 is not None
    assert rk2.name == "Rk2 – Heating circuit 2"
    assert rk3 is not None
    assert rk3.name == "Rk3 – Heating circuit 3"
    assert rk4 is not None
    assert rk4.name == "Rk4 – Domestic hot water"

    assert hass.states.get(f"climate.{SLUG}_rk1") is None
    assert hass.states.get(f"climate.{SLUG}_rk2") is not None
    assert hass.states.get(f"climate.{SLUG}_rk3") is not None


async def test_system_without_rk4_omits_rk4_entities_and_device(
    hass: HomeAssistant,
    modbus_provider: MockProvider,
) -> None:
    """Do not expose Rk4 entities for a hydronic system without hot water."""
    modbus_provider.unit.holding[1] = 10  # hydraulic system / Anlage 1.0

    entry = await _setup(hass, modbus_provider)

    assert entry.runtime_data.device.has_rk4 is False

    assert hass.states.get(f"sensor.{SLUG}_rk4_setpoint_active") is None
    assert hass.states.get(f"binary_sensor.{SLUG}_rk4_priority") is None
    assert hass.states.get(f"number.{SLUG}_rk4_setpoint") is None
    assert hass.states.get(f"select.{SLUG}_rk4_operation_mode") is None
    assert hass.states.get(f"switch.{SLUG}_rk4_storage_tank_charging_enabled") is None
    assert hass.states.get(f"time.{SLUG}_rk4_disinfection_start") is None
    assert hass.states.get(f"water_heater.{SLUG}_rk4") is None

    registry = dr.async_get(hass)
    assert registry.async_get_device({(DOMAIN, f"{entry.entry_id}_rk4")}) is None

    # Physical sensor entities stay on the Measurements sub-device and are
    # intentionally independent of the Rk4 role.
    assert hass.states.get(f"sensor.{SLUG}_sensor_sf1") is not None


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
        {"entity_id": (f"switch.{SLUG}_automatic_summer_standard_time_switchover")},
        blocking=True,
    )

    assert modbus_provider.unit.coils != coils_before

    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    daylight_saving = hass.states.get(
        f"switch.{SLUG}_automatic_summer_standard_time_switchover"
    )
    assert daylight_saving is not None
    assert daylight_saving.state == "on"

    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": f"number.{SLUG}_rk1_maximum_flow_temperature",
            "value": 75.0,
        },
        blocking=True,
    )
    assert modbus_provider.unit.holding[1000] == 750

    await hass.services.async_call(
        "number",
        "set_value",
        {
            "entity_id": f"number.{SLUG}_rk1_return_flow_gradient",
            "value": 0.7,
        },
        blocking=True,
    )
    assert modbus_provider.unit.holding[1008] == 7

    await hass.services.async_call(
        "select",
        "select_option",
        {
            "entity_id": f"select.{SLUG}_rk4_disinfection_weekday",
            "option": "friday",
        },
        blocking=True,
    )
    assert modbus_provider.unit.holding[1830] == 5

    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": f"switch.{SLUG}_rk4_storage_tank_charging_enabled"},
        blocking=True,
    )
    assert modbus_provider.unit.coils[1810] is False

    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": f"switch.{SLUG}_rk1_pump_control"},
        blocking=True,
    )
    assert modbus_provider.unit.coils[56] is False


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


async def test_buffer_tank_system_adds_rk1_buffer_entities(
    hass: HomeAssistant,
    modbus_provider: MockProvider,
) -> None:
    """Add buffer-tank extensions to the role-aware Rk1 sub-device."""
    modbus_provider.unit.holding[1] = 161  # Anlage 16.1

    entry = await _setup(hass, modbus_provider)

    assert entry.runtime_data.device.has_buffer_tank_circuit is True

    status = hass.states.get(f"sensor.{SLUG}_rk1_buffer_tank_status")
    minimum = hass.states.get(
        f"number.{SLUG}_rk1_buffer_tank_minimum_charging_setpoint"
    )
    charging_end = hass.states.get(
        f"number.{SLUG}_rk1_buffer_tank_charging_end_temperature"
    )
    boost = hass.states.get(f"number.{SLUG}_rk1_buffer_tank_charging_temperature_boost")
    lag = hass.states.get(f"number.{SLUG}_rk1_buffer_tank_charging_pump_lag_factor")

    assert status is not None
    assert status.state == "charging"
    assert minimum is not None
    assert float(minimum.state) == pytest.approx(0.0)
    assert charging_end is not None
    assert float(charging_end.state) == pytest.approx(0.0)
    assert boost is not None
    assert float(boost.state) == pytest.approx(6.0)
    assert lag is not None
    assert float(lag.state) == pytest.approx(1.0)

    registry = dr.async_get(hass)
    rk1 = registry.async_get_device({(DOMAIN, f"{entry.entry_id}_rk1")})
    assert rk1 is not None
    assert rk1.name == "Rk1 – Buffer tank circuit"
    assert (
        registry.async_get_device({(DOMAIN, f"{entry.entry_id}_buffer_tank")}) is None
    )

    assert hass.states.get(f"climate.{SLUG}_rk1") is None


async def test_fixed_loading_buffer_system_adds_status_without_pa1_p16_to_p19(
    hass: HomeAssistant,
    modbus_provider: MockProvider,
) -> None:
    """Expose buffer status but not unsupported charging parameters for 14.1."""
    modbus_provider.unit.holding[1] = 141  # Anlage 14.1

    entry = await _setup(hass, modbus_provider)

    assert entry.runtime_data.device.has_buffer_tank_circuit is True
    assert entry.runtime_data.device.has_buffer_tank_charging_parameters is False
    assert hass.states.get(f"sensor.{SLUG}_rk1_buffer_tank_status") is not None
    assert (
        hass.states.get(f"number.{SLUG}_rk1_buffer_tank_minimum_charging_setpoint")
        is None
    )
    assert (
        hass.states.get(f"number.{SLUG}_rk1_buffer_tank_charging_temperature_boost")
        is None
    )


async def test_non_buffer_system_omits_buffer_tank_entities(
    hass: HomeAssistant,
    modbus_provider: MockProvider,
) -> None:
    """Do not add buffer-tank extensions to a normal heating circuit."""
    modbus_provider.unit.holding[1] = 21  # Anlage 2.1

    await _setup(hass, modbus_provider)

    assert hass.states.get(f"sensor.{SLUG}_rk1_buffer_tank_status") is None
    assert (
        hass.states.get(f"number.{SLUG}_rk1_buffer_tank_charging_temperature_boost")
        is None
    )


async def test_buffer_tank_number_write(
    hass: HomeAssistant,
    modbus_provider: MockProvider,
) -> None:
    """Write a buffer-tank PA1 value through the Rk1 sub-device."""
    modbus_provider.unit.holding[1] = 161  # Anlage 16.1
    await _setup(hass, modbus_provider)

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
            "entity_id": (f"number.{SLUG}_rk1_buffer_tank_charging_temperature_boost"),
            "value": 7.5,
        },
        blocking=True,
    )

    assert modbus_provider.unit.holding[1101] == 75
