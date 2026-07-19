"""Tests for package boundaries, manifest and translations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from modbus_connection.mock import MockModbusConnection
from trovis_modbus import OperatingMode, Trovis557x

from .conftest import COILS, HOLDING, UNIT_ID

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "trovis557x"


async def test_library_stack_with_mock_unit() -> None:
    """Use the same ModbusUnit boundary as the Home Assistant integration."""
    connection = MockModbusConnection()
    unit = connection.for_unit(UNIT_ID)
    unit.holding.update(HOLDING)
    unit.coils.update(COILS)

    probe = await Trovis557x.async_probe(unit)

    assert probe.model == 5579

    device = Trovis557x(
        unit,
        model=probe.model,
        detected_sensors=probe.detected_sensors,
    )
    await device.async_update()

    assert device.info.model == "Trovis 5579"
    assert device.sensors.af1 == pytest.approx(12.3)
    assert device.heating_circuit_1.pump_running is True
    assert device.heating_circuit_1.mode is OperatingMode.AUTOMATIC
    assert device.hot_water.setpoint_active == pytest.approx(50.0)


def test_manifest_valid() -> None:
    """Declare the provider integration without owning its backend."""
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["domain"] == "trovis557x"
    assert manifest["config_flow"] is True
    assert "modbus_connection" in manifest["dependencies"]

    requirements = manifest["requirements"]
    assert "trovis-modbus>=1.1.1,<2" in requirements
    assert not any(
        "modbus-connection" in requirement
        or "tmodbus" in requirement
        or "pymodbus" in requirement
        for requirement in requirements
    )

    assert "trovis_modbus" in manifest["loggers"]


def test_strings_and_translation_valid() -> None:
    """Expose shared-connection setup instead of transport setup."""
    strings = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    english = json.loads(
        (COMPONENT / "translations" / "en.json").read_text(encoding="utf-8")
    )

    steps = strings["config"]["step"]

    assert {"user", "device", "reconfigure"} <= steps.keys()
    assert "network" not in steps
    assert "serial" not in steps

    assert "connection_entry_id" in steps["user"]["data"]
    assert "unit_id" in steps["user"]["data"]

    assert strings == english
