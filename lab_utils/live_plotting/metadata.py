"""JSON sidecar records linking qcodes runs to experiment config snapshots."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from lab_utils.paths import DATA_DIR


def default_record_path(
    user: str,
    run_id: int,
    exp_name: str,
    *,
    measurement_date: datetime | None = None,
) -> Path:
    """Return ``data/{user}/records/{YYYY-MM-DD}/{run_id}_{exp_name}.json``."""
    date_str = (measurement_date or datetime.now()).strftime("%Y-%m-%d")
    records_dir = DATA_DIR / user / "records" / date_str
    records_dir.mkdir(parents=True, exist_ok=True)
    safe_exp = _safe_filename_part(exp_name) or "experiment"
    return records_dir / f"{run_id}_{safe_exp}.json"


def _safe_filename_part(value: str) -> str:
    return value.replace("/", "_").replace("\\", "_").strip()


def serialize_instruments(
    instruments: Mapping[str, Any],
    parameter_paths: Mapping[str, str],
) -> dict[str, dict[str, str | None]]:
    """Serialize instrument instances to JSON-safe dicts (no live objects)."""
    serialized: dict[str, dict[str, str | None]] = {}
    for key, instrument in instruments.items():
        address = getattr(instrument, "address", None)
        if address is None:
            address = getattr(instrument, "visa_handle", None)
        if address is not None and not isinstance(address, str):
            address = str(address)
        serialized[key] = {
            "qcodes_name": getattr(instrument, "name", key),
            "address": address,
        }
    return serialized


def build_record(
    *,
    config: Mapping[str, Any],
    run_id: int,
    database_path: Path | str,
    custom: Mapping[str, Any] | None = None,
    exp_source: str = "",
    plot_traces: list[Mapping[str, Any]] | None = None,
    timestamp: datetime | None = None,
    instruments: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable measurement record dict."""
    ts = timestamp or datetime.now()
    parameters = dict(config.get("parameters", {}))
    instruments_map = instruments if instruments is not None else config.get("instruments", {})

    record: dict[str, Any] = {
        "user": config["user"],
        "exp_name": config["exp_name"],
        "sample_name": config.get("sample_name", ""),
        "measurement_name": config.get("measurement_name", ""),
        "description": config.get("description", ""),
        "exp_source": exp_source,
        "run_id": run_id,
        "timestamp": ts.isoformat(timespec="seconds"),
        "database": str(database_path),
        "parameters": parameters,
        "sweep": dict(config.get("sweep", {})),
        "custom": dict(custom or {}),
    }

    if isinstance(instruments_map, Mapping):
        record["instruments"] = serialize_instruments(instruments_map, parameters)
    elif config.get("station_config"):
        record["station_config"] = str(config["station_config"])
        record["instrument_keys"] = list(config.get("instruments", []))

    if plot_traces:
        record["plot_traces"] = [dict(trace) for trace in plot_traces]

    return record


def save_record(record: Mapping[str, Any], path: Path) -> Path:
    """Write *record* to *path* and return the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def load_record(path: Path | str) -> dict[str, Any]:
    """Load a sidecar JSON record."""
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


__all__ = [
    "build_record",
    "default_record_path",
    "load_record",
    "save_record",
    "serialize_instruments",
]
