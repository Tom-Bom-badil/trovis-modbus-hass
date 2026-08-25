"""Repository-level tests for the TROVIS HACS integration."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "trovis557x"
TRANSLATIONS = COMPONENT / "translations"


def _load_json(path: Path) -> dict:
    """Load one JSON file."""
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _requirement(requirements: list[str], prefix: str) -> str:
    """Return exactly one requirement matching the package prefix."""
    matches = [
        requirement
        for requirement in requirements
        if requirement.lower().startswith(prefix.lower())
    ]

    assert len(matches) == 1, (
        f"Expected exactly one requirement starting with {prefix!r}, got {matches}"
    )

    return matches[0]


def test_manifest_contract() -> None:
    """Validate the integration-owned package and backend contract."""
    manifest = _load_json(COMPONENT / "manifest.json")

    assert manifest["domain"] == "trovis557x"
    assert manifest["config_flow"] is True
    assert manifest["integration_type"] == "device"
    assert manifest["iot_class"] == "local_polling"

    # modbus-connection is a normal Python requirement owned by this
    # integration, not a Home Assistant integration dependency.
    assert "modbus_connection" not in manifest.get("dependencies", [])

    requirements = manifest["requirements"]

    trovis_requirement = _requirement(requirements, "trovis-modbus")
    modbus_requirement = _requirement(
        requirements,
        "modbus-connection[tmodbus]",
    )
    _requirement(requirements, "tmodbus")

    # Do not duplicate the current minimum release versions in this test.
    # The manifest itself is the single source of truth for those.
    assert ">=" in trovis_requirement
    assert "<3" in trovis_requirement

    assert ">=" in modbus_requirement
    assert "<5" in modbus_requirement

    assert not any("pymodbus" in requirement.lower() for requirement in requirements)

    assert "trovis_modbus" in manifest["loggers"]


def test_strings_and_english_translation_contract() -> None:
    """Validate integration-owned config-flow strings."""
    strings = _load_json(COMPONENT / "strings.json")
    english = _load_json(TRANSLATIONS / "en.json")

    # English is the source language and should stay synchronized.
    assert strings == english

    steps = strings["config"]["step"]

    expected_steps = {
        "user",
        "network",
        "serial",
        "device",
        "reconfigure",
        "reconfigure_network",
        "reconfigure_serial",
    }

    assert expected_steps <= steps.keys()

    assert set(steps["user"]["menu_options"]) == {
        "network",
        "serial",
    }

    assert set(steps["reconfigure"]["menu_options"]) == {
        "reconfigure_network",
        "reconfigure_serial",
    }

    assert "host" in steps["network"]["data"]
    assert "framer" in steps["network"]["data"]
    assert "unit_id" in steps["network"]["data"]

    assert "device" in steps["serial"]["data"]
    assert "unit_id" in steps["serial"]["data"]

    assert "connection_entry_id" not in json.dumps(strings)

    assert strings["selector"]["tcp_framer"]["options"] == {
        "socket": "Modbus TCP",
        "rtu": "RTU over TCP",
    }


def test_documented_sensor_abbreviations() -> None:
    """Keep documented TROVIS sensor abbreviations in visible names."""
    english = _load_json(TRANSLATIONS / "en.json")
    german = _load_json(TRANSLATIONS / "de.json")

    expected = {
        "outdoor_temperature_1": "AF1",
        "outdoor_temperature_2": "AF2",
        "flow_temperature_1": "VF1",
        "flow_temperature_2": "VF2",
        "flow_temperature_3": "VF3",
        "flow_temperature_4": "VF4",
        "return_temperature_1": "RüF1",
        "return_temperature_2": "RüF2",
        "return_temperature_3": "RüF3",
        "room_temperature_1": "RF1",
        "room_temperature_2": "RF2",
        "room_temperature_3": "RF3",
        "ww_storage_temperature": "SF1",
        "ww_storage_temperature_lower": "SF2",
        "sf3": "SF3",
        "ae1": "AE1",
        "ae2": "AE2",
        "ae3": "AE3",
        "fg1": "FG1",
        "fg2": "FG2",
        "fg3": "FG3",
        "pulse_rate": "IMP",
        "analog_input_voltage": "AE",
        "analog_input_current": "AE",
    }

    for translation_key, abbreviation in expected.items():
        english_name = english["entity"]["sensor"][translation_key]["name"]
        german_name = german["entity"]["sensor"][translation_key]["name"]

        assert english_name.startswith(abbreviation), (
            f"{translation_key}: English name must start with "
            f"{abbreviation!r}, got {english_name!r}"
        )

        assert german_name.startswith(abbreviation), (
            f"{translation_key}: German name must start with "
            f"{abbreviation!r}, got {german_name!r}"
        )


def test_local_dev_overrides_remain_local() -> None:
    """Ensure local developer overrides cannot accidentally be committed."""
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "**/_local_dev_overrides/" in gitignore

    # Obsolete development mechanisms must not return.
    assert not (COMPONENT / "_local_dev.py").exists()
    assert not (COMPONENT / "local_dev.py").exists()


def test_pumps_and_valves_device_contract() -> None:
    """Keep the canonical read-only actuator view and speaking IDs stable."""
    strings = _load_json(COMPONENT / "strings.json")
    german = _load_json(TRANSLATIONS / "de.json")

    assert strings["device"]["pumps_and_valves"]["name"] == "Pumps and Valves"
    assert german["device"]["pumps_and_valves"]["name"] == "Pumpen und Ventile"

    sensor_source = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    binary_source = (COMPONENT / "binary_sensor.py").read_text(encoding="utf-8")
    switch_source = (COMPONENT / "switch.py").read_text(encoding="utf-8")

    assert "pumps_and_valves_rk{index}_valve_setpoint" in sensor_source
    assert "pumps_and_valves_up{index}" in binary_source
    assert "pumps_and_valves_rk{index}_valve_opening" in binary_source
    assert "pumps_and_valves_rk{index}_valve_closing" in binary_source
    assert 'key="pumps_and_valves_slp"' in binary_source
    assert 'key="pumps_and_valves_zp"' in binary_source
    assert 'key="pumps_and_valves_solar_pump"' in binary_source

    # Pumps and Valves is the canonical status view. Pump controls remain in
    # their functional Rk devices and must not be duplicated here.
    assert "pumps_and_valves_up{index}_control" not in switch_source
    assert 'key="pumps_and_valves_slp_control"' not in switch_source
    assert 'key="pumps_and_valves_zp_control"' not in switch_source

    # Pump states in this device deliberately use plain binary semantics so
    # Home Assistant renders them consistently as On/Off instead of mixing
    # Running/Not running with On/Off.
    rk_actuators = binary_source.split(
        "def _pumps_and_valves_rk_binary_descriptions", 1
    )[1].split("_PUMPS_AND_VALVES_RK4", 1)[0]
    solar_actuators = binary_source.split("_PUMPS_AND_VALVES_SOLAR", 1)[1].split(
        "def _description_supported", 1
    )[0]
    assert "BinarySensorDeviceClass.RUNNING" not in rk_actuators
    assert "BinarySensorDeviceClass.RUNNING" not in solar_actuators


def test_rk4_cleanup_contract() -> None:
    """Keep the resolved Rk4 cleanup decisions in the HA presentation."""
    sensor_source = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    binary_source = (COMPONENT / "binary_sensor.py").read_text(encoding="utf-8")
    switch_source = (COMPONENT / "switch.py").read_text(encoding="utf-8")

    active_setpoint = sensor_source.split('key="rk4_setpoint_active"', 1)[1].split(
        "),", 1
    )[0]
    assert "entity_category=EntityCategory.DIAGNOSTIC" in active_setpoint

    for removed_key in (
        "rk4_mode_control_autonomous",
        "rk4_storage_tank_charging_pump_control_autonomous",
        "rk4_circulation_pump_control_autonomous",
        "rk4_special_setpoint_control_autonomous",
    ):
        assert removed_key not in binary_source

    intermediate_heating = switch_source.split(
        'key="rk4_intermediate_heating_function_enabled"', 1
    )[1].split("),", 1)[0]
    assert "enabled=False" not in intermediate_heating
    assert "coordinator.device.intermediate_heating_available" in switch_source
