"""Step-by-step AMI Model 430 magnet test (single-axis).

Follows the QCoDeS official AMI430 example:
https://microsoft.github.io/Qcodes/examples/driver_examples/Qcodes%20example%20with%20AMI430.html

Usage:
    python scripts/test_ami430_magnet.py
    python scripts/test_ami430_magnet.py --auto
    python scripts/test_ami430_magnet.py --address "TCPIP0::169.254.21.127::7180::SOCKET"
    python scripts/test_ami430_magnet.py --read-only   # connect + read, no ramping
"""
import numpy as np
import time
import matplotlib.pyplot as plt
from qcodes.instrument_drivers.american_magnetics import AMIModel430

# --- Edit for your setup ---------------------------------------------------
DEFAULT_ADDRESS = "TCPIP0::192.168.50.66::7180::SOCKET"

ami430 = AMIModel430("z", address=DEFAULT_ADDRESS)

# lets test an individual instrument first. We select the z axis.
instrument = ami430
# %% 
# Since the set method of the driver only excepts fields in Tesla and we want to check if the correct
# currents are applied, we need to convert target currents to target fields. For this reason we need
# the coil constant.
coil_const = instrument._coil_constant
current_rating = instrument._current_rating
current_ramp_limit = instrument._current_ramp_limit
print(f"coil constant = {coil_const} T/A")
print(f"current rating = {current_rating} A")
print(f"current ramp rate limit = {current_ramp_limit} A/s")

# %%
# Let see if we can set and get the field in Tesla
target_current = 1.0  # [A]  The current we want to set
target_field = coil_const * target_current  # [T]
print(f"Target field is {target_field} T")
instrument.field(target_field)

field = instrument.field()  # This gives us the measured field
print(f"Measured field is {field} T")
# The current should be
current = field / coil_const
print(f"Measured current is = {current} A")
# We have verified with manual inspection that the current has indeed ben reached

# %%
# Verify that the ramp rate is indeed how it is specified
ramp_rate = instrument.ramp_rate()  # get the ramp rate
instrument.field(0)  # make sure we are back at zero amps

target_fields = [0.1, 0.3, 0.7, 1.5]  # [T]
t_setting = []
t_actual = []

for target_field in target_fields:
    current_field = instrument.field()
    ts = abs(target_field - current_field) / ramp_rate
    t_setting.append(ts)

    tb = time.time()
    instrument.field(target_field)
    te = time.time()
    ta = te - tb
    t_actual.append(ta)

fig, ax = plt.subplots()
ax.plot(t_setting, t_actual, ".-")
plt.xlabel("ramp time calculated from settings [s]")
plt.ylabel("measured ramp time [s]")
plt.show()
slope, offset = np.polyfit(t_setting, t_actual, 1)
print(f"slope = {slope}. A value close to one means the correct ramp times are used")
print(
    f"offset = {offset}. An offset indicates that there is a fixed delay is added to a ramp request"
)