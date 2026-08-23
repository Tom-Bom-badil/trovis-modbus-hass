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
