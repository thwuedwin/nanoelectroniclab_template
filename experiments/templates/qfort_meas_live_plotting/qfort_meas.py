# Import

from qcodes import Measurement
from qcodes.instrument_drivers.Keithley.Keithley_2400 import Keithley2400
from qcodes.instrument_drivers.stanford_research import SR830

from lab_utils.live_plotting import QfortMeasNode

config = {
    "user": "",
    "exp_name": "",
    "sample_name": "",
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

node = QfortMeasNode(config)


@node.run
def exp():
    ...


if __name__ == "__main__":
    node.start()
