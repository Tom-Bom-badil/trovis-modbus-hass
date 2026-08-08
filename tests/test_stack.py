"""Tests for package boundaries, manifest and translations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from modbus_connection.mock import MockModbusConnection
from trovis_modbus import OperatingMode, Trovis557x

from custom_components.trovis557x.sensor import _GLOBAL

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

    assert device.info.model == "TROVIS 5579"
    assert device.sensors.af1 == pytest.approx(12.3)
    assert device.rk1.pump_running is True
    assert device.rk1.mode is OperatingMode.AUTOMATIC
    assert device.rk4.setpoint_active == pytest.approx(50.0)


def test_manifest_valid() -> None:
    """Own the Modbus backend as a normal Python requirement."""
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["domain"] == "trovis557x"
    assert manifest["config_flow"] is True
    assert "modbus_connection" not in manifest.get("dependencies", [])

    requirements = manifest["requirements"]
    assert "trovis-modbus>=2.1.0,<3" in requirements
    assert "modbus-connection[tmodbus]>=4.2,<5" in requirements
    assert not any("pymodbus" in requirement for requirement in requirements)

    assert "trovis_modbus" in manifest["loggers"]


def test_strings_and_translation_valid() -> None:
    """Expose the integration-owned network and serial setup flow."""
    strings = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    english = json.loads(
        (COMPONENT / "translations" / "en.json").read_text(encoding="utf-8")
    )

    steps = strings["config"]["step"]

    assert {
        "user",
        "network",
        "serial",
        "device",
        "reconfigure",
        "reconfigure_network",
        "reconfigure_serial",
    } <= steps.keys()
    assert set(steps["user"]["menu_options"]) == {"network", "serial"}
    assert set(steps["reconfigure"]["menu_options"]) == {
        "reconfigure_network",
        "reconfigure_serial",
    }

    assert "host" in steps["network"]["data"]
    assert "framer" in steps["network"]["data"]
    assert "device" in steps["serial"]["data"]
    assert "unit_id" in steps["network"]["data"]
    assert "unit_id" in steps["serial"]["data"]
    assert "connection_entry_id" not in json.dumps(strings)

    assert strings["selector"]["tcp_framer"]["options"] == {
        "socket": "Modbus TCP",
        "rtu": "RTU over TCP",
    }

    assert strings == english


def test_physical_sensor_identity_uses_documented_abbreviations() -> None:
    """Use the TROVIS sensor abbreviation in entity keys and visible names."""
    descriptions = {
        description.field: description
        for description in _GLOBAL
        if description.component == "sensors"
    }

    expected = {
        "af1": ("sensor_af1", "outdoor_temperature_1", "AF1"),
        "af2": ("sensor_af2", "outdoor_temperature_2", "AF2"),
        "vf1": ("sensor_vf1", "flow_temperature_1", "VF1"),
        "vf2": ("sensor_vf2", "flow_temperature_2", "VF2"),
        "vf3": ("sensor_vf3", "flow_temperature_3", "VF3"),
        "vf4": ("sensor_vf4", "flow_temperature_4", "VF4"),
        "ruef1": ("sensor_ruef1", "return_temperature_1", "RüF1"),
        "ruef2": ("sensor_ruef2", "return_temperature_2", "RüF2"),
        "ruef3": ("sensor_ruef3", "return_temperature_3", "RüF3"),
        "rf1": ("sensor_rf1", "room_temperature_1", "RF1"),
        "rf2": ("sensor_rf2", "room_temperature_2", "RF2"),
        "rf3": ("sensor_rf3", "room_temperature_3", "RF3"),
        "sf1": ("sensor_sf1", "ww_storage_temperature", "SF1"),
        "sf2": ("sensor_sf2", "ww_storage_temperature_lower", "SF2"),
        "sf3": ("sensor_sf3", "sf3", "SF3"),
        "ae1": ("sensor_ae1", "ae1", "AE1"),
        "ae2": ("sensor_ae2", "ae2", "AE2"),
        "ae3": ("sensor_ae3", "ae3", "AE3"),
        "fg1": ("sensor_fg1", "fg1", "FG1"),
        "fg2": ("sensor_fg2", "fg2", "FG2"),
        "fg3": ("sensor_fg3", "fg3", "FG3"),
        "pulse_rate": ("sensor_imp", "pulse_rate", "IMP"),
        "analog_input_voltage": (
            "sensor_ae_voltage",
            "analog_input_voltage",
            "AE",
        ),
        "analog_input_current": (
            "sensor_ae_current",
            "analog_input_current",
            "AE",
        ),
    }

    strings = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    german = json.loads(
        (COMPONENT / "translations" / "de.json").read_text(encoding="utf-8")
    )

    for field, (key, translation_key, abbreviation) in expected.items():
        description = descriptions[field]
        assert description.key == key
        assert description.translation_key == translation_key
        assert strings["entity"]["sensor"][translation_key]["name"].startswith(
            abbreviation
        )
        assert german["entity"]["sensor"][translation_key]["name"].startswith(
            abbreviation
        )

    # Controller-derived values are not physical sensor inputs and keep their
    # descriptive identity instead of receiving an artificial abbreviation.
    assert (
        descriptions["summer_outdoor_temperature_average"].key
        == "summer_outdoor_temperature_average"
    )
