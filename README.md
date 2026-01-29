# NanoElectronic Lab QCoDeS Template

This is a **QCoDeS-based** measurement template designed to standardize the workflow for nanoelectronic device characterization, instrument driver management, and data storage. By using this template, lab members can share instrument drivers and utility functions, ensuring consistency across different measurement setups.

---

## 📂 Project Structure

```text
.
├── README.md
├── pyproject.toml
├── data/               # Measurement data (Database files are ignored by Git)
│   └── user1/
│       ├── user1.db    # database for specific user
│       └── exp_data/   # experiments for specific user
├── experiments/        
│   ├── templates/      # Script templates for quick development
│   └── user1/          # User specific measurement script
│       ├── exp1/
│       └── exp2/
├── config/             # Station configurations
├── drivers/            # Custom instrument drivers (Bluefors temperature API, etc.)
└── lab_utils/          # Shared utility toolbox (Analysis, Plotting, Path management)
```
### Measurement Workflow & Data Management

To ensure a structured and collaborative environment, the lab follows a specific directory convention:

- Experiment Scripts: Users should create a personal directory under experiments/ (e.g., experiments/user_name/) to manage and categorize their measurement scripts.

- Data Storage: Measurement databases and raw files must be stored in the corresponding directory under data/ (e.g., data/user_name/).

- NAS Synchronization: The data/ directory is synchronized via the lab's NAS, allowing seamless data access and sharing across different workstations while keeping the main repository clean.

