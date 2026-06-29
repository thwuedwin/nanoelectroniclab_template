"""Hall-effect gate sweep with live Qt plotting (QfortMeasNode template).

Copy this folder to ``experiments/{user}/`` and edit ``config`` for your setup.

Set ``DEMO_MODE = True`` to run without lab hardware (mock parameters + simulated sweep).
"""

from __future__ import annotations

import time

import numpy as np
from qcodes.instrument_drivers.Keithley.Keithley_2400 import Keithley2400
from qcodes.instrument_drivers.stanford_research import SR830
from qcodes.parameters import Parameter

from lab_utils.live_plotting import QfortMeasNode

# Toggle for hardware-free testing of the Qt UI and JSON sidecar save flow.
DEMO_MODE = True


def _mock_instrument(name: str):
    return type("MockInstrument", (), {"name": name, "parameters": {}})()


def _demo_config() -> dict:
    gate_state = {"v": 0.0}

    def _set_gate(v: float) -> None:
        gate_state["v"] = float(v)

    keithley = _mock_instrument("keithley_2400")
    sr830_1 = _mock_instrument("sr830_1")
    sr830_2 = _mock_instrument("sr830_2")
    sr830_3 = _mock_instrument("sr830_3")

    return {
        "user": "edwin",
        "exp_name": "hall_sweep_demo",
        "sample_name": "device_A",
        "measurement_name": "IdVg",
        "instruments": {
            "keithley_2400": keithley,
            "sr830_1": sr830_1,
            "sr830_2": sr830_2,
            "sr830_3": sr830_3,
        },
        "parameters": {
            "source_drain": Parameter(
                "amplitude",
                instrument=sr830_1,
                get_cmd=lambda: 0.1,
                set_cmd=lambda v: None,
            ),
            "back_gate": Parameter(
                "volt",
                instrument=keithley,
                get_cmd=lambda: gate_state["v"],
                set_cmd=_set_gate,
            ),
            "Vxx_r": Parameter(
                "R",
                instrument=sr830_2,
                get_cmd=lambda: 100.0 + 5.0 * gate_state["v"],
            ),
            "Vxx_phase": Parameter(
                "P",
                instrument=sr830_2,
                get_cmd=lambda: 0.0,
            ),
            "Vxy_r": Parameter(
                "R",
                instrument=sr830_3,
                get_cmd=lambda: 10.0 + 2.0 * gate_state["v"],
            ),
            "Vxy_phase": Parameter(
                "P",
                instrument=sr830_3,
                get_cmd=lambda: 90.0,
            ),
        },
        "sweep": {"back_gate": {}},
    }


def _hardware_config() -> dict:
    return {
        "user": "edwin",
        "exp_name": "hall_sweep",
        "sample_name": "device_A",
        "measurement_name": "IdVg",
        "description": """Demo measurement for QfortMeasNode.
        blablablabla...
        """,
        "instruments": {
            "keithley_2400": Keithley2400("keithley_2400", "GPIB1::26::INSTR"),
            "sr830_1": SR830("sr830_1", "GPIB1::3::INSTR"),
            "sr830_2": SR830("sr830_2", "GPIB1::4::INSTR"),
            "sr830_3": SR830("sr830_3", "GPIB1::5::INSTR"),
        },
        "parameters": {
            "source_drain": "sr830_1.amplitude",
            "back_gate": "keithley_2400.volt",
            "Vxx_r": "sr830_2.R",
            "Vxx_phase": "sr830_2.P",
            "Vxy_r": "sr830_3.R",
            "Vxy_phase": "sr830_3.P",
        },
        "sweep": {
            "back_gate": {},
        },
    }


config = _demo_config() if DEMO_MODE else _hardware_config()
node = QfortMeasNode(config)

# Configure plot on the main thread before measurement starts (not inside exp()).
node.plot.add_trace(x="back_gate", y="Vxx_r", label="Vxx", color="b")
node.plot.add_trace(x="back_gate", y="Vxy_r", label="Vxy", color="r")
node.plot.set_xlabel("Gate Voltage (V)")
node.plot.set_title(config["exp_name"])


@node.run
def exp(save):
    node.add_metadata("note", "demo sweep" if DEMO_MODE else "hall measurement")
    node.param("source_drain")(0.1)

    bg = node.param("back_gate")
    for v in np.linspace(-1.0, 1.0, 2001):
        if node.cancelled:
            break
        bg(v)
        save((bg, v))
        if DEMO_MODE:
            time.sleep(0.05)


if __name__ == "__main__":
    node.start()
