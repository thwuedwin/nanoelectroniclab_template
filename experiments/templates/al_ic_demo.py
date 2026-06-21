# %% == Import ==
from pathlib import Path
import numpy as np
import math
import matplotlib.pyplot as plt
import pandas as pd
import json
import requests
import time
import sys

import qcodes as qc
import qcodes.logger
from qcodes.dataset import (
    LinSweep,
    LogSweep,
    Measurement,
    TogetherSweep,
    do1d,
    do2d,
    dond,
    initialise_or_create_database_at,
    load_or_create_experiment,
    plot_dataset,
)

from qcodes.utils.dataset.doNd import plot
from qcodes.instrument.parameter import Parameter

from drivers import bluefors
from lab_utils.paths import DATA_DIR, CONFIG_BLUEFORS
from lab_utils.utils import *

# %% == Initialize qcodes context ==
user = 'edwin'
exp_name = 'qcodes_demo'
sample_name='box'

# qcodes configuration
qc.config.user.mainfolder = DATA_DIR / f'{user}' 
database_loc = qc.config.user.mainfolder / f'{user}.db'
qc.initialise_or_create_database_at(database_loc)
print('database:', qc.config.core.db_location)

station = qc.Station(config_file=CONFIG_BLUEFORS, use_monitor=True)
exp = load_or_create_experiment(
    experiment_name=exp_name, sample_name=sample_name
)

# %% == Load instruments ==
kei = station.load_instrument('keithley_2400')

# %% Parameters
current_time = Parameter(
    name='time',
    label='Time',
    unit='s',
    get_cmd=lambda: time.time()
)

def calc_r():
    i = kei.curr()
    if i != 0:
        return kei.volt() / i
    else: 
        return float('nan')

resistance = Parameter(
    name='resistance',
    label='Resistance',
    unit='Ohm',
    get_cmd=calc_r
)

# list of dependent variables
param_list = [
    kei.curr,
    resistance,
    current_time
]

# %% == Do measurements ==
kei.output(True)
do1d(
    kei.volt,
    0, 20, 101, 0.1,
    *param_list,
    show_progress=True,
    do_plot=True
)

# %% == close instruments ==
kei.close()
# %%
