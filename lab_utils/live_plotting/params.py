"""Parameter path resolution and Measurement registration for QfortMeasNode."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from qcodes.dataset import Measurement
from qcodes.parameters import Parameter, ParameterBase


class ParameterConfigError(ValueError):
    """Raised when config ``parameters`` / ``sweep`` are invalid."""


def _get_instrument(instruments: Mapping[str, Any], name: str) -> Any:
    if name in instruments:
        return instruments[name]

    for instrument in instruments.values():
        if getattr(instrument, "name", None) == name:
            return instrument

    keys = sorted(instruments)
    inst_names = sorted(
        {getattr(inst, "name", None) for inst in instruments.values()} - {None}
    )
    raise KeyError(
        f"Unknown instrument {name!r}. "
        f"Available instrument keys: {keys}; qcodes names: {inst_names}"
    ) from None


def resolve_param(instruments: Mapping[str, Any], dotted_path: str) -> ParameterBase:
    """Resolve a dotted path such as ``sr830_1.R`` to a qcodes Parameter."""
    path = dotted_path.strip()
    if not path:
        raise ValueError("Parameter path must be a non-empty string")

    parts = path.split(".")
    if len(parts) < 2:
        raise ValueError(
            f"Parameter path {dotted_path!r} must be 'instrument_name.parameter' "
            f"(at least one dot)"
        )

    obj: Any = _get_instrument(instruments, parts[0])
    for part in parts[1:]:
        try:
            obj = getattr(obj, part)
        except AttributeError as exc:
            raise AttributeError(
                f"Cannot resolve {dotted_path!r}: {type(obj).__name__!r} "
                f"has no attribute {part!r}"
            ) from exc

    if not isinstance(obj, ParameterBase):
        raise TypeError(
            f"Path {dotted_path!r} resolved to {type(obj).__name__}, "
            f"expected a qcodes Parameter"
        )
    return obj


def resolve_parameters(
    instruments: Mapping[str, Any],
    parameters: Mapping[str, str | ParameterBase],
) -> dict[str, ParameterBase]:
    """Resolve all parameter aliases declared in config."""
    if not parameters:
        raise ParameterConfigError("config['parameters'] must contain at least one alias")

    resolved: dict[str, ParameterBase] = {}
    for alias, spec in parameters.items():
        if not alias:
            raise ParameterConfigError("Parameter aliases must be non-empty strings")
        if isinstance(spec, ParameterBase):
            resolved[alias] = spec
        elif isinstance(spec, str):
            resolved[alias] = resolve_param(instruments, spec)
        else:
            raise ParameterConfigError(
                f"Parameter {alias!r} must be a dotted path string or Parameter instance"
            )
    return resolved


def classify_parameters(
    parameters: Mapping[str, str | ParameterBase],
    sweep: Mapping[str, Any],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split aliases into setpoints (``sweep`` keys) and dependents.

    Setpoint order follows ``sweep`` dict insertion order (Python 3.7+).
    """
    if not sweep:
        raise ParameterConfigError(
            "config['sweep'] must contain at least one setpoint alias"
        )

    param_aliases = set(parameters)
    setpoint_aliases: list[str] = []
    for alias in sweep:
        if alias not in param_aliases:
            raise ParameterConfigError(
                f"Sweep alias {alias!r} is not listed in config['parameters']. "
                f"Available: {sorted(param_aliases)}"
            )
        setpoint_aliases.append(alias)

    setpoint_set = set(setpoint_aliases)
    dependent_aliases = [alias for alias in parameters if alias not in setpoint_set]
    return tuple(setpoint_aliases), tuple(dependent_aliases)


def register_parameters_on_measurement(
    meas: Measurement,
    params: Mapping[str, ParameterBase],
    *,
    setpoint_aliases: Sequence[str],
    dependent_aliases: Sequence[str] | None = None,
) -> None:
    """Register setpoints and dependents on a qcodes Measurement."""
    missing = [alias for alias in setpoint_aliases if alias not in params]
    if missing:
        raise ParameterConfigError(
            f"Setpoint alias(es) not resolved: {missing}. "
            f"Available: {sorted(params)}"
        )

    if dependent_aliases is None:
        setpoint_set = set(setpoint_aliases)
        dependent_aliases = [alias for alias in params if alias not in setpoint_set]

    missing = [alias for alias in dependent_aliases if alias not in params]
    if missing:
        raise ParameterConfigError(
            f"Dependent alias(es) not resolved: {missing}. "
            f"Available: {sorted(params)}"
        )

    sweep_params = tuple(params[alias] for alias in setpoint_aliases)

    for alias in setpoint_aliases:
        meas.register_parameter(params[alias])

    for alias in dependent_aliases:
        meas.register_parameter(params[alias], setpoints=sweep_params)


class ParameterRegistry:
    """Resolve config parameters and expose registration helpers."""

    def __init__(
        self,
        instruments: Mapping[str, Any],
        parameters: Mapping[str, str | ParameterBase],
        sweep: Mapping[str, Any],
    ) -> None:
        self._setpoint_aliases, self._dependent_aliases = classify_parameters(
            parameters, sweep
        )
        self._params = resolve_parameters(instruments, parameters)

    @property
    def setpoint_aliases(self) -> tuple[str, ...]:
        return self._setpoint_aliases

    @property
    def dependent_aliases(self) -> tuple[str, ...]:
        return self._dependent_aliases

    def param(self, alias: str) -> ParameterBase:
        try:
            return self._params[alias]
        except KeyError:
            raise KeyError(
                f"Unknown parameter alias {alias!r}. "
                f"Available: {sorted(self._params)}"
            ) from None

    def param_aliases(self) -> list[str]:
        return sorted(self._params)

    def register_on(self, meas: Measurement) -> None:
        register_parameters_on_measurement(
            meas,
            self._params,
            setpoint_aliases=self._setpoint_aliases,
            dependent_aliases=self._dependent_aliases,
        )


__all__ = [
    "Parameter",
    "ParameterBase",
    "ParameterConfigError",
    "ParameterRegistry",
    "classify_parameters",
    "register_parameters_on_measurement",
    "resolve_param",
    "resolve_parameters",
]
