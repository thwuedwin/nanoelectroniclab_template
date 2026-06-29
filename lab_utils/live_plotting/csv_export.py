"""Export QCoDeS datasets to CSV."""

from __future__ import annotations

from pathlib import Path

from qcodes.dataset.data_set_protocol import DataSetProtocol

from lab_utils.paths import DATA_DIR


def default_csv_path(user: str, run_id: int) -> Path:
    """Return ``data/{user}/run_{run_id}.csv``."""
    return DATA_DIR / user / f"run_{run_id}.csv"


def export_dataset_to_csv(dataset: DataSetProtocol, path: Path | str) -> Path:
    """Write dataset to *path* and return the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_pandas_dataframe().reset_index().to_csv(path, index=False)
    return path
