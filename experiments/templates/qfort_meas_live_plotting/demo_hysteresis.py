"""Magnetic-field hysteresis sweep with live Qt plotting (QfortMeasNode template).

Copy this folder to ``experiments/{user}/`` and edit ``config`` for your setup.

Four-branch major loop (``B_min`` should equal ``-B_max``). Each branch issues
one non-blocking ramp to its target field; this script polls the measured field
and lock-in while the magnet ramps:

1. ``0_to_Bmax``   — 0 → B_max
2. ``Bmax_to_Bmin`` — B_max → B_min
3. ``Bmin_to_Bmax`` — B_min → B_max
4. ``Bmax_to_0``   — B_max → 0

Sweep limits and timing live in ``config["sweep"]["field"]``.
"""

from __future__ import annotations

import time

from qcodes.instrument_drivers.american_magnetics import AMIModel430
from qcodes.instrument_drivers.stanford_research import SR830
from qcodes.parameters import Parameter

from lab_utils.live_plotting import QfortMeasNode

_branch_state = {"name": "0_to_Bmax"}


def set_branch(name: str) -> None:
    _branch_state["name"] = name


config = {
    "user": "edwin",
    "exp_name": "hysteresis_demo",
    "sample_name": "demo_device",
    "measurement_name": "B_hysteresis",
    "instruments": {
        "ami430": AMIModel430(
            "ami430", "TCPIP0::192.168.50.66::7180::SOCKET"
        ),
        "sr830_1": SR830("sr830_1", "GPIB1::3::INSTR"),
    },
    "parameters": {
        "field": "ami430.field",
        "branch": Parameter(
            "branch",
            label="Sweep branch",
            get_cmd=lambda: _branch_state["name"],
            set_cmd=set_branch,
        ),
        "Vxx": "sr830_1.R",
        "Vxx_phase": "sr830_1.P",
    },
    "sweep": {
        "field": {
            "B_min": -6.0,  # T; should equal -B_max for the symmetric loop
            "B_max": 6.0,  # T
            "ramp_rate": 0.1,  # T/min (magnet maximum: 0.1 T/min)
            "sample_interval_s": 0.1,  # s between readings while ramping
        },
    },
}

node = QfortMeasNode(config)

# Configure plot on the main thread before measurement starts (not inside exp()).
node.plot.add_trace(x="field", y="Vxx", label="Vxx", color="b")
node.plot.set_xlabel("Magnetic Field (T)")
node.plot.set_title(config["exp_name"])



def branches() -> tuple[tuple[str, float], ...]:
    sweep = config["sweep"]["field"]
    b_min = sweep["B_min"]
    b_max = sweep["B_max"]
    return (
        ("0_to_Bmax", b_max),
        ("Bmax_to_Bmin", b_min),
        ("Bmin_to_Bmax", b_max),
        ("Bmax_to_0", 0.0),
    )


def prepare_magnet(magnet: AMIModel430) -> None:
    """Enable ramping and return to zero field before the hysteresis loop."""
    ramp_rate = config["sweep"]["field"]["ramp_rate"]
    if ramp_rate > 0.1:
        raise ValueError("Ramp rate is too high. The maximum allowed ramp rate is 0.1 T/min.")
    magnet.ramp_rate(ramp_rate)

    if magnet.switch_heater.enabled():
        magnet.switch_heater.state(True)
    magnet.field(0)


def ramp_branch(
    save,
    field_param,
    magnet: AMIModel430,
    target_field: float,
    branch: str,
) -> None:
    """Start a non-blocking ramp and record data until the magnet stops."""
    set_branch(branch)
    magnet.set_field(target_field, block=False)

    sample_interval_s = config["sweep"]["field"]["sample_interval_s"]
    while True:
        if node.cancelled:
            magnet.pause()
            return
        save((field_param, field_param()))
        if magnet.ramping_state() != "ramping":
            break
        time.sleep(sample_interval_s)


@node.run
def exp(save):
    magnet: AMIModel430 = node.instruments["ami430"]
    prepare_magnet(magnet)

    field_param = node.param("field")
    for name, target in branches():
        ramp_branch(save, field_param, magnet, target, branch=name)


if __name__ == "__main__":
    node.start()
