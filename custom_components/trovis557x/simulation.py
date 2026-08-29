"""Home Assistant-local heating-curve simulation helpers."""

from __future__ import annotations

from dataclasses import fields

from homeassistant.components.sensor import SensorEntity
from trovis_modbus import OUTDOOR_TEMPERATURES, HeatingCircuitControlMode
from trovis_modbus.heating_curve import (
    HeatingCurveParameters,
    calculate_heating_curve,
)

from . import TrovisEntity
from .coordinator import TrovisCoordinator

_PARAMETER_NAMES = tuple(field.name for field in fields(HeatingCurveParameters))
_CURVE_ATTRIBUTE_NAMES = (
    "x_values",
    "flow_curve",
    "flow_curve_day",
    "flow_curve_night",
    "return_curve",
    "return_curve_day",
    "return_curve_night",
)
_UNRECORDED_ATTRIBUTES = frozenset(
    (
        "control_mode",
        "calculation_state",
        "changed_fields",
        *_PARAMETER_NAMES,
        *_CURVE_ATTRIBUTE_NAMES,
    )
)


class TrovisHeatingCurveSimulationSensor(TrovisEntity, SensorEntity):
    """Local simulation state for one TROVIS room-heating circuit."""

    _unrecorded_attributes = _UNRECORDED_ATTRIBUTES
    _attr_entity_registry_visible_default = False

    def __init__(
        self,
        coordinator: TrovisCoordinator,
        index: int,
    ) -> None:
        component = f"rk{index}"
        super().__init__(
            coordinator,
            f"ui_helper_rk{index}_simulation_values",
            component,
            "sensor",
            translation_key="ui_helper_simulation_values",
            translation_placeholders={"component": f"Rk{index}"},
        )

        # Dashboard-local helper: keep it out of the TROVIS device views.
        self._attr_device_info = None

        self._index = index
        self._baseline = self._subsystem.heating_curve_parameters()
        self._parameters = self._baseline
        self._operating_mode = coordinator.device.heating_circuit_operating_mode(index)

    @property
    def changed_fields(self) -> tuple[str, ...]:
        """Return parameter fields that differ from the initial snapshot."""
        return tuple(
            name
            for name in _PARAMETER_NAMES
            if getattr(self._parameters, name) != getattr(self._baseline, name)
        )

    @property
    def native_value(self) -> int:
        """Return the number of simulation parameters changed from baseline."""
        return len(self.changed_fields)

    def _curve_attributes(self) -> dict[str, object]:
        """Calculate the simulated flow and return characteristics."""
        operating_mode = self._operating_mode
        if operating_mode is None:
            return {"calculation_state": "error"}

        curves = {
            "flow_curve": calculate_heating_curve(
                self._parameters,
                operating_mode=operating_mode,
                curve="flow",
            ),
            "flow_curve_day": calculate_heating_curve(
                self._parameters,
                "day",
                operating_mode=operating_mode,
                curve="flow",
            ),
            "flow_curve_night": calculate_heating_curve(
                self._parameters,
                "night",
                operating_mode=operating_mode,
                curve="flow",
            ),
            "return_curve": calculate_heating_curve(
                self._parameters,
                operating_mode=operating_mode,
                curve="return",
            ),
            "return_curve_day": calculate_heating_curve(
                self._parameters,
                "day",
                operating_mode=operating_mode,
                curve="return",
            ),
            "return_curve_night": calculate_heating_curve(
                self._parameters,
                "night",
                operating_mode=operating_mode,
                curve="return",
            ),
        }

        if any(curve is None for curve in curves.values()):
            return {"calculation_state": "error"}

        if any(
            len(curve) != len(OUTDOOR_TEMPERATURES)
            for curve in curves.values()
            if curve is not None
        ):
            return {"calculation_state": "error"}

        return {
            "calculation_state": "calculated",
            "x_values": list(OUTDOOR_TEMPERATURES),
            **curves,
        }

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Expose the simulation snapshot and its calculated characteristics."""
        operating_mode = self._operating_mode
        attributes: dict[str, object] = {
            "control_mode": (
                operating_mode.value
                if isinstance(operating_mode, HeatingCircuitControlMode)
                else None
            ),
            "changed_fields": list(self.changed_fields),
        }
        attributes.update(
            {name: getattr(self._parameters, name) for name in _PARAMETER_NAMES}
        )
        attributes.update(self._curve_attributes())
        return attributes
