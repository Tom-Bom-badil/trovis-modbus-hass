"""Contract tests for the TROVIS heating-curve simulation UI helper."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "trovis557x"
TRANSLATIONS = COMPONENT / "translations"


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_simulation_helper_translation_contract() -> None:
    """Keep strings/en identical and preserve the simulation helper key."""
    strings = _load_json(COMPONENT / "strings.json")
    english = _load_json(TRANSLATIONS / "en.json")
    german = _load_json(TRANSLATIONS / "de.json")

    assert strings == english
    assert (
        strings["entity"]["sensor"]["ui_helper_simulation_values"]["name"]
        == "Helper - {component} simulation values"
    )
    assert (
        german["entity"]["sensor"]["ui_helper_simulation_values"]["name"]
        == "Helper - {component} Simulationswerte"
    )


def test_simulation_helper_entity_contract() -> None:
    """Keep the helper local, hidden, and named from the controller slug."""
    simulation_source = (COMPONENT / "simulation.py").read_text(encoding="utf-8")
    sensor_source = (COMPONENT / "sensor.py").read_text(encoding="utf-8")

    assert 'f"ui_helper_rk{index}_simulation_values"' in simulation_source
    assert 'translation_key="ui_helper_simulation_values"' in simulation_source
    assert "self._attr_device_info = None" in simulation_source
    assert "_attr_entity_registry_visible_default = False" in simulation_source
    assert "self._subsystem.heating_curve_parameters()" in simulation_source
    assert "calculate_heating_curve(" in simulation_source
    assert "coordinator.device.room_heating_circuit_indices" in sensor_source
    assert "TrovisHeatingCurveSimulationSensor" in sensor_source
