"""QfortMeasNode: qcodes Measurement + Qt live plotting workflow."""

from __future__ import annotations

import sys
import threading
import traceback
from collections.abc import Callable, Mapping
from functools import wraps
from datetime import datetime
from pathlib import Path
from typing import Any

import qcodes as qc
from qcodes.dataset import (
    Measurement,
    initialise_or_create_database_at,
    load_or_create_experiment,
)
from qcodes.dataset.measurements import DataSaver

from lab_utils.live_plotting.csv_export import default_csv_path, export_dataset_to_csv
from lab_utils.live_plotting.metadata import (
    build_record,
    default_record_path,
    save_record,
)
from lab_utils.live_plotting.params import ParameterRegistry
from lab_utils.live_plotting.qtbackend import LivePlotWindow, PlotManager, run_qt_app
from lab_utils.paths import CONFIG_DIR, DATA_DIR


class QfortMeasNode:
    """Orchestrate qcodes measurements with live Qt plotting."""

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = dict(config)
        self._validate_config()

        self.metadata: dict[str, Any] = {}
        self._custom_metadata: dict[str, Any] = {}
        self._exp_func: Callable[[DataSaver], Any] | None = None
        self._cancel_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._window: LivePlotWindow | None = None
        self._measurement_started_at: datetime | None = None
        self._last_point_count = 0
        self._context_lock = threading.Lock()
        self._cache_lock = threading.Lock()

        self.plot = PlotManager()
        self.instruments: dict[str, Any] | None = None
        self._registry: ParameterRegistry | None = None
        self._experiment = None
        self._meas: Measurement | None = None
        self._database_path = self._resolve_database_path()

    @property
    def experiment(self):
        return self._experiment

    @property
    def meas(self) -> Measurement | None:
        return self._meas

    @property
    def database_path(self) -> Path:
        return self._database_path

    @property
    def cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def _validate_config(self) -> None:
        user = self.config.get("user", "")
        if not user or not str(user).strip():
            raise ValueError("config['user'] must be a non-empty string")

        for key in ("exp_name", "sample_name", "parameters", "sweep"):
            if key not in self.config:
                raise ValueError(f"config must include {key!r}")

        has_station = "station_config" in self.config
        has_dict = "instruments" in self.config and isinstance(
            self.config["instruments"], Mapping
        )
        has_station_list = "station_config" in self.config and isinstance(
            self.config.get("instruments"), list
        )

        if not has_dict and not has_station_list:
            raise ValueError(
                "config must include either instruments={...} (dict mode) "
                "or station_config=... with instruments=[...] (YAML mode)"
            )
        if has_station and not has_station_list and has_dict:
            pass  # station_config ignored when dict instruments provided

    def _resolve_database_path(self) -> Path:
        user = self.config["user"]
        user_dir = DATA_DIR / user
        if "database_path" in self.config:
            return Path(self.config["database_path"]).resolve()
        db_name = self.config.get("database_name", "qcodes.db")
        return (user_dir / db_name).resolve()

    def _ensure_measurement_context(self) -> None:
        """Initialize qcodes DB, instruments, and parameter registry (worker thread)."""
        with self._context_lock:
            if self._meas is not None:
                return

            user_dir = DATA_DIR / self.config["user"]
            user_dir.mkdir(parents=True, exist_ok=True)
            self._database_path = self._resolve_database_path()
            qc.config.user.mainfolder = user_dir
            initialise_or_create_database_at(self._database_path)

            self._experiment = load_or_create_experiment(
                experiment_name=self.config["exp_name"],
                sample_name=self.config["sample_name"],
            )
            self._meas = Measurement(
                exp=self._experiment,
                name=self.config.get("measurement_name") or "results",
            )
            self.instruments = self._load_instruments()
            self._registry = ParameterRegistry(
                self.instruments,
                self.config["parameters"],
                self.config["sweep"],
            )

    def _load_instruments(self) -> dict[str, Any]:
        instruments_cfg = self.config.get("instruments")

        if isinstance(instruments_cfg, Mapping):
            return dict(instruments_cfg)

        station_config = self.config.get("station_config")
        if station_config is None:
            raise ValueError("YAML instrument mode requires config['station_config']")

        config_path = Path(station_config)
        if not config_path.is_absolute():
            config_path = (CONFIG_DIR / config_path).resolve()

        use_monitor = self.config.get("use_monitor", False)
        station = qc.Station(config_file=str(config_path), use_monitor=use_monitor)

        if not isinstance(instruments_cfg, list):
            raise ValueError(
                "YAML instrument mode requires config['instruments'] as a list of keys"
            )

        loaded: dict[str, Any] = {}
        for key in instruments_cfg:
            loaded[key] = station.load_instrument(key)
        return loaded

    def param(self, alias: str):
        if self._registry is None:
            raise RuntimeError(
                "Parameters are not available until measurement context is initialized"
            )
        return self._registry.param(alias)

    def param_aliases(self) -> list[str]:
        if self._registry is None:
            return []
        return self._registry.param_aliases()

    def add_metadata(self, key: str, value: Any) -> None:
        self._custom_metadata[key] = value

    def run(self, func: Callable[[DataSaver], Any]) -> Callable[[DataSaver], Any]:
        """Decorator registering ``exp(datasaver)``; does not start measurement."""
        self._exp_func = func
        return func

    def request_cancel(self) -> None:
        self._cancel_event.set()

    def _patch_datasaver_cache_lock(self, datasaver: DataSaver) -> None:
        """Wrap ``add_result`` so cache writes serialize with plot reads."""
        original = datasaver.add_result

        @wraps(original)
        def locked_add_result(*result_tuples):
            with self._cache_lock:
                return original(*result_tuples)

        datasaver.add_result = locked_add_result  # type: ignore[method-assign]

    def _point_count_from_cache(self, dataset: Any) -> int:
        """Return the number of measurement rows (setpoint steps) in *dataset* cache.

        Uses 1-D array lengths from the live cache — not ``dataset.subscribe``'s
        *length*, which counts SQLite INSERT rows (one per dependent tree per point).
        """
        assert self._registry is not None
        cache = dataset.cache.data()

        for alias in self._registry.setpoint_aliases:
            param = self._registry.param(alias)
            key = getattr(param, "register_name", None) or param.name
            count = 0
            for block in cache.values():
                if key not in block:
                    continue
                values = block[key]
                if hasattr(values, "__len__"):
                    count = max(count, len(values))
            if count > 0:
                return count

        count = 0
        for alias in self._registry.dependent_aliases:
            param = self._registry.param(alias)
            y_key = getattr(param, "register_name", None) or param.name
            block = cache.get(y_key)
            if block is None:
                continue
            values = block.get(y_key)
            if values is not None and hasattr(values, "__len__"):
                count = max(count, len(values))
        return count

    def _record_config_snapshot(self) -> dict[str, Any]:
        """Config copy with JSON-safe ``parameters`` paths."""
        snapshot = dict(self.config)
        parameters: dict[str, str] = {}
        for alias, spec in self.config.get("parameters", {}).items():
            if isinstance(spec, str):
                parameters[alias] = spec
            else:
                param = self._registry.param(alias) if self._registry else None
                if param is None:
                    parameters[alias] = alias
                    continue
                instrument = getattr(param, "instrument", None)
                if instrument is not None and getattr(instrument, "name", None):
                    parameters[alias] = f"{instrument.name}.{param.name}"
                else:
                    parameters[alias] = param.name
        snapshot["parameters"] = parameters
        snapshot.pop("instruments", None)
        return snapshot

    def save(self, path: Path | str | None = None) -> Path:
        run_id = self.metadata.get("run_id")
        if run_id is None:
            raise RuntimeError("Cannot save record before a measurement run_id is set")

        timestamp = self._measurement_started_at or datetime.now()
        record = build_record(
            config=self._record_config_snapshot(),
            run_id=run_id,
            database_path=self._database_path,
            custom=self._custom_metadata,
            plot_traces=self.plot.trace_dicts(),
            timestamp=timestamp,
            instruments=self.instruments or {},
        )

        if path is None:
            path = default_record_path(
                self.config["user"],
                run_id,
                self.config["exp_name"],
                measurement_date=timestamp,
            )
        record_path = save_record(record, Path(path))
        self.metadata["record_path"] = str(record_path)
        return record_path

    def start(self) -> int:
        """Open the Qt live-plot window and run the event loop."""
        if self._exp_func is None:
            raise RuntimeError("Register an experiment with @node.run before node.start()")

        return run_qt_app(self)

    def _on_start_requested(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return

        self._cancel_event.clear()
        self._measurement_started_at = datetime.now()
        self._last_point_count = 0
        assert self._window is not None
        self._window.set_measuring(True)
        self._window.set_status("Starting…")

        self._worker = threading.Thread(
            target=self._run_measurement_worker,
            name="QfortMeasNode-worker",
            daemon=True,
        )
        self._worker.start()

    def _on_stop_requested(self) -> None:
        self.request_cancel()
        if self._window is not None:
            self._window.set_status("Stop requested…")

    def _run_measurement_worker(self) -> None:
        assert self._window is not None
        assert self._exp_func is not None

        run_id = -1
        try:
            self._ensure_measurement_context()
            assert self._meas is not None
            assert self._registry is not None

            self._registry.register_on(self._meas)

            with self._meas.run() as datasaver:
                run_id = datasaver.run_id
                self.metadata["run_id"] = run_id
                self._patch_datasaver_cache_lock(datasaver)

                dataset = datasaver.dataset
                bridge = self._window.bridge
                bridge.bind_dataset(dataset)
                dataset.subscribe(bridge.on_results, min_wait=0, min_count=1)

                self._exp_func(datasaver)

                with self._cache_lock:
                    self._last_point_count = self._point_count_from_cache(
                        datasaver.dataset
                    )

                if not self.cancelled:
                    record_path = self.save()
                    dataset.add_metadata("qfort_record_path", str(record_path))
                    csv_path = export_dataset_to_csv(
                        dataset,
                        default_csv_path(self.config["user"], run_id),
                    )
                    self.metadata["csv_path"] = str(csv_path)

            self._window.measurement_finished.emit(run_id, self._last_point_count)
        except Exception:
            tb = traceback.format_exc()
            self._window.measurement_failed.emit(f"Error: {tb.splitlines()[-1]}")
            print(tb, file=sys.stderr)


__all__ = ["QfortMeasNode"]
