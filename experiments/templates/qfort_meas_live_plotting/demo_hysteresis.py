"""Magnetic-field hysteresis sweep with live Qt plotting (QfortMeasNode template).

Copy this folder to ``experiments/{user}/`` and edit ``config`` for your setup.

Sweeps the AMI Model 430 field from ``B_MIN`` to ``B_MAX`` and back while
recording lock-in response (e.g. magnetoresistance). Edit instrument addresses,
field limits, and ramp rate before running on hardware.
"""

from __future__ import annotations

import time

import numpy as np
from qcodes.instrument_drivers.american_magnetics import AMIModel430
from qcodes.instrument_drivers.stanford_research import SR830
from qcodes.parameters import Parameter

from lab_utils.live_plotting import QfortMeasNode

B_MIN = -1.0  # T
B_MAX = 1.0  # T
N_POINTS = 101
RAMP_RATE = 0.01  # T/s
SETTLING_S = 0.2  # s, extra wait after each field step

_branch_state = {"name": "up"}


def _set_branch(name: str) -> None:
    _branch_state["name"] = name


config = {
    "user": "edwin",
    "exp_name": "hysteresis_demo",
    "sample_name": "demo_device",
    "measurement_name": "B_hysteresis",
    "instruments": {
        "ami430_z": AMIModel430(
            "ami430_z", "TCPIP0::169.254.21.127::7180::SOCKET"
        ),
        "sr830_1": SR830("sr830_1", "GPIB1::3::INSTR"),
    },
    "parameters": {
        "field": "ami430_z.field",
        "branch": Parameter(
            "branch",
            label="Sweep branch",
            get_cmd=lambda: _branch_state["name"],
            set_cmd=_set_branch,
        ),
        "Vxx": "sr830_1.R",
        "Vxx_phase": "sr830_1.P",
    },
    "sweep": {
        "field": {},
    },
}

node = QfortMeasNode(config)

# Configure plot on the main thread before measurement starts (not inside exp()).
node.plot.add_trace(x="field", y="Vxx", label="Vxx", color="b")
node.plot.set_xlabel("Magnetic Field (T)")
node.plot.set_title(config["exp_name"])


def _prepare_magnet(magnet: AMIModel430) -> None:
    """Enable ramping and return to zero field before the hysteresis loop."""
    magnet.ramp_rate(RAMP_RATE)
    if magnet.switch_heater.enabled():
        magnet.switch_heater.state(True)
    magnet.field(0)


def _measure_point(save, field_param) -> None:
    save((field_param, field_param()))


def _sweep_branch(
    save,
    field_param,
    values: np.ndarray,
    branch: str,
) -> None:
    for b in values:
        if node.cancelled:
            break
        field_param(b)
        if SETTLING_S > 0:
            time.sleep(SETTLING_S)
        _set_branch(branch)
        _measure_point(save, field_param)


@node.run
def exp(save):
    magnet: AMIModel430 = node.instruments["ami430_z"]
    _prepare_magnet(magnet)

    field_param = node.param("field")
    up = np.linspace(B_MIN, B_MAX, N_POINTS)
    down = np.linspace(B_MAX, B_MIN, N_POINTS)[1:]

    _sweep_branch(save, field_param, up, branch="up")
    _sweep_branch(save, field_param, down, branch="down")


if __name__ == "__main__":
    node.start()
