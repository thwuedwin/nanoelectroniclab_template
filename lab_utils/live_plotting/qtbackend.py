"""Qt + pyqtgraph live plot window for QfortMeasNode."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

if TYPE_CHECKING:
    from lab_utils.live_plotting.node import QfortMeasNode


AxisSide = Literal["left", "right"]

PLOT_REFRESH_INTERVAL_MS = 500


@dataclass
class PlotSpec:
    """One 1D trace: *x* setpoint alias, *y* dependent alias."""

    x: str
    y: str
    label: str | None = None
    color: str | None = None
    axis: AxisSide = "left"
    trace_id: int = field(default=0, repr=False)


class PlotManager(QtCore.QObject):
    """Plot configuration API exposed as ``node.plot``."""

    trace_added = QtCore.Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._traces: list[PlotSpec] = []
        self._xlabel: str = ""
        self._title: str = ""
        self._next_id = 0
        self._window: LivePlotWindow | None = None

    def _attach_window(self, window: LivePlotWindow) -> None:
        self._window = window
        self.trace_added.connect(
            window._add_curve_for_spec,
            QtCore.Qt.ConnectionType.QueuedConnection,
        )
        for spec in self._traces:
            window._add_curve_for_spec(spec)
        if self._xlabel:
            window._plot_widget.setLabel("bottom", self._xlabel)
        if self._title:
            window._plot_widget.setTitle(self._title)

    @property
    def traces(self) -> tuple[PlotSpec, ...]:
        return tuple(self._traces)

    def add_trace(
        self,
        x: str,
        y: str,
        *,
        label: str | None = None,
        color: str | None = None,
        axis: AxisSide = "left",
    ) -> PlotSpec:
        spec = PlotSpec(
            x=x,
            y=y,
            label=label or y,
            color=color,
            axis=axis,
            trace_id=self._next_id,
        )
        self._next_id += 1
        self._traces.append(spec)
        self.trace_added.emit(spec)
        return spec

    def set_xlabel(self, text: str) -> None:
        self._xlabel = text
        if self._window is not None:
            self._window._plot_widget.setLabel("bottom", text)

    def set_title(self, text: str) -> None:
        self._title = text
        if self._window is not None:
            self._window._plot_widget.setTitle(text)

    def trace_dicts(self) -> list[dict[str, Any]]:
        return [
            {
                "x": spec.x,
                "y": spec.y,
                "label": spec.label,
                "color": spec.color,
                "axis": spec.axis,
            }
            for spec in self._traces
        ]


class PlotBridge(QtCore.QObject):
    """Read live plot arrays from the bound dataset's in-memory cache."""

    def __init__(self, node: QfortMeasNode) -> None:
        super().__init__()
        self._node = node
        self._dataset: Any | None = None

    def bind_dataset(self, dataset: Any) -> None:
        self._dataset = dataset

    def _param_dataset_key(self, param: Any) -> str:
        """qcodes cache keys use ``register_name``, not bare ``Parameter.name``."""
        return getattr(param, "register_name", None) or param.name

    def extract_plot_data(self) -> dict[int, dict[str, np.ndarray]]:
        if self._dataset is None:
            return {}
        updates: dict[int, dict[str, np.ndarray]] = {}

        with self._node._cache_lock:
            param_data = self._dataset.cache.data()
            for spec in self._node.plot.traces:
                y_param = self._node.param(spec.y)
                x_param = self._node.param(spec.x)
                y_key = self._param_dataset_key(y_param)
                x_key = self._param_dataset_key(x_param)

                if y_key not in param_data:
                    continue

                block = param_data[y_key]
                x_arr = np.asarray(block.get(x_key, []), dtype=float, copy=True)
                y_arr = np.asarray(block.get(y_key, []), dtype=float, copy=True)
                n = min(len(x_arr), len(y_arr))
                if n == 0:
                    continue
                updates[spec.trace_id] = {"x": x_arr[:n], "y": y_arr[:n]}

        return updates


class LivePlotWindow(QtWidgets.QMainWindow):
    """Main window with pyqtgraph plot, Start/Stop controls, and status bar."""

    start_requested = QtCore.Signal()
    stop_requested = QtCore.Signal()
    measurement_finished = QtCore.Signal(int, int)
    measurement_failed = QtCore.Signal(str)

    def __init__(self, node: QfortMeasNode) -> None:
        super().__init__()
        self._node = node
        self._curve_items: dict[int, pg.PlotDataItem] = {}
        self._right_view: pg.ViewBox | None = None

        refresh_ms = int(
            node.config.get("plot_refresh_interval_ms", PLOT_REFRESH_INTERVAL_MS)
        )
        self._plot_refresh_timer = QtCore.QTimer(self)
        self._plot_refresh_timer.setInterval(refresh_ms)
        self._plot_refresh_timer.timeout.connect(self._refresh_plot)

        self.setWindowTitle(
            f"QfortMeas — {node.config.get('exp_name', 'experiment')}"
        )
        self.resize(900, 600)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self._plot_widget = pg.PlotWidget()
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.addLegend()
        layout.addWidget(self._plot_widget, stretch=1)

        controls = QtWidgets.QHBoxLayout()
        self._start_btn = QtWidgets.QPushButton("Start")
        self._stop_btn = QtWidgets.QPushButton("Stop")
        self._stop_btn.setEnabled(False)
        controls.addWidget(self._start_btn)
        controls.addWidget(self._stop_btn)
        controls.addStretch(1)
        self._status_label = QtWidgets.QLabel("Ready")
        controls.addWidget(self._status_label)
        layout.addLayout(controls)

        self._start_btn.clicked.connect(self.start_requested.emit)
        self._stop_btn.clicked.connect(self.stop_requested.emit)
        self.measurement_finished.connect(self.show_finished)
        self.measurement_failed.connect(self._on_measurement_failed)

        self._bridge = PlotBridge(node)

        node.plot._attach_window(self)

    @property
    def bridge(self) -> PlotBridge:
        return self._bridge

    def _add_curve_for_spec(self, spec: PlotSpec) -> None:
        if spec.trace_id in self._curve_items:
            return
        plot_item = self._plot_widget.getPlotItem()
        pen = pg.mkPen(spec.color) if spec.color else None

        if spec.axis == "right":
            if self._right_view is None:
                self._right_view = pg.ViewBox()
                plot_item.showAxis("right")
                plot_item.scene().addItem(self._right_view)
                plot_item.getAxis("right").linkToView(self._right_view)
                self._right_view.setXLink(plot_item)
            curve = pg.PlotDataItem([], [], pen=pen, name=spec.label)
            self._right_view.addItem(curve)
        else:
            curve = self._plot_widget.plot([], [], pen=pen, name=spec.label)

        self._curve_items[spec.trace_id] = curve

    def _refresh_plot(self) -> None:
        payload = self._bridge.extract_plot_data()
        point_count = 0
        for trace_id, arrays in payload.items():
            curve = self._curve_items.get(trace_id)
            if curve is None:
                continue
            curve.setData(arrays["x"], arrays["y"])
            point_count = max(point_count, len(arrays["y"]))

        if point_count == 0 and self._bridge._dataset is not None:
            with self._node._cache_lock:
                point_count = self._node._point_count_from_cache(
                    self._bridge._dataset
                )

        run_id = self._node.metadata.get("run_id", "—")
        self._status_label.setText(f"Run ID: {run_id} | Points: {point_count}")

    def set_measuring(self, active: bool) -> None:
        if active:
            self._plot_refresh_timer.start()
        else:
            self._plot_refresh_timer.stop()
        self._start_btn.setEnabled(not active)
        self._stop_btn.setEnabled(active)

    def set_status(self, text: str) -> None:
        self._status_label.setText(text)

    @QtCore.Slot(int, int)
    def show_finished(self, run_id: int, point_count: int) -> None:
        self._plot_refresh_timer.stop()
        self._refresh_plot()
        self.set_measuring(False)
        self._status_label.setText(f"Run ID: {run_id} | Points: {point_count} | Done")

    @QtCore.Slot(str)
    def _on_measurement_failed(self, message: str) -> None:
        self._plot_refresh_timer.stop()
        self.set_measuring(False)
        self._status_label.setText(message)


def run_qt_app(node: QfortMeasNode) -> int:
    """Create QApplication, show the live-plot window, and run the event loop."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])

    window = LivePlotWindow(node)
    window.start_requested.connect(node._on_start_requested)
    window.stop_requested.connect(node._on_stop_requested)
    node._window = window
    window.show()
    return app.exec()


__all__ = [
    "LivePlotWindow",
    "PLOT_REFRESH_INTERVAL_MS",
    "PlotBridge",
    "PlotManager",
    "PlotSpec",
    "run_qt_app",
]
