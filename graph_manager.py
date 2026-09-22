import numpy as np
import collections
import pyqtgraph as pg
from PySide6.QtWidgets import QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QEvent, QObject
from PySide6.QtGui import QFont

from constants import PRIMARY_COLOR, ACCENT_COLOR

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
    Manages the real-time plot widget with dual y-axes (Displacement and Temperature).

    Full in-memory buffer stores ALL (time, temp, disp) tuples for the
    current test — cleared only when a new test starts.
    A lightweight downsampling step keeps rendering fast for edge cases.
    """

    def __init__(self):
        # ---------- Full in-memory buffer ----------
        self._buffer_time = collections.deque(maxlen=100000)
        self._buffer_temp = collections.deque(maxlen=100000)
        self._buffer_disp = collections.deque(maxlen=100000)

        # ---------- Container widget ----------
        self._container = QWidget()
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)

        # ---------- Plot widget ----------
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        
        self.p1 = self.plot_widget.getPlotItem()
        self.p1.setTitle("Live Telemetry: Displacement & Temperature vs Time", color='#2c2f33', size='18pt')
        self.p1.setLabel('bottom', "Time (s)", color='#2c2f33', size='16pt')
        self.p1.setLabel('left', "Displacement (mm)", color='#2980b9', size='16pt')
        self.p1.showGrid(x=True, y=True, alpha=0.3)
        
        # Dual axis for Temperature
        self.p2 = pg.ViewBox()
        self.p1.showAxis('right')
        self.p1.scene().addItem(self.p2)
        self.p1.getAxis('right').linkToView(self.p2)
        self.p2.setXLink(self.p1)
        self.p1.getAxis('right').setLabel("Temperature (°C)", color='#e74c3c', size='16pt')

        def updateViews():
            self.p2.setGeometry(self.p1.vb.sceneBoundingRect())
            self.p2.linkedViewChanged(self.p1.vb, self.p2.XAxis)
        
        updateViews()
        self.p1.vb.sigResized.connect(updateViews)

        # Thick, more visible axes
        pen_disp = pg.mkPen(color='#2980b9', width=2)
        pen_temp = pg.mkPen(color='#e74c3c', width=2)
        pen_bottom = pg.mkPen(color='#2c2f33', width=2)
        
        self.p1.getAxis('left').setPen(pen_disp)
        self.p1.getAxis('left').setTextPen(pen_disp)
        self.p1.getAxis('bottom').setPen(pen_bottom)
        self.p1.getAxis('bottom').setTextPen(pen_bottom)
        self.p1.getAxis('right').setPen(pen_temp)
        self.p1.getAxis('right').setTextPen(pen_temp)

        # Increase tick font size for readability on touchscreens
        font = QFont()
        font.setPixelSize(14)
        self.p1.getAxis('left').setStyle(tickFont=font)
        self.p1.getAxis('bottom').setStyle(tickFont=font)
        self.p1.getAxis('right').setStyle(tickFont=font)

        # Legend
        self.legend = self.p1.addLegend(offset=(60, 10))

        # Hide default auto-range button ("A") and add custom "Reset" button
        self.p1.hideButtons()
        self.reset_btn = QPushButton("Reset", self.plot_widget)
        self.reset_btn.setStyleSheet("""
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
        self.reset_btn.setFixedSize(50, 22)
        self.reset_btn.clicked.connect(self._reset_view)

        # Store reference and set up resize handler
        self.plot_widget._custom_reset_btn = self.reset_btn
        filter_obj = PlotResizeFilter(self.plot_widget)
        self.plot_widget.installEventFilter(filter_obj)
        self.plot_widget._resize_filter = filter_obj

        # Curves
        self.curve_disp = self.p1.plot(pen=pg.mkPen(color='#2980b9', width=3), name="Displacement")
        self.curve_temp = pg.PlotDataItem(pen=pg.mkPen(color='#e74c3c', width=3), name="Temperature")
        self.p2.addItem(self.curve_temp)
        self.legend.addItem(self.curve_temp, "Temperature")

        container_layout.addWidget(self.plot_widget)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_widget(self):
        """Returns the container widget to add to a layout."""
        return self._container

    def set_dimensions(self, span_length, width, height):
        """Set sample dimensions (kept for signature compatibility)."""
        pass

    def append_data(self, time_s, temp_c, disp_mm):
        """
        Append a new tared data point to the full buffer.
        Call render() separately to update the UI.
        """
        self._buffer_time.append(time_s)
        self._buffer_temp.append(temp_c)
        self._buffer_disp.append(disp_mm)

    def render(self):
        """Render the dual-axis graph with lightweight downsampling if needed."""
        n = len(self._buffer_time)
        if n == 0:
            self.curve_disp.setData([], [])
            self.curve_temp.setData([], [])
            return

        x = list(self._buffer_time)
        y_disp = list(self._buffer_disp)
        y_temp = list(self._buffer_temp)

        # Downsample for render if buffer is huge (worst-case safety net)
        if n > _MAX_RENDER_POINTS:
            step = n // _MAX_RENDER_POINTS
            x = x[::step]
            y_disp = y_disp[::step]
            y_temp = y_temp[::step]

        self.curve_disp.setData(x, y_disp)
        self.curve_temp.setData(x, y_temp)

    def clear(self):
        """Clear all buffered data and reset the plot. Call at start_test()."""
        self._buffer_time.clear()
        self._buffer_temp.clear()
        self._buffer_disp.clear()
        self.curve_disp.setData([], [])
        self.curve_temp.setData([], [])

    def _reset_view(self):
        """Reset view range for both axes."""
        self.p1.vb.enableAutoRange(x=True, y=True)
        self.p2.enableAutoRange(x=False, y=True)
