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
    5: 12345,  # serial number
    9: 123,  # AF1 outside temperature -> 12.3 °C
    12: 300,  # VF1 flow temperature -> 30.0 °C
    19: 200,  # RF1 room temperature -> 20.0 °C
    22: 450,  # SF1 storage temperature -> 45.0 °C
    23: 0x7FFF,  # SF2 invalid-value marker
    98: 900,  # maximum flow setpoint -> 90.0 °C
    99: 1430,  # controller time -> 14:30
    100: 2106,  # controller date -> 21.06
    101: 2026,  # controller year
    102: 1,  # upper rotary switch -> automatic
    105: 1,  # Rk1 operation mode -> automatic
    106: 42,  # Rk1 valve setpoint -> 42 %
    112: 1505,  # summer operation start -> 15.05
    149: 0,  # no controller error
    999: 550,  # Rk1 flow setpoint -> 55.0 °C
    1000: 800,  # Rk1 maximum flow temperature -> 80.0 °C
    1001: 200,  # Rk1 minimum flow temperature -> 20.0 °C
    1002: 210,  # Rk1 room setpoint day -> 21.0 °C
    1003: 180,  # Rk1 room setpoint night -> 18.0 °C
    1004: 210,  # Rk1 active room setpoint -> 21.0 °C
    1005: 12,  # Rk1 slope -> 1.2
    1006: 0,  # Rk1 level -> 0.0 K
    1199: 480,  # Rk2 flow setpoint -> 48.0 °C
    1799: 500,  # domestic-hot-water setpoint -> 50.0 °C
    1800: 600,  # domestic-hot-water maximum -> 60.0 °C
    1801: 450,  # domestic-hot-water minimum -> 45.0 °C
    1807: 500,  # active domestic-hot-water setpoint -> 50.0 °C
    1830: 3,  # disinfection weekday -> Wednesday
    1831: 1900,  # disinfection start -> 19:00
    1832: 2100,  # disinfection end -> 21:00
    1837: 670,  # active charge setpoint -> 67.0 °C
}

COILS: dict[int, bool] = {
    3: True,  # controller initially operates autonomously
    56: True,  # Rk1 pump running
    59: True,  # domestic-hot-water charge pump running
    999: True,  # Rk1 automatic mode
    1000: True,  # Rk1 day mode active
    1799: True,  # domestic hot water automatic mode
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
