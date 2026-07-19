"""Fixtures for TROVIS tests over an in-memory shared Modbus unit."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Final

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    mock_integration,
    mock_platform,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


MODBUS_CONNECTION_DOMAIN: Final = "modbus_connection"
UNIT_ID: Final = 247

_PROVIDER_UNITS: Final = "test_modbus_connection_units"


def _async_get_unit(
    hass: HomeAssistant,
    connection_entry_id: str,
    unit_id: int,
) -> MockModbusUnit:
    """Return the unit registered for a test provider entry."""
    units = hass.data.get(_PROVIDER_UNITS, {})

    try:
        return units[(connection_entry_id, unit_id)]
    except KeyError as err:
        raise ConfigEntryNotReady("The test Modbus connection is not ready") from err


# The real provider integration is installed separately in Home Assistant.
# GitHub Actions checks out only this repository, so expose the small public
# provider boundary needed by the TROVIS integration during tests.
_provider_module = ModuleType("custom_components.modbus_connection")
_provider_module.async_get_unit = _async_get_unit
sys.modules["custom_components.modbus_connection"] = _provider_module


# Raw Modbus protocol addresses, not manufacturer HR/CL reference numbers.
HOLDING: dict[int, int] = {
    0: 5579,  # controller model
    1: 21,  # hydraulic system / Anlage -> 2.1
    2: 305,  # firmware -> 3.05
    3: 110,  # hardware -> 1.10
    4: 0,  # special functions
    5: 12345,  # serial number
    9: 123,  # AF1 outside temperature -> 12.3 °C
    12: 300,  # VF1 flow temperature -> 30.0 °C
    19: 200,  # RF1 room temperature -> 20.0 °C
    22: 450,  # SF1 storage temperature -> 45.0 °C
    23: 0x7FFF,  # SF2 invalid-value marker
    27: 15,  # AE3/FG3 -> 1.5
    28: 120,  # pulse rate -> 120 Imp/h
    41: 523,  # analog input -> 5.23 V
    42: 175,  # summer outside average -> 17.5 °C
    98: 900,  # maximum flow setpoint -> 90.0 °C
    99: 1430,  # controller time -> 14:30
    100: 2106,  # controller date -> 21.06
    101: 2026,  # controller year
    102: 1,  # upper rotary switch -> automatic
    105: 1,  # Rk1 operation mode -> automatic
    106: 42,  # Rk1 valve setpoint -> 42 %
    112: 1505,  # summer operation start -> 15.05
    113: 1509,  # summer operation end -> 15.09
    114: 2,  # summer activation days
    115: 3,  # summer deactivation days
    116: 180,  # summer outside limit -> 18.0 °C
    117: 25,  # outside-temperature delay -> 2.5 K/h
    120: 20,  # temperature monitoring deviation -> 2.0 K
    121: 30,  # temperature monitoring window -> 30 min
    122: 0xFFE2,  # frost limit -> -3.0 °C
    123: 0xFE0C,  # outside input range start -> -50.0 °C
    124: 500,  # outside input range end -> 50.0 °C
    142: 246,  # station address
    153: 4,  # error count
    149: 0,  # no controller error
    999: 550,  # Rk1 flow setpoint -> 55.0 °C
    1000: 800,  # Rk1 maximum flow temperature -> 80.0 °C
    1001: 200,  # Rk1 minimum flow temperature -> 20.0 °C
    1002: 210,  # Rk1 room setpoint day -> 21.0 °C
    1003: 180,  # Rk1 room setpoint night -> 18.0 °C
    1004: 210,  # Rk1 active room setpoint -> 21.0 °C
    1005: 12,  # Rk1 slope -> 1.2
    1006: 0,  # Rk1 level -> 0.0 K
    1008: 5,  # Rk1 return slope -> 0.5
    1009: 20,  # Rk1 return level -> 2.0 K
    1010: 550,  # Rk1 maximum return temperature -> 55.0 °C
    1011: 300,  # Rk1 return base point -> 30.0 °C
    1032: 450,  # Rk1 return setpoint -> 45.0 °C
    1041: 600,  # Rk1 fixed setpoint day -> 60.0 °C
    1042: 500,  # Rk1 fixed setpoint night -> 50.0 °C
    1062: 0xFFF1,  # Rk1 flow deviation -> -1.5 K
    1199: 480,  # Rk2 flow setpoint -> 48.0 °C
    1799: 500,  # domestic-hot-water setpoint -> 50.0 °C
    1800: 600,  # domestic-hot-water maximum -> 60.0 °C
    1801: 450,  # domestic-hot-water minimum -> 45.0 °C
    1802: 50,  # domestic-hot-water hysteresis -> 5.0 K
    1803: 100,  # domestic-hot-water charge overshoot -> 10.0 K
    1804: 15,  # charge-pump overrun factor -> 1.5
    1805: 750,  # maximum charge temperature -> 75.0 °C
    1807: 500,  # active domestic-hot-water setpoint -> 50.0 °C
    1808: 600,  # special domestic-hot-water setpoint -> 60.0 °C
    1812: 1234,  # solar operating hours
    1826: 4,  # storage status -> charging
    1827: 550,  # domestic-hot-water maximum return -> 55.0 °C
    1829: 700,  # disinfection temperature -> 70.0 °C
    1830: 3,  # disinfection weekday -> Wednesday
    1831: 1900,  # disinfection start -> 19:00
    1832: 2100,  # disinfection end -> 21:00
    1837: 670,  # active charge setpoint -> 67.0 °C
    1838: 20,  # disinfection hold time -> 20 min
    1862: 0xFFF6,  # domestic-hot-water control deviation -> -1.0 K
}

COILS: dict[int, bool] = {
    1: True,  # data entry active
    2: True,  # data entry performed
    3: True,  # controller initially operates autonomously
    4: False,  # Rk1 manual operation
    61: False,  # Rk1 valve closing
    62: True,  # Rk1 valve opening
    87: True,  # outside-temperature control autonomous
    88: True,  # Rk1 mode control autonomous
    89: True,  # Rk1 valve control autonomous
    95: True,  # Rk1 pump control autonomous
    115: True,  # Rk1 flow-setpoint control autonomous
    116: True,  # Rk1 return-setpoint control autonomous
    121: True,  # Rk1 room-setpoint control autonomous
    149: False,  # manual-operation levels not locked
    150: False,  # rotary switches not locked
    158: False,  # supervisory-system timeout inactive
    56: True,  # Rk1 pump running
    59: True,  # domestic-hot-water charge pump running
    7: False,  # domestic-hot-water manual operation
    94: True,  # domestic-hot-water mode control autonomous
    98: True,  # charge-pump control autonomous
    99: True,  # circulation-pump control autonomous
    111: True,  # special-setpoint control autonomous
    999: True,  # Rk1 automatic mode
    1000: True,  # Rk1 day mode active
    1799: True,  # domestic hot water automatic mode
    1801: True,  # domestic-hot-water priority
    1802: False,  # max charge-temperature limit inactive
    1803: False,  # return-temperature limit inactive
    1806: False,  # forced charge inactive
    1807: True,  # solar pump running
    1808: False,  # forced charge uses sensor 1
    1809: True,  # storage charging active
    1810: True,  # storage charging enabled
    1811: False,  # storage charging not locked
}


@dataclass(frozen=True)
class MockProvider:
    """A configured Modbus Connection provider and its shared unit."""

    entry: MockConfigEntry
    unit: MockModbusUnit


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):  # noqa: ANN001
    """Allow loading the custom TROVIS integration."""
    yield


async def _async_setup_provider_entry(
    _hass: HomeAssistant,
    _entry: ConfigEntry,
) -> bool:
    """Set up the simulated Modbus Connection entry."""
    return True


@pytest.fixture
def modbus_provider(hass: HomeAssistant) -> MockProvider:
    """Provide one enabled Modbus Connection entry and a TROVIS-shaped unit."""
    # Register the provider with Home Assistant's integration loader. The
    # sys.modules stub above supplies async_get_unit to the TROVIS code, while
    # this loader mock satisfies the manifest dependency.
    mock_integration(
        hass,
        MockModule(
            MODBUS_CONNECTION_DOMAIN,
            async_setup_entry=_async_setup_provider_entry,
        ),
        built_in=False,
    )
    mock_platform(
        hass,
        f"{MODBUS_CONNECTION_DOMAIN}.config_flow",
        None,
    )

    entry = MockConfigEntry(
        domain=MODBUS_CONNECTION_DOMAIN,
        title="Test Modbus Connection",
    )
    entry.add_to_hass(hass)

    connection = MockModbusConnection()
    unit = connection.for_unit(UNIT_ID)
    unit.holding.update(HOLDING)
    unit.coils.update(COILS)

    hass.data.setdefault(_PROVIDER_UNITS, {})[(entry.entry_id, UNIT_ID)] = unit

    return MockProvider(entry=entry, unit=unit)
