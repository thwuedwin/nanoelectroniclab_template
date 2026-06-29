"""Save measurement rows from user setpoints; auto-read dependent parameters."""

from __future__ import annotations

from typing import Any

from qcodes.dataset.measurements import DataSaver
from qcodes.parameters import ParameterBase

from lab_utils.live_plotting.params import ParameterRegistry


class SetpointSaver:
    """Accept setpoint values from the user; read dependents from instruments."""

    def __init__(
        self,
        datasaver: DataSaver,
        registry: ParameterRegistry,
    ) -> None:
        self._datasaver = datasaver
        self._registry = registry

    def __call__(self, *setpoint_tuples: tuple[ParameterBase, Any]) -> None:
        self.save(*setpoint_tuples)

    def save(self, *setpoint_tuples: tuple[ParameterBase, Any]) -> None:
        expected = self._registry.setpoint_aliases
        if len(setpoint_tuples) != len(expected):
            aliases = ", ".join(expected)
            raise ValueError(
                f"save() expects {len(expected)} setpoint(s) ({aliases}), "
                f"got {len(setpoint_tuples)}"
            )

        result: list[tuple[ParameterBase, Any]] = []
        for alias, (param, value) in zip(expected, setpoint_tuples, strict=True):
            expected_param = self._registry.param(alias)
            if param is not expected_param:
                raise ValueError(
                    f"Setpoint {alias!r} must use node.param({alias!r}), "
                    f"got {getattr(param, 'name', param)!r}"
                )
            result.append((param, value))

        for alias in self._registry.dependent_aliases:
            dep = self._registry.param(alias)
            result.append((dep, dep()))

        self._datasaver.add_result(*result)


__all__ = ["SetpointSaver"]
