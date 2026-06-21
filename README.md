# NanoElectronic Lab QCoDeS Template

This is a **QCoDeS-based** measurement template designed to standardize the workflow for nanoelectronic device characterization, instrument driver management, and data storage. By using this template, lab members can share instrument drivers and utility functions, ensuring consistency across different measurement setups.

---

## 📂 Project Structure

```text
.
├── README.md
├── pyproject.toml
├── config/             # Station configurations (YAML)
│   ├── conf_bluefors.yaml
│   ├── conf_proteox.yaml
│   └── conf_hall.yaml  # Hall setup (3× SR830 + Keithley gate)
├── data/               # Measurement data (gitignored; created at runtime)
│   └── {user}/
│       ├── qcodes.db   # QCoDeS SQLite database
│       └── records/    # JSON experiment records
│           └── {YYYY-MM-DD}/
├── drivers/            # Custom instrument drivers
│   ├── bluefors.py
│   └── oxford/
│       └── mercury_itc.py
├── experiments/
│   ├── templates/      # Script templates (tracked in git)
│   │   ├── al_ic_demo.py
│   │   └── qfort_meas_live_plotting/
│   │       └── qfort_meas.py
│   └── {user}/         # Personal measurement scripts (gitignored)
│       └── my_experiment/
├── scripts/            # Utility / debug scripts
└── lab_utils/          # Shared toolbox (paths, plotting, analysis)
```

### Measurement Workflow & Data Management

To ensure a structured and collaborative environment, the lab follows a specific directory convention:

- **Experiment scripts:** Copy a template from `experiments/templates/` into your personal directory (e.g. `experiments/{user_name}/my_hall/`), then edit the config.

- **Data storage:** QCoDeS databases and JSON sidecar records are stored under `data/{user_name}/`:
  - `qcodes.db` — all runs for that user (override via config `database_path` if needed)
  - `records/{YYYY-MM-DD}/{run_id}_{exp_name}.json` — experiment metadata snapshots

- **NAS synchronization:** The `data/` directory may be synchronized via the lab NAS for sharing across workstations. **Do not sync SQLite database files while a measurement is in progress** — concurrent writes or sync locks can corrupt `qcodes.db`. Prefer syncing after runs complete, or use a local database path during acquisition.

### Quick start (qfort live plotting template)

```bash
cp -r experiments/templates/qfort_meas_live_plotting experiments/{user}/my_hall
# Edit experiments/{user}/my_hall/qfort_meas.py (user, exp_name, instruments, …)
uv run python experiments/{user}/my_hall/qfort_meas.py
```
