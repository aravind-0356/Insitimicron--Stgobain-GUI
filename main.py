# main.py
"""
St Gobain Pi HMI - Main Entry Point
Industrial touchscreen GUI for Raspberry Pi 5 + Waveshare HMI.
"""

import sys
import os

# --- Version Information ---
__version__ = "1.0"
__app_name__ = "ST GOBAIN HMI"

# --- DPI Scaling (neutral on Pi, handles Windows dev scaling) ---
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from theme import GLOBAL_STYLESHEET
from ui_layout import MainWindow


import atexit
from data_logger import log_kiosk_status

if __name__ == "__main__":
    log_kiosk_status("GUI BOOT STARTED")
    atexit.register(lambda: log_kiosk_status("CLEAN SHUTDOWN"))

    QApplication.setAttribute(Qt.AA_SynthesizeMouseForUnhandledTouchEvents, True)
    QApplication.setAttribute(Qt.AA_SynthesizeTouchForUnhandledMouseEvents, False)
    app = QApplication(sys.argv)

    # Apply global corporate stylesheet
    app.setStyleSheet(GLOBAL_STYLESHEET)

    # Set default font (Segoe UI on Windows, falls back to sans-serif on Pi)
    font = QFont("Segoe UI", 12)
    app.setFont(font)

    window = MainWindow()
    window.setWindowTitle(f"{__app_name__} v{__version__}")

    # During development: show maximized.
    # For Pi kiosk deployment: change to window.showFullScreen()
    if os.environ.get("KIOSK_MODE") == "1":
        app.setOverrideCursor(Qt.CursorShape.BlankCursor)
        window.showFullScreen()
    else:
        window.showMaximized()

    sys.exit(app.exec())
