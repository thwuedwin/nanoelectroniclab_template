import numpy as np
import time

def ramp_to_step(param, step, set_val, delay=0.1, call_by_user=True):
    while call_by_user:
        print()
        res = input(f"It takes {step * delay} seconds. Do you want to continue?[y/N]")

        if res.lower() == 'y':
            break
        else:
            pass

    for val in np.linspace(param(), set_val, step + 1):
        param(val)
        time.sleep(delay)

def ramp_to_time(param, ramp_time, set_val, delay=0.1):
    step = int(ramp_time / delay)
    step_size = abs((param() - set_val))/ step
    while True:
        res = input(f"Step size is {step_size} {param.unit}. Do you want to continue?[y/N]")

        if res.lower() == 'y':
            break
        else:
            pass
    ramp_to_step(param, step, set_val, delay=delay, call_by_user=False)
    

def reset_sr830():
    pass