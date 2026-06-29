"""Time-series measurement with live Qt plotting (QfortMeasNode template).

Copy this folder to ``experiments/{user}/`` and edit ``config`` for your setup.
"""

from __future__ import annotations

import time

from qcodes.instrument_drivers.stanford_research import SR830
from qcodes.instrument_drivers.Keithley.Keithley_2400 import Keithley2400
from qcodes.parameters import Parameter

from lab_utils.live_plotting import QfortMeasNode

DURATION_S = 300.0
INTERVAL_S = 0.1

config = {
    "user": "edwin",
    "exp_name": "demo_exp",
    "sample_name": "demo_device",
    "measurement_name": "demo",
    "instruments": {
        "sr830_1": SR830("sr830_1", "TCPIP::192.168.50.76::INSTR"),
        "sr830_2": SR830("sr830_2", "TCPIP::192.168.50.76::INSTR"),
        "sr830_3": SR830("sr830_3", "TCPIP::192.168.50.76::INSTR"),
        "keithley_2400": Keithley2400("keithley_2400", "GPIB1::26::INSTR"),
    },
    "parameters": {
        "time": Parameter("time", unit="s"),
        "source_drain": "sr830_1.amplitude",
        "Vxx": "sr830_1.R",
        "Vxx_phase": "sr830_1.P",
    },
    "sweep": {
        "time": {},
    },
}

node = QfortMeasNode(config)

# Configure plot on the main thread before measurement starts (not inside exp()).
node.plot.add_trace(x="time", y="Vxx", label="Vxx", color="b")
# node.plot.add_trace(x="time", y="Vxx_phase", label="Vxx_phase", color="r")
node.plot.set_xlabel("Time (s)")
node.plot.set_title(config["exp_name"])


@node.run
def exp(save):
    node.param("source_drain")(0)

    time_param = node.param("time")
    t0 = time.time()
    while time.time() - t0 < DURATION_S:
        if node.cancelled:
            break
        elapsed = time.time() - t0
        save((time_param, elapsed))
        time.sleep(INTERVAL_S)


if __name__ == "__main__":
    node.start()
