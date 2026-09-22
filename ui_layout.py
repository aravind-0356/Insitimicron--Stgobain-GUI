# ui_layout.py
"""
Main window layout for the Pi HMI.
Corporate styling matching InsituMicron GUI_v3.1:
  - Light sidebar (#ecf0f1) with PRIMARY_COLOR selected items
  - White content area with professional typography
  - Touch-friendly button sizes (min 60px height)
  - No emojis — this is industrial software
  - Integrated data logging (Phase 2) with history/export UI
  - Virtual numpad/keyboard for touchscreen input (no physical keyboard)
"""

import os
import platform
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QStackedWidget, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QGroupBox, QFormLayout, QLineEdit, QAbstractItemView,
    QScrollArea
)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QPixmap, QFont

from constants import PRIMARY_COLOR, ACCENT_COLOR
from graph_manager import GraphManager, setup_plot_style
from serial_manager import SerialManager
from data_logger import DataLogger
from virtual_keyboard import NumpadDialog, TextInputDialog
from settings_manager import SettingsManager

import pyqtgraph as pg

# =========================================================
# ADMIN CREDENTIALS  — change here to reset password
# =========================================================
_ADMIN_ID   = "admin"
_ADMIN_PASS = "insitumicron"


# =========================================================
# HELPER: Touch-friendly read-only input field with popup editor
# =========================================================
class TouchLineEdit(QLineEdit):
    """
    A read-only QLineEdit that opens a virtual keyboard/numpad on tap.
    Used for touchscreen HMIs without a physical keyboard.
    """

    def __init__(self, parent=None, mode="text", title="", unit=""):
        super().__init__(parent)
        self.setReadOnly(True)
        self._mode = mode      # "text" or "numeric"
        self._title = title
        self._unit = unit
        self.setStyleSheet(
            "font-size: 20px; padding: 8px; border: 1px solid #bdc3c7; "
            "border-radius: 6px; background-color: #f4f6f7; color: #2c3e50;"
        )

    def mousePressEvent(self, event):
        """Open the appropriate virtual keyboard on tap."""
        guard = getattr(self, '_admin_guard', None)
        if guard is not None:
            if not guard():
                return
                
        if self._mode == "numeric":
            dlg = NumpadDialog(
                self.window(), title=self._title, unit=self._unit,
                current_value=self.text()
            )
            if dlg.exec() == NumpadDialog.Accepted:
                val = dlg.get_value()
                if val is not None:
                    self.setText(str(val))
        else:
            dlg = TextInputDialog(
                self.window(), title=self._title,
                current_value=self.text()
            )
            if dlg.exec() == TextInputDialog.Accepted:
                val = dlg.get_value()
                if val is not None:
                    self.setText(val)
        super().mousePressEvent(event)


from PySide6.QtWidgets import QTextEdit

class TouchTextEdit(QTextEdit):
    """
    A read-only QTextEdit that opens a virtual keyboard on tap.
    """
    def __init__(self, parent=None, title=""):
        super().__init__(parent)
        self.setReadOnly(True)
        self._title = title
        self.setStyleSheet(
            "font-size: 18px; padding: 8px; border: 1px solid #bdc3c7; "
            "border-radius: 6px; background-color: #f4f6f7; color: #2c3e50;"
        )

    def mousePressEvent(self, event):
        dlg = TextInputDialog(
            self.window(), title=self._title,
            current_value=self.toPlainText()
        )
        if dlg.exec() == TextInputDialog.Accepted:
            val = dlg.get_value()
            if val is not None:
                self.setText(val)
        super().mousePressEvent(event)

# =========================================================
# STANDARD BUTTON STYLE (used for secondary/action buttons)
# =========================================================
_BTN_STYLE_PRIMARY = f"""
    QPushButton {{
        background-color: {PRIMARY_COLOR};
        border: none; font-size: 16px; font-weight: bold;
        border-radius: 6px; color: white; padding: 8px 16px;
        border-bottom: 4px solid #002233;
        margin-top: 0px;
    }}
    QPushButton:pressed {{
        background-color: #004a66;
        border-bottom: 0px solid #002233;
        margin-top: 4px;
    }}
    QPushButton:hover {{ background-color: {ACCENT_COLOR}; }}
    QPushButton:disabled {{ background-color: #dfe6e9; border-bottom: 4px solid #b2bec3; color: #b2bec3; }}
"""

_BTN_STYLE_ACCENT = f"""
    QPushButton {{
        background-color: {ACCENT_COLOR};
        border: none; font-size: 16px; font-weight: bold;
        border-radius: 6px; color: white; padding: 8px 16px;
        border-bottom: 4px solid #006680;
        margin-top: 0px;
    }}
    QPushButton:pressed {{
        background-color: #0097b5;
        border-bottom: 0px solid #006680;
        margin-top: 4px;
    }}
    QPushButton:hover {{ background-color: #33b5d5; }}
"""

_BTN_STYLE_DANGER = """
    QPushButton {
        background-color: #e74c3c;
        border: none; font-size: 16px; font-weight: bold;
        border-radius: 6px; color: white; padding: 8px 16px;
        border-bottom: 4px solid #900000;
        margin-top: 0px;
    }
    QPushButton:pressed {
        background-color: #c0392b;
        border-bottom: 0px solid #900000;
        margin-top: 4px;
    }
    QPushButton:hover { background-color: #ec7063; }
    QPushButton:disabled { background-color: #dfe6e9; border-bottom: 4px solid #b2bec3; color: #b2bec3; }
"""



from PySide6.QtWidgets import QDialog
from PySide6.QtCore import QCoreApplication

class FileBrowserDialog(QDialog):
    def __init__(self, data_logger, parent=None):
        super().__init__(parent)
        self.data_logger = data_logger
        self.selected_test_ids = []
        
        self.setWindowTitle("Browse Saved Tests")
        self.setMinimumSize(800, 480)
        self.resize(1050, 700)
        
        layout = QVBoxLayout(self)
        
        # Test Table
        self.test_table = QTableWidget()
        self.test_table.setColumnCount(5)
        self.test_table.setHorizontalHeaderLabels([
            "Record ID", "Test Name", "Sample ID", "Test No.", "Duration"
        ])
        self.test_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.test_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Option A: MultiSelection (every tap toggles)
        self.test_table.setSelectionMode(QAbstractItemView.MultiSelection)
        self.test_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.test_table.verticalHeader().setVisible(False)
        self.test_table.verticalHeader().setDefaultSectionSize(50)
        self.test_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.test_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.test_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.test_table.setStyleSheet("""
            QTableWidget {
                font-size: 18px;
                gridline-color: #ecf0f1;
            }
            QTableWidget::item:selected {
                background-color: #d6eaf8;
                color: #2c3e50;
            }
            QHeaderView::section {
                background-color: #ecf0f1;
                font-weight: bold;
                padding: 12px;
                border: none;
                border-bottom: 2px solid #bdc3c7;
                font-size: 18px;
            }
            QScrollBar:vertical {
                border: none;
                background: #ecf0f1;
                width: 60px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #bdc3c7;
                min-height: 80px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #95a5a6;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        layout.addWidget(self.test_table)
        
        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        
        self.btn_load = QPushButton("Load into Graph")
        self.btn_load.setFixedHeight(60)
        self.btn_load.setStyleSheet(_BTN_STYLE_PRIMARY)
        self.btn_load.clicked.connect(self.accept_load)
        btn_row.addWidget(self.btn_load)
        
        self.btn_export = QPushButton("Export to USB")
        self.btn_export.setFixedHeight(60)
        self.btn_export.setStyleSheet(_BTN_STYLE_ACCENT)
        self.btn_export.clicked.connect(self.export_usb)
        btn_row.addWidget(self.btn_export)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setFixedHeight(60)
        self.btn_delete.setStyleSheet(_BTN_STYLE_DANGER)
        self.btn_delete.clicked.connect(self.delete_tests)
        btn_row.addWidget(self.btn_delete)
        
        self.btn_cancel = QPushButton("Close")
        self.btn_cancel.setFixedHeight(60)
        self.btn_cancel.setStyleSheet(_BTN_STYLE_PRIMARY)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_row)
        
        self.refresh_list()
        
    def refresh_list(self):
        tests = self.data_logger.get_all_tests()
        self.test_table.setRowCount(len(tests))

        for row, test in enumerate(tests):
            def create_item(text):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignCenter)
                return item

            self.test_table.setItem(row, 0, create_item(test["test_id"]))
            self.test_table.setItem(row, 1, create_item(test["name"]))
            self.test_table.setItem(row, 2, create_item(test.get("sample_name", "")))
            self.test_table.setItem(row, 3, create_item(test.get("test_number", "")))

            dur = test["duration_s"]
            dur_str = f"{dur:.1f}s" if dur is not None else "Running..."
            self.test_table.setItem(row, 4, create_item(dur_str))
            
    def _get_selected_test_ids(self):
        selected_rows = set()
        for item in self.test_table.selectedItems():
            selected_rows.add(item.row())
        test_ids = []
        for row in sorted(selected_rows):
            id_item = self.test_table.item(row, 0)
            if id_item:
                test_ids.append(int(id_item.text()))
        return test_ids
        
    def accept_load(self):
        self.selected_test_ids = self._get_selected_test_ids()
        if not self.selected_test_ids:
            QMessageBox.warning(self, "No Selection", "Please select one or more tests.")
            return
        if len(self.selected_test_ids) > 5:
            QMessageBox.warning(self, "Limit Exceeded", "You can only compare a maximum of 5 tests at a time.\nPlease deselect some tests.")
            return
        self.accept()
        
    def export_usb(self):
        test_ids = self._get_selected_test_ids()
        if not test_ids:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("No Selection")
            msg.setText("Please select one or more tests to export.")
            msg.addButton("OK", QMessageBox.AcceptRole)
            msg.exec()
            return
            
        from usb_utils import detect_usb_drive
        folder = detect_usb_drive()
        
        if not folder:
            QMessageBox.critical(self, "No USB Detected", "No USB drive (Pendrive) was detected.\nPlease insert one and try again.")
            return
            
        # Custom message box to avoid OS-level emojis on standard buttons
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Export")
        msg_box.setText(f"USB drive detected at:\n{folder}\n\nDo you want to export the selected test(s) to this drive?")
        btn_yes = msg_box.addButton("Yes", QMessageBox.YesRole)
        btn_no = msg_box.addButton("No", QMessageBox.NoRole)
        msg_box.exec()
        
        if msg_box.clickedButton() != btn_yes:
            return
            
        from PySide6.QtWidgets import QProgressDialog
        progress = QProgressDialog("Exporting data to USB...", "Cancel", 0, len(test_ids), self)
        progress.setCancelButton(QPushButton("Cancel"))
        progress.setWindowTitle("Exporting")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        exported = 0
        try:
            for i, test_id in enumerate(test_ids):
                if progress.wasCanceled():
                    break
                
                progress.setValue(i)
                QCoreApplication.processEvents()
                
                tests = self.data_logger.get_all_tests()
                name = f"Test_{test_id}"
                for t in tests:
                    if t["test_id"] == test_id:
                        name = t["name"].replace(" ", "_").replace("/", "-")
                        break
                path = os.path.join(folder, f"{name}.csv")
                rows = self.data_logger.export_test_to_csv(test_id, path, yield_callback=QCoreApplication.processEvents)
                if rows > 0:
                    exported += 1
                elif rows == 0:
                    QMessageBox.warning(self, "No Data", f"Test '{name}' has no data points and was skipped.")
                    
            progress.setValue(len(test_ids))
            
            # On Linux (Raspberry Pi), force the OS to flush all pending USB writes 
            # so the user can immediately pull the drive out without data loss.
            if platform.system() == 'Linux':
                os.system("sync")
                
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Export Complete")
            msg.setText(f"Exported {exported} test(s) to:\n{folder}\n\nIt is now safe to remove the USB drive.")
            msg.addButton("OK", QMessageBox.AcceptRole)
            msg.exec()
        except Exception as e:
            progress.cancel()
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Export Error")
            msg.setText(f"An error occurred during export:\n{str(e)}")
            msg.addButton("OK", QMessageBox.AcceptRole)
            msg.exec()
        self.test_table.clearSelection()
        
    def delete_tests(self):
        test_ids = self._get_selected_test_ids()
        if not test_ids:
            QMessageBox.warning(self, "No Selection", "Please select tests to delete.")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to permanently delete {len(test_ids)} test(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        for test_id in test_ids:
            self.data_logger.delete_test(test_id)
        self.refresh_list()
        QMessageBox.information(self, "Deleted", f"Deleted {len(test_ids)} test(s).")

# End of FileBrowserDialog
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HMI System")
        self.resize(1024, 600)

        self.settings = SettingsManager()
        
        self.serial_manager = SerialManager()
        self.data_logger = DataLogger()
        self._is_test_running = False
        self.load_offset = 0.0
        self.disp_offset = 0.0
        self.test_start_time = 0.0

        # Auto Start/Stop state
        self._auto_start_stop_enabled = False
        self._auto_peak_load = 0.0
        self._auto_armed = False
        self._AUTO_START_THRESHOLD = self.settings.get("auto_start_threshold", self.settings.get("break_arm_threshold", 20.0))
        self._AUTO_STOP_DROP_FRACTION = self.settings.get("auto_stop_drop_fraction", self.settings.get("break_drop_fraction", 0.40))

        # Contact-Triggered Displacement (CTD) state
        self._ctd_enabled = self.settings.get("ctd_enabled", False)
        self._ctd_threshold = self.settings.get("ctd_threshold", 10.0)
        self._ctd_state = "IDLE"         # "IDLE" | "WAITING_CONTACT" | "RECORDING"
        self._ctd_disp_offset = 0.0      # Raw displacement at contact moment
        self._ctd_time_offset = 0.0      # Time at contact moment
        self._toast_label = None         # Reusable floating toast QLabel

        # Admin access — locked on every boot, unlocked per session
        self._admin_unlocked = False

        # Timer for recording time
        self.recording_timer = QTimer(self)
        self.recording_timer.timeout.connect(self._update_timer_label)

        self.setup_layout()
        self.setup_connections()

        # Start background serial reader immediately
        self.serial_manager.start_reading()

    # =========================================================
    # LAYOUT
    # =========================================================

    def setup_layout(self):
        main = QWidget()
        self.setCentralWidget(main)
        layout = QHBoxLayout(main)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # =============================================
        # LEFT SIDEBAR
        # =============================================
        self.sidebar_drawer = QWidget()
        self.sidebar_drawer.setFixedWidth(220)
        self.sidebar_drawer.setStyleSheet(
            "background-color: #ecf0f1; border-right: 1px solid #bdc3c7;"
        )
        drawer_layout = QVBoxLayout(self.sidebar_drawer)
        drawer_layout.setContentsMargins(0, 10, 0, 0)

        # Company Logo
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setStyleSheet(
            "background-color: white; margin: 8px 8px 5px 8px; "
            "padding: 5px; border-radius: 4px;"
        )
        logo_path = os.path.join(os.path.dirname(__file__), "InsituMicronlogo.jpg")
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path)
            scaled_pixmap = logo_pixmap.scaledToHeight(35, Qt.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
        else:
            self.logo_label.setText("INSITU MICRON")
            self.logo_label.setStyleSheet(
                f"background-color: white; margin: 8px 8px 5px 8px; "
                f"padding: 10px; border-radius: 4px; "
                f"font-size: 20px; font-weight: bold; color: {PRIMARY_COLOR};"
            )
        drawer_layout.addWidget(self.logo_label)

        # "MENU" label
        lbl_menu = QLabel("MENU")
        lbl_menu.setStyleSheet(
            "font-weight: bold; font-size: 22px; color: #2c3e50; "
            "margin-left: 15px; margin-bottom: 10px;"
        )
        drawer_layout.addWidget(lbl_menu)

        # Navigation list
        self.sidebar = QListWidget()
        self.sidebar.addItems([
            "Sample Parameters",
            "Test Dashboard",
            "Test Analysis",
            "Settings"
        ])
        self.sidebar.setStyleSheet(f"""
            QListWidget {{ background-color: transparent; border: none; font-size: 18px; }}
            QListWidget::item {{ padding: 12px; margin: 2px 5px; color: #2c3e50; }}
            QListWidget::item:selected {{ background-color: {PRIMARY_COLOR}; color: white; border-radius: 5px; }}
            QListWidget::item:hover:!selected {{ background-color: #dfe6e9; border-radius: 5px; }}
        """)
        self.sidebar.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sidebar.verticalScrollBar().setDisabled(True)
        self.sidebar.wheelEvent = lambda event: event.ignore()
        self.sidebar.setVerticalScrollMode(QAbstractItemView.ScrollPerItem)
        self.sidebar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.sidebar.setMinimumHeight(200)
        self.sidebar.setCurrentRow(0)
        drawer_layout.addWidget(self.sidebar, stretch=1)

        # Action buttons at bottom (no addStretch — sidebar list fills remaining space)

        self.btn_start_test = QPushButton("Start Test")
        self.btn_start_test.setFixedHeight(55)
        self.btn_start_test.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_COLOR};
                border: none; font-size: 18px; font-weight: bold;
                border-radius: 6px; margin: 3px 10px; color: white;
                border-bottom: 3px solid #006680;
            }}
            QPushButton:pressed {{
                background-color: #0097b5;
                border-bottom: 0px solid #006680;
                margin: 6px 10px 3px 10px;
            }}
            QPushButton:hover {{ background-color: #33b5d5; }}
            QPushButton:disabled {{ background-color: #dfe6e9; border-bottom: 3px solid #b2bec3; color: #b2bec3; }}
        """)
        drawer_layout.addWidget(self.btn_start_test)

        self.btn_stop_test = QPushButton("Stop Test")
        self.btn_stop_test.setFixedHeight(55)
        self.btn_stop_test.setEnabled(False)
        self.btn_stop_test.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                border: none; font-size: 18px; font-weight: bold;
                border-radius: 6px; margin: 3px 10px 3px 10px; color: white;
                border-bottom: 3px solid #900000;
            }
            QPushButton:pressed {
                background-color: #c0392b;
                border-bottom: 0px solid #900000;
                margin: 6px 10px 3px 10px;
            }
            QPushButton:hover { background-color: #ec7063; }
            QPushButton:disabled { background-color: #dfe6e9; border-bottom: 3px solid #b2bec3; color: #b2bec3; }
        """)
        drawer_layout.addWidget(self.btn_stop_test)

        self.lbl_recording_status = QLabel("IDLE")
        self.lbl_recording_status.setAlignment(Qt.AlignCenter)
        self.lbl_recording_status.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: white; background-color: #95a5a6; "
            "border-radius: 4px; padding: 4px; margin-left: 40px; margin-right: 40px; margin-top: 5px;"
        )
        drawer_layout.addWidget(self.lbl_recording_status)

        lbl_test_duration = QLabel("Test Duration")
        lbl_test_duration.setAlignment(Qt.AlignCenter)
        lbl_test_duration.setStyleSheet(
            "font-size: 13px; color: #7f8c8d; background-color: transparent; margin-top: 6px;"
        )
        drawer_layout.addWidget(lbl_test_duration)

        self.lbl_timer = QLabel("00:00:00")
        self.lbl_timer.setAlignment(Qt.AlignCenter)
        self.lbl_timer.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50; margin-bottom: 10px;")
        drawer_layout.addWidget(self.lbl_timer)

        layout.addWidget(self.sidebar_drawer)

        # =============================================
        # RIGHT CONTENT AREA
        # =============================================
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #f8f9fa;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_sample_params_page())   # Tab 0
        self.pages.addWidget(self._build_test_dashboard_page())            # Tab 1
        self.pages.addWidget(self._build_history_page())         # Tab 2
        self.pages.addWidget(self._build_settings_page())        # Tab 3

        content_layout.addWidget(self.pages)
        layout.addWidget(content_widget)

    # ---------------------------------------------------------
    # PAGE BUILDERS
    # ---------------------------------------------------------

    def _build_sample_params_page(self):
        """Build the Sample Parameters input page with touch-friendly fields."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Sample Parameters")
        title.setStyleSheet(
            f"font-size: 28px; font-weight: bold; color: {PRIMARY_COLOR}; "
            "margin-bottom: 5px; background-color: transparent;"
        )
        page_layout.addWidget(title)

        # Wrap form content in a scroll area so it never inflates the window minimum size
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        form_widget = QWidget()
        layout = QVBoxLayout(form_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 10, 0)

        # --- Sample Identification ---
        id_group = QGroupBox("Identification")
        id_form = QFormLayout(id_group)
        id_form.setSpacing(12)
        id_form.setContentsMargins(15, 25, 15, 15)

        self.inp_sample_name = TouchLineEdit(
            mode="text", title="Enter Sample ID"
        )
        self.inp_sample_name.setPlaceholderText("Tap to enter sample ID...")
        id_form.addRow(self._form_label("Sample ID:"), self.inp_sample_name)

        self.inp_test_number = TouchLineEdit(
            mode="numeric", title="Enter Test Number"
        )
        self.inp_test_number.setPlaceholderText("Tap to enter test number...")
        id_form.addRow(self._form_label("Test Number:"), self.inp_test_number)

        self.inp_business_type = TouchLineEdit(
            mode="text", title="Enter Business Type"
        )
        self.inp_business_type.setPlaceholderText("Tap to enter business type...")
        id_form.addRow(self._form_label("Business Type:"), self.inp_business_type)

        layout.addWidget(id_group)

        # --- Dimensions ---
        dim_group = QGroupBox("Sample Dimensions")
        dim_form = QFormLayout(dim_group)
        dim_form.setSpacing(12)
        dim_form.setContentsMargins(15, 25, 15, 15)

        self.inp_length = TouchLineEdit(
            mode="numeric", title="Enter Span Length", unit="mm"
        )
        self.inp_length.setPlaceholderText("Tap to enter...")
        dim_form.addRow(self._form_label("Span Length (mm):"), self.inp_length)

        self.inp_width = TouchLineEdit(
            mode="numeric", title="Enter Width", unit="mm"
        )
        self.inp_width.setPlaceholderText("Tap to enter...")
        dim_form.addRow(self._form_label("Width (mm):"), self.inp_width)

        self.inp_thickness = TouchLineEdit(
            mode="numeric", title="Enter Height", unit="mm"
        )
        self.inp_thickness.setPlaceholderText("Tap to enter...")
        dim_form.addRow(self._form_label("Height (mm):"), self.inp_thickness)

        layout.addWidget(dim_group)

        # --- Environmental ---
        env_group = QGroupBox("Environmental Conditions")
        env_form = QFormLayout(env_group)
        env_form.setSpacing(12)
        env_form.setContentsMargins(15, 25, 15, 15)

        self.inp_temperature = TouchLineEdit(
            mode="numeric", title="Enter Temperature", unit="C"
        )
        self.inp_temperature.setPlaceholderText("Tap to enter...")
        env_form.addRow(self._form_label("Furnace Temperature (C):"), self.inp_temperature)

        layout.addWidget(env_group)
        layout.addStretch()

        scroll.setWidget(form_widget)
        page_layout.addWidget(scroll)
        return page

    def _form_label(self, text):
        """Create a styled form label."""
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #2c3e50; "
            "background-color: transparent;"
        )
        lbl.setMinimumWidth(160)
        return lbl

    def _build_test_dashboard_page(self):
        """Build the Test Dashboard with readouts and graph."""
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Add Title
        title = QLabel("Test Dashboard")
        title.setStyleSheet(
            f"font-size: 28px; font-weight: bold; color: {PRIMARY_COLOR}; "
            "margin-bottom: 10px; background-color: transparent;"
        )
        layout.addWidget(title)
        
        # Top Panel: Readouts
        readout_layout = QHBoxLayout()
        
        # Load Readout
        load_group = QGroupBox("Load Sensor")
        load_group.setStyleSheet("QGroupBox { font-size: 20px; font-weight: bold; }")
        load_group.setMaximumWidth(380)
        load_layout = QHBoxLayout(load_group)
        
        self.lbl_load_tared = QLabel("0.0 N")
        self.lbl_load_tared.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_load_tared.setStyleSheet("font-size: 34px; font-weight: bold; color: #e74c3c;")
        load_layout.addWidget(self.lbl_load_tared, stretch=2)
        
        load_right_layout = QVBoxLayout()
        load_right_layout.setAlignment(Qt.AlignCenter)
        load_right_layout.setSpacing(4)
        
        self.lbl_load_raw = QLabel("Raw: 0.0 N")
        self.lbl_load_raw.setAlignment(Qt.AlignCenter)
        self.lbl_load_raw.setStyleSheet("font-size: 16px; color: #7f8c8d;")
        load_right_layout.addWidget(self.lbl_load_raw)
        
        self.btn_tare_load = QPushButton("Tare Load")
        self.btn_tare_load.setFixedHeight(44)
        self.btn_tare_load.setMinimumWidth(130)
        self.btn_tare_load.setStyleSheet(_BTN_STYLE_PRIMARY)
        self.btn_tare_load.clicked.connect(self._tare_load)
        load_right_layout.addWidget(self.btn_tare_load)
        
        load_layout.addLayout(load_right_layout, stretch=1)
        readout_layout.addWidget(load_group, stretch=3)
        
        # Disp Readout
        disp_group = QGroupBox("Displacement Sensor")
        disp_group.setStyleSheet("QGroupBox { font-size: 20px; font-weight: bold; }")
        disp_group.setMaximumWidth(420)
        disp_layout = QHBoxLayout(disp_group)
        
        self.lbl_disp_tared = QLabel("0.000 mm")
        self.lbl_disp_tared.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_disp_tared.setStyleSheet("font-size: 34px; font-weight: bold; color: #2980b9;")
        disp_layout.addWidget(self.lbl_disp_tared, stretch=2)
        
        disp_right_layout = QVBoxLayout()
        disp_right_layout.setAlignment(Qt.AlignCenter)
        disp_right_layout.setSpacing(4)
        
        self.lbl_disp_raw = QLabel("Raw: 0.000 mm")
        self.lbl_disp_raw.setAlignment(Qt.AlignCenter)
        self.lbl_disp_raw.setStyleSheet("font-size: 16px; color: #7f8c8d;")
        disp_right_layout.addWidget(self.lbl_disp_raw)
        
        self.btn_tare_disp = QPushButton("Tare Disp")
        self.btn_tare_disp.setFixedHeight(44)
        self.btn_tare_disp.setMinimumWidth(130)
        self.btn_tare_disp.setStyleSheet(_BTN_STYLE_PRIMARY)
        self.btn_tare_disp.clicked.connect(self._tare_disp)
        disp_right_layout.addWidget(self.btn_tare_disp)
        
        disp_layout.addLayout(disp_right_layout, stretch=1)
        readout_layout.addWidget(disp_group, stretch=3)

        # Auto Start/Stop Panel — compact right column
        auto_group = QGroupBox("Auto Start/Stop")
        auto_group.setStyleSheet("QGroupBox { font-size: 20px; font-weight: bold; }")
        auto_layout = QVBoxLayout(auto_group)
        auto_layout.setAlignment(Qt.AlignCenter)
        auto_layout.setSpacing(4)
        auto_layout.setContentsMargins(6, 20, 6, 6)

        # Peak load tracker (useful live readout)
        peak_layout = QHBoxLayout()
        peak_layout.setAlignment(Qt.AlignCenter)
        
        lbl_peak_title = QLabel("Peak Load:")
        lbl_peak_title.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_peak_title.setStyleSheet(
            "font-size: 18px; color: #7f8c8d; font-weight: bold; background-color: transparent;"
        )
        peak_layout.addWidget(lbl_peak_title)

        self.lbl_peak_load = QLabel("0.0 N")
        self.lbl_peak_load.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_peak_load.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #8e44ad; background-color: transparent;"
        )
        peak_layout.addWidget(self.lbl_peak_load)
        
        auto_layout.addLayout(peak_layout)

        # Divider line
        divider = QLabel()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #bdc3c7; margin: 2px 0px;")
        auto_layout.addWidget(divider)

        # Status label
        self.lbl_auto_status = QLabel("DISABLED")
        self.lbl_auto_status.setAlignment(Qt.AlignCenter)
        self.lbl_auto_status.setStyleSheet(
            "font-size: 11px; color: #7f8c8d; font-weight: bold; background-color: transparent;"
        )
        auto_layout.addWidget(self.lbl_auto_status)

        # Toggle button — compact
        self.btn_auto_toggle = QPushButton("OFF")
        self.btn_auto_toggle.setFixedHeight(44)
        self.btn_auto_toggle.setStyleSheet("""
            QPushButton {
                background-color: #00334e;
                border: none; font-size: 18px; font-weight: bold;
                border-radius: 6px; color: white;
                border-bottom: 3px solid #002233;
            }
            QPushButton:pressed {
                border-bottom: 0px;
                margin-top: 3px;
            }
        """)
        self.btn_auto_toggle.clicked.connect(self._toggle_auto_start_stop)
        auto_layout.addWidget(self.btn_auto_toggle)

        # Auto Start/Stop status layout ends here

        readout_layout.addWidget(auto_group, stretch=2)
        layout.addLayout(readout_layout)

        # Graph
        self.graph_manager = GraphManager()
        self._graph_widget = self.graph_manager.get_widget()  # Keep reference for toast overlay
        layout.addWidget(self._graph_widget)
        
        self.graph_manager.plot_widget.scene().sigMouseClicked.connect(self._on_live_plot_clicked)
        self._live_touch_marker = None
        self._live_touch_label = None
        
        return page
        
    def _tare_load(self):
        # We need the last raw value, which we'll pull from the labels or store in an attribute
        if hasattr(self, '_last_raw_load'):
            self.load_offset = self._last_raw_load
            self.lbl_load_tared.setText("0.0 N")

    def _tare_disp(self):
        if hasattr(self, '_last_raw_disp'):
            self.disp_offset = self._last_raw_disp
            self.lbl_disp_tared.setText("0.000 mm")

    def _toggle_auto_start_stop(self):
        """Toggle auto start/stop on/off and update button appearance."""
        self._set_auto_start_stop(not self._auto_start_stop_enabled)

    def _set_auto_start_stop(self, enabled):
        """Helper to explicitly turn the feature on or off."""
        self._auto_start_stop_enabled = enabled
        if self._auto_start_stop_enabled:
            self.btn_auto_toggle.setText("ON")
            self.btn_auto_toggle.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ACCENT_COLOR};
                    border: none; font-size: 18px; font-weight: bold;
                    border-radius: 6px; color: white;
                    border-bottom: 3px solid #006680;
                }}
                QPushButton:pressed {{
                    border-bottom: 0px;
                    margin-top: 3px;
                }}
            """)
            
            if self._is_test_running:
                self.lbl_auto_status.setText("TEST RUNNING")
                self.lbl_auto_status.setStyleSheet("font-size: 13px; color: #27ae60; font-weight: bold; background-color: transparent;")
            else:
                self.lbl_auto_status.setText("WAITING TO START")
                self.lbl_auto_status.setStyleSheet("font-size: 13px; color: #7f8c8d; font-weight: bold; background-color: transparent;")
        else:
            self.btn_auto_toggle.setText("OFF")
            self.btn_auto_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #bdc3c7;
                    border: none; font-size: 18px; font-weight: bold;
                    border-radius: 6px; color: white;
                    border-bottom: 3px solid #7f8c8d;
                }
                QPushButton:pressed {
                    border-bottom: 0px;
                    margin-top: 3px;
                }
            """)
            self.lbl_auto_status.setText("DISABLED")
            self.lbl_auto_status.setStyleSheet(
                "font-size: 13px; color: #7f8c8d; font-weight: bold; background-color: transparent;"
            )

    def _tare_disp(self):
        if hasattr(self, '_last_raw_disp'):
            self.disp_offset = self._last_raw_disp
            self.lbl_disp_tared.setText("0.000 mm")

    def _build_history_page(self):
        """Build the Test Analysis page with a fullscreen graph and a Browse button."""
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Test Analysis")
        title.setStyleSheet(
            f"font-size: 28px; font-weight: bold; color: {PRIMARY_COLOR}; "
            "margin-bottom: 10px; background-color: transparent;"
        )
        layout.addWidget(title)

        # ----- Top action buttons row -----
        btn_row = QHBoxLayout()
        self.btn_browse_tests = QPushButton("Browse Saved Tests")
        self.btn_browse_tests.setFixedHeight(54)
        self.btn_browse_tests.setStyleSheet(_BTN_STYLE_PRIMARY + "QPushButton { font-size: 22px; }")
        btn_row.addWidget(self.btn_browse_tests)

        self.btn_clear_overlay = QPushButton("Clear Graph")
        self.btn_clear_overlay.setFixedHeight(54)
        self.btn_clear_overlay.setStyleSheet(_BTN_STYLE_PRIMARY + "QPushButton { font-size: 22px; }")
        btn_row.addWidget(self.btn_clear_overlay)
        layout.addLayout(btn_row)

        # ----- Segmented mode toggle buttons -----
        # Shared active/inactive styles matching the dashboard buttons
        _HA_ACTIVE = f"""
            QPushButton {{
                background-color: {PRIMARY_COLOR};
                border: none; font-size: 18px; font-weight: bold;
                color: white; padding: 8px 12px;
                border-bottom: 3px solid #002233;
            }}
        """
        _HA_INACTIVE = """
            QPushButton {
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                font-size: 18px; font-weight: bold;
                color: #2c3e50; padding: 8px 12px;
            }
            QPushButton:hover { background-color: #dfe6e9; }
        """

        seg_row = QHBoxLayout()
        seg_row.setSpacing(0)
        seg_row.setContentsMargins(0, 4, 0, 4)
        seg_row.setAlignment(Qt.AlignVCenter)

        lbl_graph_type = QLabel("View :")
        lbl_graph_type.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #2c3e50; background-color: transparent; margin-right: 10px;"
        )
        seg_row.addWidget(lbl_graph_type)

        _modes = [
            (0, "Load vs Disp",  "border-radius: 6px; border-top-right-radius: 0; border-bottom-right-radius: 0;"),
            (1, "Load vs Time",  "border-radius: 0;"),
            (2, "Disp vs Time",  "border-radius: 0;"),
            (3, "Stress vs Strain", "border-radius: 0;"),
            (4, "Analysis", "border-radius: 0;"),
            (5, "Results", "border-radius: 6px; border-top-left-radius: 0; border-bottom-left-radius: 0;"),
        ]

        self._history_mode_btns = []
        self._history_mode = 0   # default: Load vs Disp

        for mode_idx, label, corner_css in _modes:
            btn = QPushButton(label)
            btn.setFixedHeight(48)
            base = _HA_ACTIVE if mode_idx == 0 else _HA_INACTIVE
            btn.setStyleSheet(base + f"QPushButton {{ {corner_css} }}")
            btn.clicked.connect(lambda checked=False, m=mode_idx: self._switch_history_mode(m))
            self._history_mode_btns.append(btn)
            seg_row.addWidget(btn)

        seg_row.addStretch()
        layout.addLayout(seg_row)

        # ----- Stacked Widget for Graph vs Results -----
        from PySide6.QtWidgets import QStackedWidget, QFormLayout, QTextEdit
        self.history_stack = QStackedWidget()
        layout.addWidget(self.history_stack)

        # --- Stack Page 0: Graph ---
        graph_page = QWidget()
        graph_layout = QVBoxLayout(graph_page)
        graph_layout.setContentsMargins(0,0,0,0)
        self.history_plot = pg.PlotWidget()
        setup_plot_style(
            self.history_plot,
            "Test Comparison: Load vs Displacement",
            "Displacement (mm)", "Load (N)"
        )
        self.history_plot.addLegend(offset=(60, 10))
        self.history_plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        graph_layout.addWidget(self.history_plot)
        self.history_stack.addWidget(graph_page)

        # --- Stack Page 1: Results Pane ---
        results_page = QWidget()
        results_layout = QVBoxLayout(results_page)
        results_layout.setContentsMargins(15, 15, 15, 15)

        grp_results = QGroupBox("Mechanical Properties")
        grp_results.setStyleSheet("QGroupBox { font-size: 22px; font-weight: bold; }")
        res_form = QFormLayout(grp_results)
        res_form.setSpacing(15)

        val_style = f"font-size: 24px; font-weight: bold; color: {PRIMARY_COLOR};"
        lbl_style = "font-size: 20px; font-weight: bold; color: #2c3e50;"

        self.lbl_res_e = QLabel("--")
        self.lbl_res_e.setStyleSheet(val_style)
        self.lbl_res_break = QLabel("--")
        self.lbl_res_break.setStyleSheet(val_style)
        self.lbl_res_break_strain = QLabel("--")
        self.lbl_res_break_strain.setStyleSheet(val_style)

        def _form_row(label_text, widget):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(lbl_style)
            res_form.addRow(lbl, widget)

        _form_row("Flexural Modulus (E):", self.lbl_res_e)
        _form_row("Break Stress:", self.lbl_res_break)
        _form_row("Break Strain:", self.lbl_res_break_strain)

        results_layout.addWidget(grp_results)

        grp_notes = QGroupBox("Operator Notes")
        grp_notes.setStyleSheet("QGroupBox { font-size: 20px; font-weight: bold; }")
        notes_layout = QVBoxLayout(grp_notes)
        self.txt_analysis_notes = TouchTextEdit(title="Operator Notes")
        notes_layout.addWidget(self.txt_analysis_notes)
        results_layout.addWidget(grp_notes)

        self.btn_export_report = QPushButton("Export PDF to USB")
        self.btn_export_report.setFixedHeight(54)
        self.btn_export_report.setStyleSheet(f"background-color: {PRIMARY_COLOR}; color: white; font-weight: bold; font-size: 22px; border-radius: 6px;")
        self.btn_export_report.clicked.connect(self._on_export_pdf_clicked)
        results_layout.addWidget(self.btn_export_report)

        self.history_stack.addWidget(results_page)

        # Cache: list of dicts {test_id, name, timestamps, loads, disps}
        self._loaded_tests_cache = []
        
        # Analysis result cache
        self._current_analysis_result = None
        self._analyzed_test_meta = None
        
        self.history_plot.scene().sigMouseClicked.connect(self._on_history_plot_clicked)
        self._history_touch_marker = None
        self._history_touch_label = None

        return page

    def _handle_plot_click(self, event, plot_widget, marker_item, label_item):
        """Generic click handler to find closest point on a plot and place a marker."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont
        import numpy as np
        
        if event.button() != Qt.LeftButton:
            return marker_item, label_item
            
        pos = event.scenePos()
        if not plot_widget.sceneBoundingRect().contains(pos):
            return marker_item, label_item
            
        mouse_point = plot_widget.plotItem.vb.mapSceneToView(pos)
        click_x = mouse_point.x()
        click_y = mouse_point.y()
        
        closest_point = None
        min_dist = float('inf')
        
        for item in plot_widget.plotItem.items:
            if isinstance(item, pg.PlotDataItem):
                x_data = item.xData
                y_data = item.yData
                
                if x_data is not None and len(x_data) > 0 and y_data is not None and len(y_data) > 0:
                    x_range = plot_widget.plotItem.vb.viewRange()[0]
                    y_range = plot_widget.plotItem.vb.viewRange()[1]
                    x_span = x_range[1] - x_range[0]
                    y_span = y_range[1] - y_range[0]
                    
                    if x_span == 0 or y_span == 0: continue
                    
                    dx = (x_data - click_x) / x_span
                    dy = (y_data - click_y) / y_span
                    dist = dx**2 + dy**2
                    idx = np.argmin(dist)
                    
                    if dist[idx] < min_dist:
                        min_dist = dist[idx]
                        closest_point = (x_data[idx], y_data[idx])
                        
        if closest_point and min_dist < 0.05:
            cx, cy = closest_point
            
            if marker_item in plot_widget.items(): plot_widget.removeItem(marker_item)
            if label_item in plot_widget.items(): plot_widget.removeItem(label_item)
                
            marker_item = pg.ScatterPlotItem([cx], [cy], size=14, pen=pg.mkPen(None), brush=pg.mkBrush(PRIMARY_COLOR))
            
            label_item = pg.TextItem(
                text=f"X: {cx:.4f}\nY: {cy:.2f}",
                color="#2c3e50", fill=(255,255,255,230), border=pg.mkPen(PRIMARY_COLOR, width=2), anchor=(0.5, 1.2)
            )
            label_item.setPos(cx, cy)
            label_item.setFont(QFont("Arial", 14, QFont.Bold))
            
            plot_widget.addItem(marker_item)
            plot_widget.addItem(label_item)
        else:
            if marker_item in plot_widget.items():
                plot_widget.removeItem(marker_item)
                marker_item = None
            if label_item in plot_widget.items():
                plot_widget.removeItem(label_item)
                label_item = None
                
        return marker_item, label_item

    def _on_live_plot_clicked(self, event):
        self._live_touch_marker, self._live_touch_label = self._handle_plot_click(
            event, self.graph_manager.plot_widget, self._live_touch_marker, self._live_touch_label
        )

    def _on_history_plot_clicked(self, event):
        """Handle tap on the history plot to show exact x,y values."""
        self._history_touch_marker, self._history_touch_label = self._handle_plot_click(
            event, self.history_plot, self._history_touch_marker, self._history_touch_label
        )

    def _build_settings_page(self):
        """Build the Settings page — compact layout to fit everything on one screen."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(4)

        title = QLabel("Settings")
        title.setStyleSheet(
            f"font-size: 28px; font-weight: bold; color: {PRIMARY_COLOR}; "
            "margin-bottom: 2px; background-color: transparent;"
        )

        title_row = QHBoxLayout()
        title_row.addWidget(title)
        title_row.addStretch()

        self.btn_admin_toggle = QPushButton("LOCKED")
        self.btn_admin_toggle.setFixedSize(100, 36)
        self.btn_admin_toggle.clicked.connect(self._on_admin_toggle_clicked)
        title_row.addWidget(self.btn_admin_toggle)
        page_layout.addLayout(title_row)

        self._update_admin_badge()

        # Wrap settings content in a scroll area (safety for very small screens)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        form_widget = QWidget()
        layout = QVBoxLayout(form_widget)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.setSpacing(6)

        # Controller Status Label
        self.lbl_controller_status = QLabel("Controller: DISCONNECTED")
        self.lbl_controller_status.setStyleSheet(
            "font-size: 18px; color: #e74c3c; font-weight: bold; margin-bottom: 6px; background-color: transparent;"
        )
        layout.addWidget(self.lbl_controller_status)

        # --- Sensor Calibration Group ---
        cal_group = QGroupBox("Sensor Calibration")
        cal_group.setStyleSheet("QGroupBox { font-size: 18px; font-weight: bold; }")
        cal_form = QFormLayout(cal_group)
        cal_form.setSpacing(10)
        cal_form.setContentsMargins(15, 22, 15, 10)

        self.inp_cal_load = TouchLineEdit(mode="numeric", title="Enter Load Calibration Factor", unit="x")
        self.inp_cal_load.setText(str(self.settings.get("load_calibration_factor", 1.0)))
        self.inp_cal_load.textChanged.connect(self._on_load_cal_changed)
        self.inp_cal_load._admin_guard = self._admin_guard
        cal_form.addRow(self._form_label("Load Calibration Factor:"), self.inp_cal_load)

        self.inp_cal_disp = TouchLineEdit(mode="numeric", title="Enter Displacement Calibration Factor", unit="x")
        self.inp_cal_disp.setText(str(self.settings.get("disp_calibration_factor", 1.0)))
        self.inp_cal_disp.textChanged.connect(self._on_disp_cal_changed)
        self.inp_cal_disp._admin_guard = self._admin_guard
        cal_form.addRow(self._form_label("Displacement Calibration Factor:"), self.inp_cal_disp)

        layout.addWidget(cal_group)

        # --- Auto Start/Stop Configuration Group ---
        settings_group = QGroupBox("Auto Start/Stop Configuration")
        settings_group.setStyleSheet("QGroupBox { font-size: 18px; font-weight: bold; margin-top: 6px; }")
        settings_form = QFormLayout(settings_group)
        settings_form.setSpacing(10)
        settings_form.setContentsMargins(15, 22, 15, 10)

        self.inp_auto_start = TouchLineEdit(
            mode="numeric", title="Enter Auto-Start Threshold", unit="N"
        )
        self.inp_auto_start.setText(str(self._AUTO_START_THRESHOLD))
        self.inp_auto_start.textChanged.connect(self._on_auto_start_changed)
        self.inp_auto_start._admin_guard = self._admin_guard
        settings_form.addRow(self._form_label("Auto-Start Threshold (N):"), self.inp_auto_start)

        self.inp_auto_drop = TouchLineEdit(
            mode="numeric", title="Enter Auto-Stop Drop", unit="%"
        )
        self.inp_auto_drop.setText(str(int(self._AUTO_STOP_DROP_FRACTION * 100)))
        self.inp_auto_drop.textChanged.connect(self._on_auto_drop_changed)
        self.inp_auto_drop._admin_guard = self._admin_guard
        settings_form.addRow(self._form_label("Auto-Stop Drop (%):"), self.inp_auto_drop)

        layout.addWidget(settings_group)

        # --- Contact-Triggered Displacement (CTD) Group ---
        ctd_group = QGroupBox("Contact-Triggered Displacement (CTD)")
        ctd_group.setStyleSheet("QGroupBox { font-size: 18px; font-weight: bold; margin-top: 6px; }")
        ctd_inner = QVBoxLayout(ctd_group)
        ctd_inner.setSpacing(6)
        ctd_inner.setContentsMargins(15, 22, 15, 10)

        # Toggle + Threshold on the SAME row
        ctd_row = QHBoxLayout()
        ctd_row.setSpacing(12)

        lbl_ctd = self._form_label("CTD:")
        lbl_ctd.setMinimumWidth(50)
        ctd_row.addWidget(lbl_ctd)

        self.btn_ctd_toggle = QPushButton("ON" if self._ctd_enabled else "OFF")
        self.btn_ctd_toggle.setFixedHeight(40)
        self.btn_ctd_toggle.setFixedWidth(100)
        self.btn_ctd_toggle.clicked.connect(self._on_ctd_toggle_clicked)
        self.btn_ctd_toggle._admin_guard = self._admin_guard
        self._update_ctd_toggle_style()
        ctd_row.addWidget(self.btn_ctd_toggle)

        ctd_row.addSpacing(15)

        lbl_thresh = self._form_label("Load Threshold:")
        lbl_thresh.setMinimumWidth(130)
        ctd_row.addWidget(lbl_thresh)

        self.inp_ctd_threshold = TouchLineEdit(
            mode="numeric", title="Enter CTD Load Threshold", unit="N"
        )
        self.inp_ctd_threshold.setText(str(self._ctd_threshold))
        self.inp_ctd_threshold.textChanged.connect(self._on_ctd_threshold_changed)
        self.inp_ctd_threshold._admin_guard = self._admin_guard
        ctd_row.addWidget(self.inp_ctd_threshold, stretch=1)

        ctd_inner.addLayout(ctd_row)

        # Note — single line clear explanation
        ctd_note = QLabel(
            "Note: If Auto-Start is also enabled, the Auto-Start threshold will be used for contact detection instead of the CTD load threshold."
        )
        ctd_note.setStyleSheet(
            "font-size: 13px; color: #7f8c8d; font-style: italic; "
            "background-color: transparent; padding: 2px 0px;"
        )
        ctd_note.setWordWrap(True)
        ctd_inner.addWidget(ctd_note)

        layout.addWidget(ctd_group)

        # --- System Actions (Shutdown) ---
        system_group = QGroupBox("System Actions")
        system_group.setStyleSheet("QGroupBox { font-size: 18px; font-weight: bold; margin-top: 6px; }")
        sys_layout = QVBoxLayout(system_group)
        sys_layout.setContentsMargins(15, 22, 15, 10)

        self.btn_shutdown = QPushButton("Shut Down Machine")
        self.btn_shutdown.setFixedHeight(46)
        self.btn_shutdown.setStyleSheet("""
            QPushButton {
                background-color: #c0392b; color: white;
                font-size: 18px; font-weight: bold; border-radius: 6px;
            }
            QPushButton:hover { background-color: #e74c3c; }
        """)
        self.btn_shutdown.clicked.connect(self._confirm_shutdown)
        sys_layout.addWidget(self.btn_shutdown)

        layout.addWidget(system_group)

        layout.addStretch()

        scroll.setWidget(form_widget)
        page_layout.addWidget(scroll)
        return page

    # =========================================================
    # ADMIN SECURITY
    # =========================================================

    def _update_admin_badge(self):
        if self._admin_unlocked:
            self.btn_admin_toggle.setText("ADMIN")
            self.btn_admin_toggle.setStyleSheet("""
                QPushButton { background-color: #27ae60; color: white; font-weight: bold; border-radius: 4px; font-size: 14px; }
            """)
        else:
            self.btn_admin_toggle.setText("LOCKED")
            self.btn_admin_toggle.setStyleSheet("""
                QPushButton { background-color: #c0392b; color: white; font-weight: bold; border-radius: 4px; font-size: 14px; }
            """)

    def _on_admin_toggle_clicked(self):
        if self._admin_unlocked:
            self._admin_unlocked = False
            self._update_admin_badge()
        else:
            self._prompt_admin_login()

    def _admin_guard(self):
        if self._admin_unlocked:
            return True
        return self._prompt_admin_login()

    def _prompt_admin_login(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Admin Login")
        dlg.setFixedSize(400, 280)
        dlg.setStyleSheet("background-color: white; border-radius: 8px;")
        
        layout = QVBoxLayout(dlg)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        lbl_title = QLabel("Admin Access Required")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {PRIMARY_COLOR};")
        layout.addWidget(lbl_title)
        
        lbl_error = QLabel("")
        lbl_error.setAlignment(Qt.AlignCenter)
        lbl_error.setStyleSheet("color: #e74c3c; font-size: 14px; font-weight: bold;")
        layout.addWidget(lbl_error)
        
        form = QFormLayout()
        
        class _TapField(QLineEdit):
            def __init__(self, parent_dlg, placeholder):
                super().__init__()
                self._parent_dlg = parent_dlg
                self._placeholder = placeholder
                self._real_value = ""
                self.setReadOnly(True)
                self.setPlaceholderText(f"Tap to enter {placeholder.lower()}...")
                self.setStyleSheet("font-size: 16px; padding: 8px; border: 1px solid #bdc3c7; border-radius: 4px; background-color: #f4f6f7; color: #2c3e50;")
                
            def mousePressEvent(self, event):
                kb_dlg = TextInputDialog(
                    self._parent_dlg,
                    title=self._placeholder,
                    current_value=self._real_value
                )
                if kb_dlg.exec() == TextInputDialog.Accepted:
                    val = kb_dlg.get_value()
                    if val is not None:
                        self._real_value = val
                        self.setText(val)
                super().mousePressEvent(event)
                
            def get_real(self):
                return self._real_value

        id_field = _TapField(dlg, "Admin ID")
        pw_field = _TapField(dlg, "Password")
        
        lbl_id = QLabel("Admin ID:")
        lbl_id.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        form.addRow(lbl_id, id_field)
        
        lbl_pw = QLabel("Password:")
        lbl_pw.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        form.addRow(lbl_pw, pw_field)
        
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(45)
        btn_cancel.setStyleSheet(_BTN_STYLE_PRIMARY)
        btn_cancel.clicked.connect(dlg.reject)
        
        btn_ok = QPushButton("Login")
        btn_ok.setFixedHeight(45)
        btn_ok.setStyleSheet(_BTN_STYLE_ACCENT)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)
        
        def _try_login():
            if id_field.get_real().strip() == _ADMIN_ID and pw_field.get_real() == _ADMIN_PASS:
                self._admin_unlocked = True
                self._update_admin_badge()
                dlg.accept()
            else:
                lbl_error.setText("Incorrect ID or password. Try again.")
                pw_field._real_value = ""
                pw_field.clear()
                
        btn_ok.clicked.connect(_try_login)
        
        return dlg.exec() == QDialog.Accepted

    def _confirm_shutdown(self):
        reply = QMessageBox.question(
            self, "Confirm Shutdown",
            "Are you sure you want to safely shut down the machine?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            import os
            os.system("sudo shutdown now")

    def _on_load_cal_changed(self, text):
        try:
            val = float(text)
            self.settings.set("load_calibration_factor", val)
            QMessageBox.information(self, "Settings Saved", f"Load Calibration Factor saved successfully as {val}")
        except ValueError:
            pass

    def _on_disp_cal_changed(self, text):
        try:
            val = float(text)
            self.settings.set("disp_calibration_factor", val)
            QMessageBox.information(self, "Settings Saved", f"Displacement Calibration Factor saved successfully as {val}")
        except ValueError:
            pass

    def _on_auto_start_changed(self, text):
        try:
            val = float(text)
            if val >= 0:
                self._AUTO_START_THRESHOLD = val
                self.settings.set("auto_start_threshold", val)
                QMessageBox.information(self, "Settings Saved", f"Auto-Start Threshold saved successfully as {val} N")
        except ValueError:
            pass

    def _on_auto_drop_changed(self, text):
        try:
            val = float(text)
            if 0 <= val <= 100:
                self._AUTO_STOP_DROP_FRACTION = val / 100.0
                self.settings.set("auto_stop_drop_fraction", val / 100.0)
                QMessageBox.information(self, "Settings Saved", f"Auto-Stop Drop Percentage saved successfully as {val} %")
        except ValueError:
            pass

    def _on_ctd_toggle_clicked(self):
        """Toggle the CTD feature on/off and persist."""
        guard = getattr(self.btn_ctd_toggle, '_admin_guard', None)
        if guard is not None:
            if not guard():
                return
        self._ctd_enabled = not self._ctd_enabled
        self.btn_ctd_toggle.setText("ON" if self._ctd_enabled else "OFF")
        self._update_ctd_toggle_style()
        self.settings.set("ctd_enabled", self._ctd_enabled)
        state_text = "enabled" if self._ctd_enabled else "disabled"
        QMessageBox.information(
            self, "Settings Saved",
            f"Contact-Triggered Displacement {state_text}."
        )

    def _update_ctd_toggle_style(self):
        """Update the CTD toggle button visual to match its state."""
        if self._ctd_enabled:
            self.btn_ctd_toggle.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ACCENT_COLOR};
                    border: none; font-size: 18px; font-weight: bold;
                    border-radius: 6px; color: white;
                    border-bottom: 3px solid #006680;
                    padding: 0px 8px; text-align: center;
                }}
                QPushButton:pressed {{
                    border-bottom: 0px;
                    margin-top: 3px;
                }}
            """)
        else:
            self.btn_ctd_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #bdc3c7;
                    border: none; font-size: 18px; font-weight: bold;
                    border-radius: 6px; color: white;
                    border-bottom: 3px solid #7f8c8d;
                    padding: 0px 8px; text-align: center;
                }
                QPushButton:pressed {
                    border-bottom: 0px;
                    margin-top: 3px;
                }
            """)

    def _on_ctd_threshold_changed(self, text):
        try:
            val = float(text)
            if val >= 0:
                self._ctd_threshold = val
                self.settings.set("ctd_threshold", val)
                QMessageBox.information(
                    self, "Settings Saved",
                    f"CTD Threshold saved successfully as {val} N"
                )
        except ValueError:
            pass

    # =========================================================
    # TOAST NOTIFICATION (floating overlay on graph widget)
    # =========================================================

    def _show_toast(self, message):
        """Show a floating notification overlaying the graph widget.
        Auto-dismisses after 3500 ms. Does not shift the graph layout.
        If a toast is already showing, it is replaced immediately."""
        parent_widget = self._graph_widget

        if self._toast_label is None:
            self._toast_label = QLabel(parent_widget)
            self._toast_label.setAlignment(Qt.AlignCenter)
            self._toast_label.setStyleSheet(
                f"background-color: {PRIMARY_COLOR}; color: white; "
                "font-size: 16px; font-weight: bold; "
                "border-radius: 8px; padding: 10px 24px;"
            )

        self._toast_label.setText(message)
        self._toast_label.adjustSize()

        # Centre horizontally at top of graph widget
        pw = parent_widget.width()
        tw = self._toast_label.sizeHint().width()
        th = self._toast_label.sizeHint().height()
        x = max(0, (pw - tw) // 2)
        y = 10  # 10px from top
        self._toast_label.setGeometry(x, y, tw, th)
        self._toast_label.raise_()
        self._toast_label.show()

        # Auto-dismiss after 3500 ms
        QTimer.singleShot(3500, self._dismiss_toast)

    def _dismiss_toast(self):
        """Hide the toast label if it exists."""
        if self._toast_label is not None:
            self._toast_label.hide()

    # =========================================================
    # SIGNAL CONNECTIONS
    # =========================================================

    def setup_connections(self):
        self.sidebar.currentRowChanged.connect(self.change_page)
        self.serial_manager.new_data.connect(self.update_graph)
        self.serial_manager.connection_status_changed.connect(self._on_connection_changed)
        self.btn_start_test.clicked.connect(self.start_test)
        self.btn_stop_test.clicked.connect(self.stop_test)

                # History page
        self.btn_browse_tests.clicked.connect(self.open_file_browser)
        self.btn_clear_overlay.clicked.connect(self.clear_overlay_graph)

    # =========================================================
    # NAVIGATION
    # =========================================================

    @Slot(int)
    def change_page(self, index):
        self.pages.setCurrentIndex(index)
        
        # Prevent the QListWidget from auto-scrolling down and hiding the top tabs
        # since we disabled manual scrolling for the user.
        if self.sidebar.count() > 0:
            self.sidebar.scrollToItem(self.sidebar.item(0))

    # =========================================================
    # LIVE VIEW
    # =====================================================    @Slot(float, float, float)
    def update_graph(self, time_val, load_raw, disp_raw):
        # Apply calibration factors
        load_raw = load_raw * self.settings.get("load_calibration_factor", 1.0)
        disp_raw = disp_raw * self.settings.get("disp_calibration_factor", 1.0)

        self._last_raw_load = load_raw
        self._last_raw_disp = disp_raw

        load_tared = load_raw - self.load_offset
        disp_tared = disp_raw - self.disp_offset

        # If a test is NOT running and NOT waiting for CTD contact,
        # just show live data on the screen but don't log/graph it.
        if not self._is_test_running and self._ctd_state != "WAITING_CONTACT":
            # ---- Auto Start logic ----
            if self._auto_start_stop_enabled:
                if load_tared >= self._AUTO_START_THRESHOLD:
                    self.start_test()
                    return  # Exit this frame early so it picks up on the next frame

            # Throttle the live view to save CPU
            if not hasattr(self, '_gui_update_counter'):
                self._gui_update_counter = 0
            self._gui_update_counter += 1
            if self._gui_update_counter % 5 == 0:
                self.lbl_load_raw.setText(f"Raw: {load_raw:.0f} N")
                self.lbl_load_tared.setText(f"{load_tared:.0f} N")
                self.lbl_disp_raw.setText(f"Raw: {disp_raw:.3f} mm")
                self.lbl_disp_tared.setText(f"{disp_tared:.3f} mm")
            return

        # ---- CTD: WAITING_CONTACT state ----
        # Test has been armed but we're waiting for load to exceed the contact threshold.
        # During this phase, update load/disp readout labels but do NOT log or graph.
        if self._ctd_state == "WAITING_CONTACT":
            # Update live readouts so the operator sees sensor values
            if not hasattr(self, '_gui_update_counter'):
                self._gui_update_counter = 0
            self._gui_update_counter += 1
            if self._gui_update_counter % 5 == 0:
                self.lbl_load_raw.setText(f"Raw: {load_raw:.0f} N")
                self.lbl_load_tared.setText(f"{load_tared:.0f} N")
                self.lbl_disp_raw.setText(f"Raw: {disp_raw:.3f} mm")
                self.lbl_disp_tared.setText(f"{disp_tared:.3f} mm")

            # Determine effective CTD threshold:
            # If Auto-Start is enabled, use the auto-start threshold (takes priority).
            # Otherwise, use the dedicated CTD threshold.
            if self._auto_start_stop_enabled:
                effective_ctd_threshold = self._AUTO_START_THRESHOLD
            else:
                effective_ctd_threshold = self._ctd_threshold

            if load_tared >= effective_ctd_threshold:
                # === CONTACT DETECTED ===
                import time as _time_mod
                self._ctd_disp_offset = disp_tared   # Capture displacement at contact
                self._ctd_time_offset = _time_mod.time()  # Capture time at contact
                self._ctd_state = "RECORDING"

                # Now actually start the data logger and recording
                self.test_start_time = self._ctd_time_offset
                self.graph_manager.clear()

                sample_params = self._collect_sample_params()
                self.graph_manager.set_dimensions(
                    sample_params.get("length_mm"),
                    sample_params.get("width_mm"),
                    sample_params.get("thickness_mm")
                )

                from datetime import datetime
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                test_name = sample_params.get("sample_name", "")
                test_number = sample_params.get("test_number", "")
                if test_name and test_number:
                    name = f"{test_name}_Run{test_number}_{ts}"
                elif test_name:
                    name = f"{test_name}_{ts}"
                else:
                    name = f"Test_{ts}"

                self.data_logger.start_test(name=name, sample_params=sample_params)
                self._is_test_running = True
                self.serial_manager.is_logging = True

                # UI: switch from amber WAITING to red RECORDING
                self.lbl_recording_status.setText("RECORDING")
                self.lbl_recording_status.setStyleSheet(
                    "font-size: 14px; font-weight: bold; color: white; background-color: #e74c3c; "
                    "border-radius: 4px; padding: 4px; margin-left: 40px; margin-right: 40px; margin-top: 5px;"
                )
                self.recording_timer.start(1000)
                self.lbl_timer.setText("00:00:00")

                if self._auto_start_stop_enabled:
                    self.lbl_auto_status.setText("TEST RUNNING")
                    self.lbl_auto_status.setStyleSheet(
                        "font-size: 13px; color: #27ae60; font-weight: bold; background-color: transparent;"
                    )

                # Show toast notification
                self._show_toast(f"Displacement tared at contact: {load_tared:.1f} N")
            return  # Whether contact was detected or not, exit early during WAITING_CONTACT

        # ---- Normal test recording (CTD off, or CTD on and contact already detected) ----
        import time
        relative_time = time.time() - getattr(self, 'test_start_time', time.time())

        # If CTD is active and recording, apply the displacement offset
        if self._ctd_state == "RECORDING":
            disp_tared = disp_tared - self._ctd_disp_offset

        # Feed GraphManager - it stores full buffer
        self.graph_manager.append_data(relative_time, load_tared, disp_tared)

        if self._is_test_running:
            self.data_logger.log_data_point(relative_time, load_tared, disp_tared)

        # Throttle GUI rendering
        if not hasattr(self, '_gui_update_counter'):
            self._gui_update_counter = 0
        self._gui_update_counter += 1

        if self._gui_update_counter % 5 == 0:
            self.lbl_load_raw.setText(f"Raw: {load_raw:.0f} N")
            self.lbl_load_tared.setText(f"{load_tared:.0f} N")
            self.lbl_disp_raw.setText(f"Raw: {disp_raw:.3f} mm")
            self.lbl_disp_tared.setText(f"{disp_tared:.3f} mm")
            self.graph_manager.render()

            # ---- Auto Stop logic ----
            if self._auto_start_stop_enabled:
                # Stage 1: arm once load exceeds start threshold
                if not self._auto_armed:
                    if load_tared >= self._AUTO_START_THRESHOLD:
                        self._auto_armed = True
                        self._auto_peak_load = load_tared
                        self.lbl_peak_load.setText(f"{load_tared:.0f} N")
                        self.lbl_auto_status.setText("TEST RUNNING")
                        self.lbl_auto_status.setStyleSheet(
                            "font-size: 13px; color: #27ae60; font-weight: bold; background-color: transparent;"
                        )
                # Stage 2: track peak and detect drop
                else:
                    if load_tared > self._auto_peak_load:
                        self._auto_peak_load = load_tared
                    self.lbl_peak_load.setText(f"{self._auto_peak_load:.0f} N")
                    drop_threshold = self._auto_peak_load * (1.0 - self._AUTO_STOP_DROP_FRACTION)
                    if load_tared < drop_threshold and self._auto_peak_load > self._AUTO_START_THRESHOLD:
                        # Auto-Stop detected — update status BEFORE stopping test
                        self.lbl_auto_status.setText("AUTO STOPPED")
                        self.lbl_auto_status.setStyleSheet(
                            "font-size: 13px; color: #e74c3c; font-weight: bold; background-color: transparent;"
                        )
                        # Auto-stop disables the auto feature immediately
                        self._set_auto_start_stop(False)
                        self.stop_test()
                        QMessageBox.information(
                            self, "Auto Stop Triggered",
                            f"An automatic stop was triggered.\n"
                            f"Peak load: {self._auto_peak_load:.0f} N\n"
                            f"Drop to: {load_tared:.0f} N\n\n"
                            f"Test has been automatically stopped and saved."
                        )

    # =========================================================
    # SAMPLE PARAMETERS HELPER
    # =========================================================

    def _collect_sample_params(self):
        """Read sample parameter fields and return as a dict."""
        def _safe_float(text):
            try:
                return float(text) if text.strip() else None
            except ValueError:
                return None

        return {
            "sample_name": self.inp_sample_name.text().strip(),
            "test_number": self.inp_test_number.text().strip(),
            "business_type": self.inp_business_type.text().strip(),
            "length_mm": _safe_float(self.inp_length.text()),
            "width_mm": _safe_float(self.inp_width.text()),
            "thickness_mm": _safe_float(self.inp_thickness.text()),
            "temperature_c": _safe_float(self.inp_temperature.text()),
        }

    # =========================================================
    # TEST LIFECYCLE
    # =========================================================


    def _update_timer_label(self):
        import time
        elapsed = int(time.time() - self.test_start_time)
        hrs = elapsed // 3600
        mins = (elapsed % 3600) // 60
        secs = elapsed % 60
        self.lbl_timer.setText(f"{hrs:02d}:{mins:02d}:{secs:02d}")

    @Slot(bool, str)
    def _on_connection_changed(self, connected, message):
        """Update UI and handle test interruption if hardware disconnects."""
        from data_logger import log_kiosk_status
        if connected:
            log_kiosk_status("STM32 CONNECTED")
            self.lbl_controller_status.setText(f"Controller: CONNECTED")
            self.lbl_controller_status.setStyleSheet(
                "font-size: 18px; color: #27ae60; font-weight: bold; margin-bottom: 20px; background-color: transparent;"
            )
            if hasattr(self, 'lbl_disconnect_warning'):
                self.lbl_disconnect_warning.hide()
        else:
            log_kiosk_status(f"STM32 DISCONNECTED: {message}")
            self.lbl_controller_status.setText(f"CONTROLLER DISCONNECTED - CHECK CONNECTION")
            self.lbl_controller_status.setStyleSheet(
                "font-size: 18px; color: #e74c3c; font-weight: bold; margin-bottom: 20px; background-color: transparent;"
            )
            
            # Show a prominent warning on the dashboard
            if not hasattr(self, 'lbl_disconnect_warning'):
                self.lbl_disconnect_warning = QLabel("CONTROLLER DISCONNECTED - CHECK CONNECTION")
                self.lbl_disconnect_warning.setAlignment(Qt.AlignCenter)
                self.lbl_disconnect_warning.setStyleSheet(
                    "font-size: 20px; font-weight: bold; color: white; background-color: #c0392b; padding: 10px; border-radius: 6px; margin-bottom: 10px;"
                )
                # Insert it near the top of the dashboard page (index 1 is right under the title)
                dashboard_page = self.pages.widget(1)
                if dashboard_page:
                    dashboard_page.layout().insertWidget(1, self.lbl_disconnect_warning)
                    
            self.lbl_disconnect_warning.show()

            # If a test is running (or waiting for CTD contact) and we lose connection, stop gracefully
            if self._is_test_running or self._ctd_state == "WAITING_CONTACT":
                self.stop_test()
                self.lbl_disconnect_warning.setText("CONTROLLER DISCONNECTED - TEST AUTO-SAVED & STOPPED")

    def start_test(self):
        """Begin a new test with sample parameters.
        When CTD is enabled, this method enters the WAITING_CONTACT state instead
        of immediately starting the data logger. The actual logging begins in
        update_graph() when the contact threshold is crossed."""
        if getattr(self.serial_manager, 'serial_port', None) is None or not self.serial_manager.serial_port.is_open:
            QMessageBox.warning(self, "Controller Disconnected", "Cannot start test. Controller is not connected.")
            return

        # Reset auto start/stop state for the new test
        self._auto_peak_load = 0.0
        self._auto_armed = False
        self.lbl_peak_load.setText("0.0 N")

        if self._ctd_enabled:
            # === CTD is ON: enter WAITING_CONTACT state ===
            # Do NOT start the data logger yet — that happens when contact is detected.
            self._ctd_state = "WAITING_CONTACT"
            self._ctd_disp_offset = 0.0
            self._ctd_time_offset = 0.0

            # UI: amber status
            self.lbl_recording_status.setText("WAITING FOR CONTACT")
            self.lbl_recording_status.setStyleSheet(
                "font-size: 14px; font-weight: bold; color: white; background-color: #e67e22; "
                "border-radius: 4px; padding: 4px; margin-left: 40px; margin-right: 40px; margin-top: 5px;"
            )

            if self._auto_start_stop_enabled:
                self.lbl_auto_status.setText("WAITING FOR CONTACT")
                self.lbl_auto_status.setStyleSheet(
                    "font-size: 13px; color: #e67e22; font-weight: bold; background-color: transparent;"
                )

            self.btn_start_test.setEnabled(False)
            self.btn_stop_test.setEnabled(True)

            # Switch to Live View
            self.sidebar.setCurrentRow(1)
            return

        # === CTD is OFF: original immediate-start behaviour ===
        # Clear buffer AND reset test_start_time BEFORE any data arrives
        import time
        self.test_start_time = time.time()
        self.graph_manager.clear()

        sample_params = self._collect_sample_params()

        self.graph_manager.set_dimensions(
            sample_params.get("length_mm"),
            sample_params.get("width_mm"),
            sample_params.get("thickness_mm")
        )

        if self._auto_start_stop_enabled:
            self.lbl_auto_status.setText("TEST RUNNING")
            self.lbl_auto_status.setStyleSheet(
                "font-size: 13px; color: #27ae60; font-weight: bold; background-color: transparent;"
            )

        # Use sample name as test name if provided, else auto-generate
        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        test_name = sample_params.get("sample_name", "")
        test_number = sample_params.get("test_number", "")

        if test_name and test_number:
            name = f"{test_name}_Run{test_number}_{ts}"
        elif test_name:
            name = f"{test_name}_{ts}"
        else:
            name = f"Test_{ts}"

        test_id = self.data_logger.start_test(name=name, sample_params=sample_params)
        self._is_test_running = True

        self.serial_manager.is_logging = True

        # UI feedback
        self.lbl_recording_status.setText("RECORDING")
        self.lbl_recording_status.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: white; background-color: #e74c3c; "
            "border-radius: 4px; padding: 4px; margin-left: 40px; margin-right: 40px; margin-top: 5px;"
        )
        self.recording_timer.start(1000)
        self.lbl_timer.setText("00:00:00")

        self.btn_start_test.setEnabled(False)
        self.btn_stop_test.setEnabled(True)

        # Switch to Live View
        self.sidebar.setCurrentRow(1)

    def stop_test(self):
        # Turn off Auto Start/Stop to prevent immediate restart if load is still high
        if self._auto_start_stop_enabled:
            self._set_auto_start_stop(False)

        # Reset CTD state regardless of current phase
        was_waiting = (self._ctd_state == "WAITING_CONTACT")
        self._ctd_state = "IDLE"
        self._ctd_disp_offset = 0.0
        self._ctd_time_offset = 0.0

        self.serial_manager.is_logging = False
        self._is_test_running = False
        self.recording_timer.stop()
        self.lbl_recording_status.setText("IDLE")
        self.lbl_recording_status.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: white; background-color: #95a5a6; "
            "border-radius: 4px; padding: 4px; margin-left: 40px; margin-right: 40px; margin-top: 5px;"
        )
        test_id = self.data_logger.stop_test()

        self.btn_start_test.setEnabled(True)
        self.btn_stop_test.setEnabled(False)

        if test_id:
            # Auto-export logic
            import os
            from PySide6.QtWidgets import QProgressDialog
            
            export_dir = os.path.join(os.getcwd(), "exports")
            os.makedirs(export_dir, exist_ok=True)
            
            tests = self.data_logger.get_all_tests()
            name = f"Test_{test_id}"
            for t in tests:
                if t["test_id"] == test_id:
                    name = t["name"].replace(" ", "_").replace("/", "-")
                    break
            
            export_path = os.path.join(export_dir, f"{name}.csv")
            
            progress = QProgressDialog("Saving test data to CSV...", None, 0, 0, self)
            progress.setWindowTitle("Auto-Exporting")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            from PySide6.QtCore import QCoreApplication
            QCoreApplication.processEvents()
            
            self.data_logger.export_test_to_csv(test_id, export_path, yield_callback=QCoreApplication.processEvents)
            
            progress.cancel()

            QMessageBox.information(
                self, "Test Saved",
                f"Test data saved and automatically exported to:\n{export_path}"
            )

    # =========================================================
    # HISTORY & EXPORT
    # =========================================================
    
    def _on_export_pdf_clicked(self):
        if not self._current_analysis_result or not self._analyzed_test_meta:
            QMessageBox.warning(self, "No Data", "Please run analysis on a test before generating a report.")
            return
            
        from usb_utils import detect_usb_drive
        usb_path = detect_usb_drive()
        if not usb_path:
            QMessageBox.critical(self, "No USB Drive", "No USB drive detected. Please insert a USB drive and try again.")
            return
            
        # Determine filename
        sample_name = str(self._analyzed_test_meta.get("sample_name", "UnknownSample")).replace(" ", "_")
        test_number = str(self._analyzed_test_meta.get("test_number", "001"))
        filename = f"FlexuralReport_{sample_name}_Test{test_number}.pdf"
        
        save_path = os.path.join(usb_path, filename)
        
        # Capture graph
        temp_img_path = os.path.join(os.path.dirname(__file__), "temp_graph.png")
        try:
            # Re-render graph to mode 4 temporarily if it's not currently on it
            old_mode = self._history_mode
            if old_mode != 4:
                self._switch_history_mode(4)
                
            from PySide6.QtCore import QCoreApplication
            QCoreApplication.processEvents()
            
            self.history_plot.grab().save(temp_img_path)
            
            # Switch back
            if old_mode != 4:
                self._switch_history_mode(old_mode)
                
        except Exception as e:
            QMessageBox.critical(self, "Graph Error", f"Failed to capture graph image:\n{e}")
            return
            
        comments = self.txt_analysis_notes.toPlainText()
        
        from PySide6.QtWidgets import QProgressDialog
        from PySide6.QtCore import QThread, Signal, Qt
        
        class PDFWorker(QThread):
            finished_sig = Signal(bool, str)
            def run(self):
                try:
                    from pdf_reporter import PDFReporter
                    reporter = PDFReporter()
                    # metadata and results to pass to PDF
                    metadata = self.parent()._analyzed_test_meta
                    results = self.parent()._current_analysis_result
                    
                    # Convert result object properties to a dictionary matching the PDF reporter expectations
                    res_dict = {
                        "youngs_modulus": results.youngs_modulus,
                        "break_stress": results.break_stress,
                        "break_strain": results.break_strain
                    }
                    
                    success = reporter.generate_report(save_path, metadata, res_dict, comments, temp_img_path)
                    self.finished_sig.emit(success, "")
                except Exception as ex:
                    self.finished_sig.emit(False, str(ex))
                    
        self._pdf_worker = PDFWorker(self)
        
        progress = QProgressDialog("Exporting PDF to USB...", None, 0, 0, self)
        progress.setWindowTitle("Exporting")
        progress.setWindowModality(Qt.WindowModal)
        progress.setStyleSheet(f"QProgressDialog {{ font-size: 18px; font-weight: bold; color: {PRIMARY_COLOR}; }}")
        progress.show()
        
        def on_finished(success, error_msg):
            progress.cancel()
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)
                
            if success:
                QMessageBox.information(self, "Export Success", f"Report successfully saved to USB:\n{save_path}")
            else:
                QMessageBox.critical(self, "Export Error", f"Failed to generate PDF:\n{error_msg}")
                
        self._pdf_worker.finished_sig.connect(on_finished)
        self._pdf_worker.start()

    # =========================================================

    def open_file_browser(self):
        dialog = FileBrowserDialog(self.data_logger, self)
        if dialog.exec():
            test_ids = dialog.selected_test_ids
            if not test_ids:
                return
                
            self.plot_selected_tests(test_ids)
            
            from PySide6.QtWidgets import QProgressDialog
            from PySide6.QtCore import QCoreApplication, Qt
            from constants import PRIMARY_COLOR
            
            progress = QProgressDialog("Running Flexural Analysis...", None, 0, 0, self)
            progress.setWindowTitle("Analyzing")
            progress.setWindowModality(Qt.WindowModal)
            progress.setStyleSheet(f"QProgressDialog {{ font-size: 18px; font-weight: bold; color: {PRIMARY_COLOR}; }}")
            progress.show()
            QCoreApplication.processEvents()
            
            def on_analysis_done():
                progress.cancel()
                # Switch to Analysis graph mode automatically if only 1 test selected
                if len(test_ids) == 1:
                    self._switch_history_mode(4)
                else:
                    self._switch_history_mode(0) # Default to Load vs Disp for multiple
            
            # Auto-run analysis on the first selected test so results are ready
            self._run_flexural_analysis(callback=on_analysis_done)

    def _run_flexural_analysis(self, manual_elastic_range=None, callback=None):
        if not self._loaded_tests_cache:
            if callback: callback()
            return
            
        entry = self._loaded_tests_cache[0]
        L, w, h = entry.get("L"), entry.get("w"), entry.get("h")
        if not (L and w and h and L > 0 and w > 0 and h > 0):
            QMessageBox.warning(self, "Analysis Error", "Sample dimensions missing or invalid for this test.")
            if callback: callback()
            return

        from PySide6.QtCore import QThread, Signal
        
        class AnalysisThread(QThread):
            finished_sig = Signal(object)
            def run(self):
                from flexural_analysis import FlexuralAnalysisEngine
                engine = FlexuralAnalysisEngine()
                res = engine.analyse(
                    load=entry["loads"],
                    displacement=entry["disps"],
                    span_length_mm=L,
                    width_mm=w,
                    height_mm=h,
                    manual_elastic_range=manual_elastic_range
                )
                self.finished_sig.emit(res)
                
        self._analysis_thread = AnalysisThread(self)
        
        def on_finished(result):
            self._current_analysis_result = result
            self._analyzed_test_meta = entry
            
            def _fmt(val, suffix=""):
                return f"{val:.1f} {suffix}" if val is not None else "--"
            
            def _fmt_strain(val):
                return f"{val:.5f}" if val is not None else "--"
            
            self.lbl_res_e.setText(_fmt(result.youngs_modulus, "MPa"))
            self.lbl_res_break.setText(_fmt(result.break_stress, "MPa"))
            self.lbl_res_break_strain.setText(_fmt_strain(result.break_strain))
            
            if callback:
                callback()
                
        self._analysis_thread.finished_sig.connect(on_finished)
        self._analysis_thread.start()
            
    def plot_selected_tests(self, test_ids):
        """Load test data from DB, cache it, then render the current mode."""
        all_tests = self.data_logger.get_all_tests()
        test_map = {t["test_id"]: t for t in all_tests}

        self._loaded_tests_cache = []
        for test_id in test_ids:
            timestamps, loads, disps = self.data_logger.get_test_data(test_id)
            if not timestamps:
                continue
            
            t_info = test_map.get(test_id, {})
            self._loaded_tests_cache.append({
                "test_id": test_id,
                "name": t_info.get("name", f"Test {test_id}"),
                "timestamps": timestamps,
                "loads": loads,
                "disps": disps,
                "L": t_info.get("length_mm"),
                "w": t_info.get("width_mm"),
                "h": t_info.get("thickness_mm")
            })

        self._render_history_plot()

    def _render_history_plot(self):
        """Re-draw history_plot from cache using the current _history_mode."""
        colors = ['#005b7f', '#e74c3c', '#27ae60', '#f39c12', '#8e44ad',
                  '#00a8cc', '#d35400', '#2ecc71', '#c0392b', '#2980b9']

        self.history_plot.clear()

        # Update axis labels based on mode
        if self._history_mode == 0:
            xlabel, ylabel = "Displacement (mm)", "Load (N)"
            title = "Test Comparison: Load vs Displacement"
        elif self._history_mode == 1:
            xlabel, ylabel = "Time (s)", "Load (N)"
            title = "Test Comparison: Load vs Time"
        elif self._history_mode == 2:
            xlabel, ylabel = "Time (s)", "Displacement (mm)"
            title = "Test Comparison: Displacement vs Time"
        else:
            xlabel, ylabel = "Strain", "Stress (MPa)"
            title = "Test Comparison: Stress vs Strain"

        self.history_plot.setTitle(title, color='#2c2f33', size='18pt')
        self.history_plot.setLabel('left', ylabel, color='#2c2f33', size='16pt')
        self.history_plot.setLabel('bottom', xlabel, color='#2c2f33', size='16pt')
        self.history_plot.addLegend(offset=(60, 10))
        self.history_plot.getPlotItem().getViewBox().enableAutoRange(x=True, y=True)

        for i, entry in enumerate(self._loaded_tests_cache):
            # In Analysis mode, ONLY plot the first test
            if self._history_mode == 4 and i > 0:
                continue
                
            color = colors[i % len(colors)]
            pen = pg.mkPen(color=color, width=4)
            ts = entry["timestamps"]
            ld = entry["loads"]
            dp = entry["disps"]

            if self._history_mode == 0:
                x, y = dp, ld
            elif self._history_mode == 1:
                x, y = ts, ld
            elif self._history_mode == 2:
                x, y = ts, dp
            else:
                L, w, h = entry.get("L"), entry.get("w"), entry.get("h")
                if L and w and h and L > 0 and w > 0 and h > 0:
                    x = [(6 * d * h) / (L**2) for d in dp]
                    y = [(3 * f * L) / (2 * w * (h**2)) for f in ld]
                else:
                    continue  # skip plotting if dimensions missing

            self.history_plot.plot(x, y, pen=pen, name=entry["name"])

        # ----- Add Analysis Lines if mode 4 -----
        if self._history_mode == 4 and self._current_analysis_result:
            res = self._current_analysis_result
            # Draw Modulus Line
            if res.modulus_line:
                mx, my = res.modulus_line
                self.history_plot.plot(mx, my, pen=pg.mkPen(color='blue', width=3, style=Qt.DashLine), name="Modulus Fit")
            
            # Draw Break Point marker (peak stress = fracture point for brittle ceramics)
            if res.break_strain is not None and res.break_stress is not None:
                self.history_plot.plot([res.break_strain], [res.break_stress], 
                    pen=None, symbol='o', symbolSize=15, symbolBrush='red', name="Break Point")
                
                # Add text annotation showing break stress and strain values
                break_label = pg.TextItem(
                    text=f"Break Point\nσ = {res.break_stress:.1f} MPa\nε = {res.break_strain:.5f}",
                    color='#e74c3c',
                    anchor=(0, 1)
                )
                break_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
                break_label.setPos(res.break_strain, res.break_stress)
                self.history_plot.addItem(break_label)
            
            # Add shaded elastic region that can be clicked
            if res.elastic_start_idx < res.elastic_end_idx and len(res.strain) > res.elastic_end_idx:
                s_start = res.strain[res.elastic_start_idx]
                s_end = res.strain[res.elastic_end_idx]
                self._elastic_region = pg.LinearRegionItem(values=[s_start, s_end], movable=False)
                self._elastic_region.setBrush(pg.mkBrush(0, 0, 255, 30))
                self._elastic_region.setHoverBrush(pg.mkBrush(0, 0, 255, 60))
                self.history_plot.addItem(self._elastic_region)
                
                # We need a custom click handler for the linear region item
                def region_clicked(ev):
                    from virtual_keyboard import NumpadDialog
                    
                    # Pop up two dialogs in sequence to get start and end
                    dlg1 = NumpadDialog(self, title="Elastic Region Start Strain", current_value=f"{s_start:.5f}")
                    if dlg1.exec():
                        try:
                            new_start = float(dlg1.get_value())
                            dlg2 = NumpadDialog(self, title="Elastic Region End Strain", current_value=f"{s_end:.5f}")
                            if dlg2.exec():
                                new_end = float(dlg2.get_value())
                                if new_start < new_end:
                                    # Pop up loading bar for manual override
                                    from PySide6.QtWidgets import QProgressDialog
                                    from PySide6.QtCore import QCoreApplication, Qt
                                    from constants import PRIMARY_COLOR
                                    
                                    progress = QProgressDialog("Re-running Analysis...", None, 0, 0, self)
                                    progress.setWindowTitle("Analyzing")
                                    progress.setWindowModality(Qt.WindowModal)
                                    progress.setStyleSheet(f"QProgressDialog {{ font-size: 18px; font-weight: bold; color: {PRIMARY_COLOR}; }}")
                                    progress.show()
                                    QCoreApplication.processEvents()
                                    
                                    def on_rerun_done():
                                        progress.cancel()
                                        self._render_history_plot() # redraw
                                        
                                    self._run_flexural_analysis(
                                        manual_elastic_range=(new_start, new_end), 
                                        callback=on_rerun_done
                                    )
                                else:
                                    QMessageBox.warning(self, "Invalid Range", "Start strain must be less than End strain.")
                        except ValueError:
                            pass
                
                # Attach mouse click event
                self._elastic_region.mouseClickEvent = region_clicked


    def _switch_history_mode(self, mode):
        """Switch graph mode for the Test Analysis page and re-render from cache."""
        _HA_ACTIVE = f"""
            QPushButton {{
                background-color: {PRIMARY_COLOR};
                border: none; font-size: 18px; font-weight: bold;
                color: white; padding: 8px 12px;
                border-bottom: 3px solid #002233;
            }}
        """
        _HA_INACTIVE = """
            QPushButton {
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                font-size: 18px; font-weight: bold;
                color: #2c3e50; padding: 8px 12px;
            }
            QPushButton:hover { background-color: #dfe6e9; }
        """
        corners = [
            "border-radius: 6px; border-top-right-radius: 0; border-bottom-right-radius: 0;",
            "border-radius: 0;",
            "border-radius: 0;",
            "border-radius: 0;",
            "border-radius: 0;",
            "border-radius: 6px; border-top-left-radius: 0; border-bottom-left-radius: 0;",
        ]
        self._history_mode = mode
        for i, btn in enumerate(self._history_mode_btns):
            base = _HA_ACTIVE if i == mode else _HA_INACTIVE
            btn.setStyleSheet(base + f"QPushButton {{ {corners[i]} }}")

        if mode == 5:
            # Results page
            self.history_stack.setCurrentIndex(1)
        else:
            # Graph page
            self.history_stack.setCurrentIndex(0)
            self._render_history_plot()

    def clear_overlay_graph(self):
        self._loaded_tests_cache = []
        self.history_plot.clear()

    # =========================================================
    # CLEANUP
    # =========================================================

    def closeEvent(self, event):
        # Reset CTD state if active
        self._ctd_state = "IDLE"
        self._ctd_disp_offset = 0.0
        self._ctd_time_offset = 0.0

        if self._is_test_running:
            self.serial_manager.is_logging = False
            self._is_test_running = False
            self.data_logger.stop_test()
        self.serial_manager.stop()
        self.data_logger.close()
        event.accept()
