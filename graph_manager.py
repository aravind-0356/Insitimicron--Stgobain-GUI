# graph_manager.py
"""
PyQtGraph graph manager for the Pi HMI.
Styled to match GUI_v3.1/gui_panels.py -> setup_plot_style():
  - White background, dark axis text (#2c2f33)
  - Thick axis pens, large tick fonts
  - Custom "Reset" button on each plot
  - Corporate PRIMARY_COLOR for data curves
  - Three graph modes: Load vs Disp, Load vs Time, Disp vs Time
  - Segmented toggle buttons to switch between modes
  - Full in-memory buffer for seamless backfill on mode switch
  - Downsampling for worst-case long tests
"""

import numpy as np
import collections
import pyqtgraph as pg
from PySide6.QtWidgets import QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QEvent, QObject
from PySide6.QtGui import QFont

from constants import PRIMARY_COLOR, ACCENT_COLOR

# Graph mode constants
MODE_LOAD_VS_DISP = 0
MODE_LOAD_VS_TIME = 1
MODE_DISP_VS_TIME = 2
MODE_STRESS_VS_STRAIN = 3

_MODE_CONFIG = {
    MODE_LOAD_VS_DISP: {
        "title": "Load vs Displacement",
        "xlabel": "Displacement (mm)",
        "ylabel": "Load (N)",
        "btn_label": "Load vs Disp",
    },
    MODE_LOAD_VS_TIME: {
        "title": "Load vs Time",
        "xlabel": "Time (s)",
        "ylabel": "Load (N)",
        "btn_label": "Load vs Time",
    },
    MODE_DISP_VS_TIME: {
        "title": "Displacement vs Time",
        "xlabel": "Time (s)",
        "ylabel": "Displacement (mm)",
        "btn_label": "Disp vs Time",
    },
    MODE_STRESS_VS_STRAIN: {
        "title": "Stress vs Strain",
        "xlabel": "Strain",
        "ylabel": "Stress (MPa)",
        "btn_label": "Stress vs Strain",
    },
}

# Downsample: keep at most this many points per render (performance safety net)
_MAX_RENDER_POINTS = 5000


class PlotResizeFilter(QObject):
    """Event filter to reposition the Reset button when the plot is resized."""
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize:
            if hasattr(obj, '_custom_reset_btn'):
                obj._custom_reset_btn.move(5, obj.height() - 30)
        return super().eventFilter(obj, event)


def setup_plot_style(plot, title, xlabel, ylabel):
    """
    Apply professional plot styling matching GUI_v3.1 exactly.
    White background, dark text, thick axes, custom Reset button.
    """
    plot.setBackground('w')
    plot.setTitle(title, color='#2c2f33', size='18pt')
    plot.setLabel('left', ylabel, color='#2c2f33', size='16pt')
    plot.setLabel('bottom', xlabel, color='#2c2f33', size='16pt')
    plot.showGrid(x=True, y=True, alpha=0.3)

    # Thick, more visible axes
    pen = pg.mkPen(color='#2c2f33', width=2)
    plot.getAxis('left').setPen(pen)
    plot.getAxis('bottom').setPen(pen)
    plot.getAxis('left').setTextPen(pen)
    plot.getAxis('bottom').setTextPen(pen)

    # Increase tick font size for readability on touchscreens
    font = QFont()
    font.setPixelSize(14)
    plot.getAxis('left').setStyle(tickFont=font)
    plot.getAxis('bottom').setStyle(tickFont=font)

    # Hide default auto-range button ("A") and add custom "Reset" button
    plot_item = plot.getPlotItem()
    plot_item.hideButtons()

    reset_btn = QPushButton("Reset", plot)
    reset_btn.setStyleSheet("""
        QPushButton {
            background-color: rgba(255, 255, 255, 0.9);
            border: 1px solid #bdc3c7;
            border-radius: 3px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: bold;
            color: #2c3e50;
        }
        QPushButton:hover {
            background-color: #ecf0f1;
            border-color: #005b7f;
        }
    """)
    reset_btn.setFixedSize(50, 22)
    reset_btn.move(5, plot.height() - 30)
    reset_btn.clicked.connect(
        lambda: plot.getPlotItem().getViewBox().enableAutoRange(x=True, y=True)
    )

    # Store reference and set up resize handler
    plot._custom_reset_btn = reset_btn
    filter_obj = PlotResizeFilter(plot)
    plot.installEventFilter(filter_obj)
    plot._resize_filter = filter_obj  # prevent garbage collection


class GraphManager:
    """
    Manages the real-time plot widget with three switchable graph modes.

    Full in-memory buffer stores ALL (time, load, disp) tuples for the
    current test — cleared only when a new test starts.  When the user
    switches modes the entire buffer is re-plotted instantly.  A
    lightweight downsampling step keeps rendering fast for edge cases.
    """

    # Segmented-button style helpers
    _BTN_ACTIVE = f"""
        QPushButton {{
            background-color: {PRIMARY_COLOR};
            border: none; font-size: 18px; font-weight: bold;
            color: white; padding: 8px 12px;
            border-bottom: 3px solid #002233;
        }}
    """
    _BTN_INACTIVE = """
        QPushButton {
            background-color: #ecf0f1;
            border: 1px solid #bdc3c7; font-size: 18px; font-weight: bold;
            color: #7f8c8d; padding: 8px 12px;
        }
        QPushButton:hover {
            background-color: #dfe6e9;
        }
    """

    def __init__(self):
        self._mode = MODE_LOAD_VS_DISP

        # ---------- Sample Dimensions ----------
        self._span_length = None
        self._width = None
        self._height = None

        # ---------- Full in-memory buffer ----------
        # Stores points since the last start_test() call (capped for memory safety)
        # Each element: (time_s, load_N, disp_mm) — all tared values
        self._buffer_time = collections.deque(maxlen=100000)
        self._buffer_load = collections.deque(maxlen=100000)
        self._buffer_disp = collections.deque(maxlen=100000)

        # ---------- Container widget ----------
        self._container = QWidget()
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)

        # ---------- Segmented toggle buttons ----------
        btn_row = QHBoxLayout()
        btn_row.setSpacing(0)
        btn_row.setContentsMargins(0, 4, 0, 4)
        btn_row.setAlignment(Qt.AlignVCenter)

        lbl = QLabel("Choose Graph Type :")
        lbl.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #2c3e50; "
            "background-color: transparent; margin-right: 10px;"
        )
        btn_row.addWidget(lbl)

        self._mode_buttons = []
        for mode, cfg in _MODE_CONFIG.items():
            btn = QPushButton(cfg["btn_label"])
            btn.setFixedHeight(48)
            btn.clicked.connect(lambda checked=False, m=mode: self._switch_mode(m))
            # Apply rounded corners only on the outer edges
            if mode == MODE_LOAD_VS_DISP:
                btn.setStyleSheet(self._BTN_ACTIVE + "QPushButton { border-radius: 6px; border-top-right-radius: 0; border-bottom-right-radius: 0; }")
            elif mode == MODE_STRESS_VS_STRAIN:
                btn.setStyleSheet(self._BTN_INACTIVE + "QPushButton { border-radius: 6px; border-top-left-radius: 0; border-bottom-left-radius: 0; }")
            else:
                btn.setStyleSheet(self._BTN_INACTIVE + "QPushButton { border-radius: 0; }")
            self._mode_buttons.append(btn)
            btn_row.addWidget(btn)

        btn_row.addStretch()
        container_layout.addLayout(btn_row)

        # ---------- Plot widget ----------
        self.plot_widget = pg.PlotWidget()
        cfg0 = _MODE_CONFIG[MODE_LOAD_VS_DISP]
        setup_plot_style(self.plot_widget, cfg0["title"], cfg0["xlabel"], cfg0["ylabel"])

        pen = pg.mkPen(color=PRIMARY_COLOR, width=3)
        self.curve = self.plot_widget.plot(pen=pen)

        container_layout.addWidget(self.plot_widget)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_widget(self):
        """Returns the container widget (buttons + plot) to add to a layout."""
        return self._container

    def set_dimensions(self, span_length, width, height):
        """Set sample dimensions for Stress/Strain calculations."""
        self._span_length = span_length
        self._width = width
        self._height = height

    def append_data(self, time_s, load_n, disp_mm):
        """
        Append a new tared data point to the full buffer.
        Call render() separately to update the UI.
        """
        self._buffer_time.append(time_s)
        self._buffer_load.append(load_n)
        self._buffer_disp.append(disp_mm)

    def render(self):
        """Render only the current mode"""
        self._render_current_mode()

    def clear(self):
        """Clear all buffered data and reset the plot. Call at start_test()."""
        self._buffer_time.clear()
        self._buffer_load.clear()
        self._buffer_disp.clear()
        self.curve.setData([], [])

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _switch_mode(self, mode):
        """Switch the active graph mode and instantly re-plot from buffer."""
        self._mode = mode
        cfg = _MODE_CONFIG[mode]

        # Update axis labels and title
        self.plot_widget.setTitle(cfg["title"], color='#2c2f33', size='18pt')
        self.plot_widget.setLabel('left', cfg["ylabel"], color='#2c2f33', size='16pt')
        self.plot_widget.setLabel('bottom', cfg["xlabel"], color='#2c2f33', size='16pt')

        # Re-style buttons
        for i, btn in enumerate(self._mode_buttons):
            is_active = (i == mode)
            base = self._BTN_ACTIVE if is_active else self._BTN_INACTIVE
            if i == 0:
                corner = "QPushButton { border-radius: 6px; border-top-right-radius: 0; border-bottom-right-radius: 0; }"
            elif i == len(self._mode_buttons) - 1:
                corner = "QPushButton { border-radius: 6px; border-top-left-radius: 0; border-bottom-left-radius: 0; }"
            else:
                corner = "QPushButton { border-radius: 0; }"
            btn.setStyleSheet(base + corner)

        # Reset view auto-range then re-plot everything from buffer
        self.plot_widget.getPlotItem().getViewBox().enableAutoRange(x=True, y=True)
        self._render_current_mode()

    def _render_current_mode(self):
        """
        Plot the correct X/Y arrays for the current mode.
        Applies lightweight downsampling if the buffer is very large.
        """
        n = len(self._buffer_time)
        if n == 0:
            self.curve.setData([], [])
            return

        # Select arrays based on mode
        if self._mode == MODE_LOAD_VS_DISP:
            x = self._buffer_disp
            y = self._buffer_load
        elif self._mode == MODE_LOAD_VS_TIME:
            x = self._buffer_time
            y = self._buffer_load
        elif self._mode == MODE_DISP_VS_TIME:
            x = self._buffer_time
            y = self._buffer_disp
        elif self._mode == MODE_STRESS_VS_STRAIN:
            # Check if dimensions are valid
            if (self._span_length and self._width and self._height and 
                self._span_length > 0 and self._width > 0 and self._height > 0):
                L = self._span_length
                w = self._width
                h = self._height
                x = [(6 * d * h) / (L**2) for d in self._buffer_disp]
                y = [(3 * f * L) / (2 * w * (h**2)) for f in self._buffer_load]
            else:
                x = []
                y = []

        # Downsample for render if buffer is huge (worst-case safety net)
        if n > _MAX_RENDER_POINTS:
            step = n // _MAX_RENDER_POINTS
            x = x[::step]
            y = y[::step]

        self.curve.setData(x, y)
