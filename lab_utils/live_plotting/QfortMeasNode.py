import qcodes as qc
from qcodes.dataset import (
    load_or_create_experiment,
    Measurement,
)

from lab_utils.paths import DATA_DIR
from lab_utils.utils import *

class QfortMeasNode():
    def __init__(self, config):
        self.config = config
        self.qcodes_context = self.setup_qcodes_context()

    def setup_ui(self):
        ...
    
    def setup_qcodes_context(self, config):
        user = 'edwin'
        exp_name = 'qcodes_demo'
        sample_name='box'

        # qcodes configuration
        qc.config.user.mainfolder = DATA_DIR / f'{self.config['user']}' 
        database_loc = qc.config.user.mainfolder / f'{self.config['user']}.db'
        qc.initialise_or_create_database_at(database_loc)

        exp = load_or_create_experiment(
            experiment_name=self.config['exp_name'], sample_name=self.config['sample_name']
        )
        measurement = Measurement()
    
    def run(self, func):
        ...

class QcodesContext():
    def __init__(self, user, exp_name, sample_name):
        self.user = user
        self.exp_name = exp_name
        self.sample_name = sample_name
