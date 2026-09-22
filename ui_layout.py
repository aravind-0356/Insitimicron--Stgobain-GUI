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
    QScrollArea, QButtonGroup, QComboBox
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QPixmap

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
_ADMIN_ID   = "admin"          # change to your preferred user ID
_ADMIN_PASS = "insitumicron"   # change to your preferred password


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
        """Open the appropriate virtual keyboard on tap.
        If an admin guard is set and admin is not unlocked, prompt login first.
        """
        # Admin guard: check if this field is protected
        guard = getattr(self, '_admin_guard', None)
        if guard is not None:
            if not guard():       # returns True if unlocked, False if still locked
                return            # user cancelled login — do not open keyboard

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
    def __init__(self, data_logger, parent=None, calibration_only=False):
        super().__init__(parent)
        self.data_logger = data_logger
        self.calibration_only = calibration_only
        self.selected_test_ids = []
        
        self.setWindowTitle("Browse Calibration Tests" if calibration_only else "Browse Saved Tests")
        self.setMinimumSize(800, 480)
        self.resize(1050, 700)
        
        layout = QVBoxLayout(self)
        
        # Test Table
        self.test_table = QTableWidget()
        if self.calibration_only:
            self.test_table.setColumnCount(2)
            self.test_table.setHorizontalHeaderLabels(["Test Name", "Heat Rate (C/min)"])
            self.test_table.setSelectionMode(QAbstractItemView.SingleSelection)
        else:
            self.test_table.setColumnCount(4)
            self.test_table.setHorizontalHeaderLabels([
                "Test Name", "Heat Rate", "Duration", "Mode"
            ])
            self.test_table.setSelectionMode(QAbstractItemView.MultiSelection)
            
        self.test_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.test_table.setSelectionBehavior(QAbstractItemView.SelectRows)
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
        
        self.btn_load = QPushButton("Select and Save" if self.calibration_only else "Load into Graph")
        self.btn_load.setFixedHeight(60)
        self.btn_load.setStyleSheet(_BTN_STYLE_PRIMARY)
        self.btn_load.clicked.connect(self.accept_load)
        btn_row.addWidget(self.btn_load)
        
        if not self.calibration_only:
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
        if self.calibration_only:
            tests = [t for t in tests if t.get("test_mode") == "CALIBRATION"]
            
        self.test_table.setRowCount(len(tests))

        for row, test in enumerate(tests):
            def create_item(text):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignCenter)
                return item

            name_item = create_item(test["name"])
            name_item.setData(Qt.UserRole, test["test_id"])
            self.test_table.setItem(row, 0, name_item)
            
            hr = test.get("target_heat_rate")
            hr_str = f"{hr:.1f}" if hr is not None else "N/A"
            self.test_table.setItem(row, 1, create_item(hr_str))
            
            if not self.calibration_only:
                dur = test["duration_s"]
                dur_str = f"{dur:.1f}s" if dur is not None else "Running..."
                self.test_table.setItem(row, 2, create_item(dur_str))
                self.test_table.setItem(row, 3, create_item(test.get("test_mode", "TEST")))
            
    def _get_selected_test_ids(self):
        selected_rows = set()
        for item in self.test_table.selectedItems():
            selected_rows.add(item.row())
        test_ids = []
        for row in sorted(selected_rows):
            id_item = self.test_table.item(row, 0)
            if id_item:
                test_ids.append(int(id_item.data(Qt.UserRole)))
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

        # Break detection state
        self._break_detection_enabled = False
        self._break_peak_load = 0.0
        self._break_armed = False
        self._BREAK_ARM_THRESHOLD = self.settings.get("break_arm_threshold", 20.0)
        self._BREAK_DROP_FRACTION = self.settings.get("break_drop_fraction", 0.40)

        # Admin access — locked on every boot, unlocked per session
        self._admin_unlocked = False

        # Crosshair markers for touch
        self._live_touch_marker = None
        self._live_touch_label = None
        self._history_touch_marker = None
        self._history_touch_label = None

        # Timer for recording time
        from PySide6.QtCore import QTimer
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

        form_widget = QWidget()
        layout = QHBoxLayout(form_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 10, 0)

        left_col = QVBoxLayout()
        right_col = QVBoxLayout()

        # --- Mode Selection (Right Col) ---
        mode_group = QGroupBox("Test Mode")
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.setContentsMargins(15, 25, 15, 15)
        
        self.btn_mode_calib = QPushButton("Calibration")
        self.btn_mode_calib.setFixedHeight(50)
        self.btn_mode_calib.setCheckable(True)
        self.btn_mode_calib.setStyleSheet("""
            QPushButton { background-color: #ecf0f1; border: 1px solid #bdc3c7; font-size: 18px; font-weight: bold; color: #2c3e50; border-radius: 6px; }
            QPushButton:checked { background-color: #006680; color: white; border: none; }
        """)
        
        self.btn_mode_test = QPushButton("Test")
        self.btn_mode_test.setFixedHeight(50)
        self.btn_mode_test.setCheckable(True)
        self.btn_mode_test.setChecked(True)
        self.btn_mode_test.setStyleSheet("""
            QPushButton { background-color: #ecf0f1; border: 1px solid #bdc3c7; font-size: 18px; font-weight: bold; color: #2c3e50; border-radius: 6px; }
            QPushButton:checked { background-color: #006680; color: white; border: none; }
        """)
        
        self.mode_btn_group = QButtonGroup(self)
        self.mode_btn_group.addButton(self.btn_mode_calib)
        self.mode_btn_group.addButton(self.btn_mode_test)
        
        self.btn_mode_calib.toggled.connect(self._toggle_test_mode)
        self.btn_mode_test.toggled.connect(self._toggle_test_mode)

        mode_layout.addWidget(self.btn_mode_calib)
        mode_layout.addWidget(self.btn_mode_test)
        right_col.addWidget(mode_group)
        
        # --- Sample Identification (Left Col) ---
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
        self.inp_business_type_lbl = self._form_label("Business Type:")
        id_form.addRow(self.inp_business_type_lbl, self.inp_business_type)

        self.inp_calib_name = TouchLineEdit(
            mode="text", title="Enter Calibration File Name"
        )
        self.inp_calib_name.setPlaceholderText("Tap to enter calib name...")
        self.inp_calib_name_lbl = self._form_label("Calibration Name:")
        id_form.addRow(self.inp_calib_name_lbl, self.inp_calib_name)
        
        self.inp_calib_name.hide()
        self.inp_calib_name_lbl.hide()

        left_col.addWidget(id_group)

        # --- Dimensions (Left Col) ---
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

        left_col.addWidget(dim_group)

        # --- Environmental & Testing (Right Col) ---
        env_group = QGroupBox("Testing Parameters")
        env_form = QFormLayout(env_group)
        env_form.setSpacing(12)
        env_form.setContentsMargins(15, 25, 15, 15)

        self.inp_constant_load = TouchLineEdit(
            mode="numeric", title="Enter Constant Load", unit="N"
        )
        self.inp_constant_load.setPlaceholderText("Tap to enter...")
        env_form.addRow(self._form_label("Constant Load (N):"), self.inp_constant_load)
        
        self.inp_heat_rate = TouchLineEdit(
            mode="numeric", title="Enter Target Heat Rate", unit="C/min"
        )
        self.inp_heat_rate.setPlaceholderText("Tap to enter...")
        env_form.addRow(self._form_label("Target Heat Rate (C/min):"), self.inp_heat_rate)
        
        # Calibration File selection
        self.btn_browse_calib = QPushButton("Browse")
        self.btn_browse_calib.setFixedHeight(40)
        self.btn_browse_calib.setStyleSheet("""
            QPushButton { background-color: #006680; color: white; border: none; font-size: 16px; font-weight: bold; border-radius: 4px; padding: 0 14px; }
            QPushButton:hover { background-color: #005b7f; }
            QPushButton:pressed { background-color: #004a66; }
        """)
        self.btn_browse_calib.clicked.connect(self._browse_calibration_file)
        
        self.lbl_selected_calib = QLabel("None")
        self.lbl_selected_calib.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; padding-left: 10px;")
        
        calib_layout = QHBoxLayout()
        calib_layout.setContentsMargins(0, 0, 0, 0)
        calib_layout.addWidget(self.btn_browse_calib)
        calib_layout.addWidget(self.lbl_selected_calib)
        calib_layout.addStretch()
        
        self.lbl_calib_title = self._form_label("Calibration File:")
        env_form.addRow(self.lbl_calib_title, calib_layout)

        right_col.addWidget(env_group)
        
        left_col.addStretch()
        right_col.addStretch()

        layout.addLayout(left_col, stretch=1)
        layout.addLayout(right_col, stretch=1)

        scroll = QScrollArea()
        scroll.setWidget(form_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QWidget#scroll_content { background: transparent; }")
        form_widget.setObjectName("scroll_content")
        
        page_layout.addWidget(scroll)
        return page

    def _toggle_test_mode(self):
        if self.btn_mode_calib.isChecked():
            self.inp_business_type.hide()
            self.inp_business_type_lbl.hide()
            self.inp_calib_name.show()
            self.inp_calib_name_lbl.show()
            
            self.btn_browse_calib.hide()
            self.lbl_selected_calib.hide()
            self.lbl_calib_title.hide()
        else:
            self.inp_business_type.show()
            self.inp_business_type_lbl.show()
            self.inp_calib_name.hide()
            self.inp_calib_name_lbl.hide()
            
            self.btn_browse_calib.show()
            self.lbl_selected_calib.show()
            self.lbl_calib_title.show()

    def _browse_calibration_file(self):
        dialog = FileBrowserDialog(self.data_logger, self, calibration_only=True)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_test_ids:
            self.lbl_selected_calib.setText(str(dialog.selected_test_ids[0]))

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
        
        # Motor Controls — vertical layout: jog buttons row + encoder label below
        motor_group = QGroupBox("Motor Controls")
        motor_group.setStyleSheet("QGroupBox { font-size: 17px; font-weight: bold; }")
        motor_group.setMinimumWidth(210)
        motor_vlayout = QVBoxLayout(motor_group)
        motor_vlayout.setContentsMargins(15, 25, 15, 15)
        motor_vlayout.setSpacing(8)

        self.btn_jog_up = QPushButton("Jog UP \u2191")
        self.btn_jog_up.setFixedHeight(50)
        self.btn_jog_up.setStyleSheet("""
            QPushButton { background-color: #005b7f; color: white; font-size: 16px; font-weight: bold; border-radius: 6px; padding: 6px 12px; }
            QPushButton:pressed { background-color: #003f5c; }
        """)
        self.btn_jog_up.pressed.connect(self._motor_jog_up)
        self.btn_jog_up.released.connect(self._motor_stop)
        motor_vlayout.addWidget(self.btn_jog_up)

        self.btn_jog_down = QPushButton("Jog DOWN \u2193")
        self.btn_jog_down.setFixedHeight(50)
        self.btn_jog_down.setStyleSheet("""
            QPushButton { background-color: #005b7f; color: white; font-size: 16px; font-weight: bold; border-radius: 6px; padding: 6px 12px; }
            QPushButton:pressed { background-color: #003f5c; }
        """)
        self.btn_jog_down.pressed.connect(self._motor_jog_down)
        self.btn_jog_down.released.connect(self._motor_stop)
        motor_vlayout.addWidget(self.btn_jog_down)

        # Faded live encoder count — sits quietly below jog buttons
        self.lbl_encoder_live = QLabel("Enc: \u2014")
        self.lbl_encoder_live.setAlignment(Qt.AlignCenter)
        self.lbl_encoder_live.setStyleSheet(
            "font-size: 13px; color: rgba(127,140,141,0.65); background-color: transparent;"
        )
        motor_vlayout.addWidget(self.lbl_encoder_live)

        readout_layout.addWidget(motor_group, stretch=3)
        
        # Disp Readout
        disp_group = QGroupBox("Displacement")
        disp_group.setStyleSheet("QGroupBox { font-size: 17px; font-weight: bold; }")
        disp_group.setMinimumWidth(160)
        disp_layout = QVBoxLayout(disp_group)
        disp_layout.setAlignment(Qt.AlignCenter)
        disp_layout.setSpacing(4)
        
        self.lbl_disp_tared = QLabel("0.000 mm")
        self.lbl_disp_tared.setAlignment(Qt.AlignCenter)
        self.lbl_disp_tared.setStyleSheet("font-size: 24px; font-weight: bold; color: #2980b9;")
        disp_layout.addWidget(self.lbl_disp_tared)
        
        self.lbl_disp_raw = QLabel("Raw: 0.000 mm")
        self.lbl_disp_raw.setAlignment(Qt.AlignCenter)
        self.lbl_disp_raw.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        disp_layout.addWidget(self.lbl_disp_raw)

        self.btn_tare_disp = QPushButton("Tare Disp")
        self.btn_tare_disp.setFixedHeight(40)
        self.btn_tare_disp.setStyleSheet(_BTN_STYLE_PRIMARY + "QPushButton { font-size: 16px; padding: 6px 12px; }")
        self.btn_tare_disp.clicked.connect(self._tare_disp)
        disp_layout.addWidget(self.btn_tare_disp)
        readout_layout.addWidget(disp_group, stretch=2)

        # Temperature Readout (replaces Motor Controls on the right)
        temp_group = QGroupBox("Temperature")
        temp_group.setStyleSheet("QGroupBox { font-size: 17px; font-weight: bold; }")
        temp_group.setMinimumWidth(140)
        temp_layout = QVBoxLayout(temp_group)
        temp_layout.setAlignment(Qt.AlignCenter)
        
        self.lbl_temp_tared = QLabel("0.0 °C")
        self.lbl_temp_tared.setAlignment(Qt.AlignCenter)
        self.lbl_temp_tared.setStyleSheet("font-size: 24px; font-weight: bold; color: #e74c3c;")
        temp_layout.addWidget(self.lbl_temp_tared)
        
        readout_layout.addWidget(temp_group, stretch=2)

        # Break Detection Panel — tracks Displacement
        break_group = QGroupBox("Break Detection")
        break_group.setStyleSheet("QGroupBox { font-size: 17px; font-weight: bold; }")
        break_group.setMinimumWidth(210)
        break_layout = QVBoxLayout(break_group)
        break_layout.setAlignment(Qt.AlignCenter)
        break_layout.setSpacing(4)
        break_layout.setContentsMargins(6, 10, 6, 6)

        # Peak Disp tracker (useful live readout)
        peak_layout = QHBoxLayout()
        peak_layout.setAlignment(Qt.AlignCenter)
        
        lbl_peak_title = QLabel("Peak Disp:")
        lbl_peak_title.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_peak_title.setStyleSheet("font-size: 14px; color: #7f8c8d; font-weight: bold; background-color: transparent;")
        peak_layout.addWidget(lbl_peak_title)

        self.lbl_peak_disp = QLabel("0.0 mm")
        self.lbl_peak_disp.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_peak_disp.setStyleSheet("font-size: 16px; font-weight: bold; color: #8e44ad; background-color: transparent;")
        peak_layout.addWidget(self.lbl_peak_disp)
        
        break_layout.addLayout(peak_layout)

        # Divider line
        divider = QLabel()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #bdc3c7; margin: 2px 0px;")
        break_layout.addWidget(divider)

        # Status label
        self.lbl_break_status = QLabel("DISARMED")
        self.lbl_break_status.setAlignment(Qt.AlignCenter)
        self.lbl_break_status.setStyleSheet("font-size: 11px; color: #7f8c8d; font-weight: bold; background-color: transparent;")
        break_layout.addWidget(self.lbl_break_status)

        # Toggle button
        self.btn_break_toggle = QPushButton("OFF")
        self.btn_break_toggle.setFixedHeight(44)
        self.btn_break_toggle.setStyleSheet("""
            QPushButton {
                background-color: #00334e; border: none; font-size: 16px; font-weight: bold;
                border-radius: 6px; color: white; border-bottom: 3px solid #002233;
                padding: 6px 12px;
            }
            QPushButton:pressed { border-bottom: 0px; margin-top: 3px; }
        """)
        self.btn_break_toggle.clicked.connect(self._toggle_break_detection)
        break_layout.addWidget(self.btn_break_toggle)

        readout_layout.addWidget(break_group, stretch=3)

        layout.addLayout(readout_layout)

        # Graph
        self.graph_manager = GraphManager()
        layout.addWidget(self.graph_manager.get_widget())
        
        self.graph_manager.plot_widget.scene().sigMouseClicked.connect(self._on_live_plot_clicked)
        return page
        

    def _tare_disp(self):
        if hasattr(self, '_last_raw_disp'):
            self.disp_offset = self._last_raw_disp
            self.lbl_disp_tared.setText("0.000 mm")

    def _motor_jog_up(self):
        # Velocity in RPM from settings
        vel = self.settings.get("motor_jog_velocity_rpm", 10.0)
        self.serial_manager.send_command(f"Vel:{vel}\n")
        
        # Give STM32 20ms to parse the Vel command before sending JogUp,
        # otherwise they collide in the RX buffer (e.g., "Vel:10.0JogUp")
        import time
        time.sleep(0.02)
        
        self.serial_manager.send_command("JogUp\n")

    def _motor_jog_down(self):
        vel = self.settings.get("motor_jog_velocity_rpm", 10.0)
        self.serial_manager.send_command(f"Vel:{vel}\n")
        import time
        time.sleep(0.02)
        self.serial_manager.send_command("JogDown\n")

    def _motor_stop(self):
        self.serial_manager.send_command("Stop\n")

    def _toggle_break_detection(self):
        """Toggle break detection on/off and update button appearance."""
        self._break_detection_enabled = not self._break_detection_enabled
        if self._break_detection_enabled:
            self.btn_break_toggle.setText("ON")
            self.btn_break_toggle.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ACCENT_COLOR};
                    border: none; font-size: 16px; font-weight: bold;
                    border-radius: 6px; color: white;
                    border-bottom: 3px solid #006680;
                    padding: 6px 12px;
                }}
                QPushButton:pressed {{
                    border-bottom: 0px;
                    margin-top: 3px;
                }}
            """)
            self.lbl_break_status.setText("WAITING")
            self.lbl_break_status.setStyleSheet(
                "font-size: 13px; color: #7f8c8d; font-weight: bold; background-color: transparent;"
            )
        else:
            self.btn_break_toggle.setText("OFF")
            self.btn_break_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #bdc3c7;
                    border: none; font-size: 16px; font-weight: bold;
                    border-radius: 6px; color: white;
                    border-bottom: 3px solid #7f8c8d;
                    padding: 6px 12px;
                }
                QPushButton:pressed {
                    border-bottom: 0px;
                    margin-top: 3px;
                }
            """)
            self.lbl_break_status.setText("DISARMED")
            self.lbl_break_status.setStyleSheet(
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

        lbl_graph_type = QLabel("Graph View :")
        lbl_graph_type.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #2c3e50; background-color: transparent; margin-right: 10px;"
        )
        seg_row.addWidget(lbl_graph_type)

        _modes = [
            (0, "Temp vs Time",  "border-radius: 6px; border-top-right-radius: 0; border-bottom-right-radius: 0;"),
            (1, "Disp vs Time",  "border-radius: 6px; border-top-left-radius: 0; border-bottom-left-radius: 0;"),
        ]

        self._history_mode_btns = []
        self._history_mode = 0   # default: Temp vs Time

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

        # ----- Graph -----
        self.history_plot = pg.PlotWidget()
        setup_plot_style(
            self.history_plot,
            "Test Comparison: Temperature vs Time",
            "Time (s)", "Temperature (°C)"
        )
        self.history_plot.addLegend(offset=(60, 10))
        self.history_plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.history_plot)
        self.history_plot.scene().sigMouseClicked.connect(self._on_history_plot_clicked)

        # Cache: list of dicts {test_id, name, timestamps, temps, disps}
        self._loaded_tests_cache = []

        return page

    def _handle_plot_click(self, event, plot_widget, marker_item, label_item, secondary_vb=None):
        """Generic click handler to find closest point on a plot (across multiple axes) and place a marker."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QFont, QColor
        import numpy as np
        
        if event.button() != Qt.LeftButton:
            return marker_item, label_item
            
        pos = event.scenePos()
        if not plot_widget.sceneBoundingRect().contains(pos):
            return marker_item, label_item
            
        closest_point = None
        min_dist = float('inf')
        matched_color = QColor(PRIMARY_COLOR)
        matched_name = ""
        
        # Collect all curves from primary and secondary viewboxes
        curves = []
        for item in plot_widget.plotItem.items:
            if isinstance(item, pg.PlotDataItem):
                curves.append((item, plot_widget.plotItem.vb))
                
        if secondary_vb is not None:
            for item in secondary_vb.addedItems:
                if isinstance(item, pg.PlotDataItem):
                    curves.append((item, secondary_vb))
                    
        # Check distance for each curve using its specific ViewBox scale
        for curve, vb in curves:
            mouse_point = vb.mapSceneToView(pos)
            click_x = mouse_point.x()
            click_y = mouse_point.y()
            
            x_data = curve.xData
            y_data = curve.yData
            
            if x_data is not None and len(x_data) > 0 and y_data is not None and len(y_data) > 0:
                x_range = vb.viewRange()[0]
                y_range = vb.viewRange()[1]
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
                    
                    # Extract curve color for the marker
                    pen = curve.opts.get('pen')
                    if pen:
                        matched_color = pg.mkPen(pen).color()
                    matched_name = curve.opts.get('name', '')
                        
        if closest_point and min_dist < 0.05:
            cx, cy = closest_point
            
            import shiboken6
            try:
                if marker_item and shiboken6.isValid(marker_item):
                    if marker_item in plot_widget.items(): plot_widget.removeItem(marker_item)
                if label_item and shiboken6.isValid(label_item):
                    if label_item in plot_widget.items(): plot_widget.removeItem(label_item)
            except RuntimeError:
                pass # Object was already destroyed
                
            marker_item = pg.ScatterPlotItem([cx], [cy], size=14, pen=pg.mkPen(None), brush=pg.mkBrush(matched_color))
            
            # Format text based on curve name if available
            unit = "°C" if "Temp" in matched_name else "mm" if "Disp" in matched_name else ""
            prefix = f"{matched_name}\n" if matched_name else ""
            
            label_item = pg.TextItem(
                text=f"{prefix}X: {cx:.2f} s\nY: {cy:.3f} {unit}",
                color="#2c3e50", fill=(255,255,255,230), border=pg.mkPen(matched_color, width=2), anchor=(0.5, 1.2)
            )
            label_item.setPos(cx, cy)
            label_item.setFont(QFont("Arial", 12, QFont.Bold))
            
            plot_widget.addItem(marker_item)
            plot_widget.addItem(label_item)
        else:
            import shiboken6
            try:
                if marker_item and shiboken6.isValid(marker_item):
                    if marker_item in plot_widget.items(): plot_widget.removeItem(marker_item)
                if label_item and shiboken6.isValid(label_item):
                    if label_item in plot_widget.items(): plot_widget.removeItem(label_item)
            except RuntimeError:
                pass
            marker_item = None
            label_item = None
                
        return marker_item, label_item

    def _on_live_plot_clicked(self, event):
        # Pass the secondary ViewBox (Temperature) so it can be scanned too
        self._live_touch_marker, self._live_touch_label = self._handle_plot_click(
            event, self.graph_manager.plot_widget, self._live_touch_marker, self._live_touch_label,
            secondary_vb=getattr(self.graph_manager, 'p2', None)
        )

    def _on_history_plot_clicked(self, event):
        """Handle tap on the history plot to show exact x,y values."""
        self._history_touch_marker, self._history_touch_label = self._handle_plot_click(
            event, self.history_plot, self._history_touch_marker, self._history_touch_label
        )

    def _build_settings_page(self):
        """Build the Settings page — wrapped in a QScrollArea."""
        page = QWidget()
        scroll_layout = QVBoxLayout(page)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        inner_widget = QWidget()
        inner_widget.setObjectName("scroll_content")
        page_layout = QVBoxLayout(inner_widget)
        page_layout.setContentsMargins(4, 4, 4, 4)
        page_layout.setSpacing(6)

        # Title row: Settings title | admin status badge | controller status
        title_row = QHBoxLayout()
        title = QLabel("Settings")
        title.setStyleSheet(
            f"font-size: 24px; font-weight: bold; color: {PRIMARY_COLOR}; background-color: transparent;"
        )
        title_row.addWidget(title)

        # Admin login/status button — left-aligned after title
        self.btn_admin_toggle = QPushButton("  LOCKED  ")
        self.btn_admin_toggle.setFixedHeight(34)
        self.btn_admin_toggle.setStyleSheet("""
            QPushButton {
                background-color: #c0392b; color: white;
                font-size: 13px; font-weight: bold;
                border-radius: 6px; padding: 0 12px;
            }
            QPushButton:hover { background-color: #e74c3c; }
        """)
        self.btn_admin_toggle.clicked.connect(self._on_admin_toggle_clicked)
        title_row.addWidget(self.btn_admin_toggle)
        title_row.addStretch()

        self.lbl_controller_status = QLabel("Controller: DISCONNECTED")
        self.lbl_controller_status.setStyleSheet(
            "font-size: 15px; color: #e74c3c; font-weight: bold; background-color: transparent;"
        )
        title_row.addWidget(self.lbl_controller_status)
        page_layout.addLayout(title_row)

        # ── Row 1: Sensor Calibration  |  Motor Configuration ──
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        cal_group = QGroupBox("Sensor Calibration")
        cal_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
        cal_form = QFormLayout(cal_group)
        cal_form.setSpacing(8)
        cal_form.setContentsMargins(12, 24, 12, 12)
        self.inp_cal_disp = TouchLineEdit(mode="numeric", title="Enter Displacement Calibration Factor", unit="x")
        self.inp_cal_disp.setText(str(self.settings.get("disp_calibration_factor", 1.0)))
        self.inp_cal_disp.textChanged.connect(self._on_disp_cal_changed)
        self.inp_cal_disp._admin_guard = self._admin_guard   # protected
        cal_form.addRow(self._form_label("Displacement Calibration Factor:"), self.inp_cal_disp)
        row1.addWidget(cal_group)

        motor_set_group = QGroupBox("Motor Configuration")
        motor_set_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
        motor_form = QFormLayout(motor_set_group)
        motor_form.setSpacing(8)
        motor_form.setContentsMargins(12, 24, 12, 12)
        self.inp_jog_vel = TouchLineEdit(mode="numeric", title="Enter Jog Velocity", unit="RPM")
        self.inp_jog_vel.setText(str(self.settings.get("motor_jog_velocity_rpm", 10.0)))
        self.inp_jog_vel.textChanged.connect(self._on_jog_vel_changed)
        self.inp_jog_vel._admin_guard = self._admin_guard          # protected
        motor_form.addRow(self._form_label("Jog Velocity (RPM):"), self.inp_jog_vel)
        self.inp_pullback_speed = TouchLineEdit(mode="numeric", title="Enter Pullback Speed", unit="RPM")
        self.inp_pullback_speed.setText(str(self.settings.get("pullback_speed_rpm", 20.0)))
        self.inp_pullback_speed.textChanged.connect(self._on_pullback_speed_changed)
        self.inp_pullback_speed._admin_guard = self._admin_guard   # protected
        motor_form.addRow(self._form_label("Pullback Speed (RPM):"), self.inp_pullback_speed)
        row1.addWidget(motor_set_group)

        page_layout.addLayout(row1)

        # ── Row 2: Break Detection Config  |  Break Action ──
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        settings_group = QGroupBox("Break Detection")
        settings_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
        settings_form = QFormLayout(settings_group)
        settings_form.setSpacing(8)
        settings_form.setContentsMargins(12, 24, 12, 12)
        self.inp_break_arm = TouchLineEdit(mode="numeric", title="Enter Arm Threshold", unit="mm")
        self.inp_break_arm.setText(str(self._BREAK_ARM_THRESHOLD))
        self.inp_break_arm.textChanged.connect(self._on_break_arm_changed)
        self.inp_break_arm._admin_guard = self._admin_guard         # protected
        settings_form.addRow(self._form_label("Arm Threshold (mm):"), self.inp_break_arm)
        self.inp_break_drop = TouchLineEdit(mode="numeric", title="Enter Drop Percentage", unit="%")
        self.inp_break_drop.setText(str(int(self._BREAK_DROP_FRACTION * 100)))
        self.inp_break_drop.textChanged.connect(self._on_break_drop_changed)
        self.inp_break_drop._admin_guard = self._admin_guard         # protected
        settings_form.addRow(self._form_label("Drop % (%):"), self.inp_break_drop)
        row2.addWidget(settings_group)

        # Break Action group (right side of row 2)
        break_action_group = QGroupBox("Break Action")
        break_action_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
        ba_layout = QVBoxLayout(break_action_group)
        ba_layout.setContentsMargins(12, 24, 12, 12)
        ba_layout.setSpacing(8)

        ba_btn_row = QHBoxLayout()
        ba_btn_row.setSpacing(6)
        self.btn_action_stop_only = QPushButton("Stop Test Only")
        self.btn_action_stop_only.setFixedHeight(44)
        self.btn_action_stop_only.setCheckable(True)
        self.btn_action_pullback  = QPushButton("Stop + Auto Pullback")
        self.btn_action_pullback.setFixedHeight(44)
        self.btn_action_pullback.setCheckable(True)
        self._ba_btn_group = QButtonGroup(self)
        self._ba_btn_group.setExclusive(True)
        self._ba_btn_group.addButton(self.btn_action_stop_only, 0)
        self._ba_btn_group.addButton(self.btn_action_pullback,  1)
        self._ba_btn_group.idClicked.connect(self._on_break_action_changed)
        _btn_active   = "QPushButton { background-color: #005b7f; color: white; font-size: 14px; font-weight: bold; border-radius: 6px; }"
        _btn_inactive = "QPushButton { background-color: #ecf0f1; color: #7f8c8d; font-size: 14px; font-weight: bold; border-radius: 6px; }"
        ba_btn_row.addWidget(self.btn_action_stop_only)
        ba_btn_row.addWidget(self.btn_action_pullback)
        ba_layout.addLayout(ba_btn_row)

        ba_form = QFormLayout()
        ba_form.setSpacing(8)
        self.inp_pullback_dist = TouchLineEdit(mode="numeric", title="Enter Pullback Distance", unit="mm")
        self.inp_pullback_dist.setText(str(self.settings.get("pullback_distance_mm", 5.0)))
        self.inp_pullback_dist.textChanged.connect(self._on_pullback_dist_changed)
        self.inp_pullback_dist._admin_guard = self._admin_guard   # protected
        ba_form.addRow(self._form_label("Pullback Distance (mm):"), self.inp_pullback_dist)
        ba_layout.addLayout(ba_form)

        # Default: Stop + Auto Pullback ON (saved_mode default is now 1)
        saved_mode = int(self.settings.get("break_action_mode", 1))
        if saved_mode == 1:
            self.btn_action_pullback.setChecked(True)
            self.btn_action_stop_only.setStyleSheet(_btn_inactive)
            self.btn_action_pullback.setStyleSheet(_btn_active)
            self.inp_pullback_dist.setEnabled(True)
        else:
            self.btn_action_stop_only.setChecked(True)
            self.btn_action_stop_only.setStyleSheet(_btn_active)
            self.btn_action_pullback.setStyleSheet(_btn_inactive)
            self.inp_pullback_dist.setEnabled(False)
        self._ba_btn_active_style   = _btn_active
        self._ba_btn_inactive_style = _btn_inactive
        row2.addWidget(break_action_group)

        page_layout.addLayout(row2)

        # ── Shutdown button — full width, prominent ──
        self.btn_shutdown = QPushButton("Shut Down Machine")
        self.btn_shutdown.setFixedHeight(54)
        self.btn_shutdown.setStyleSheet("""
            QPushButton {
                background-color: #c0392b; color: white;
                font-size: 18px; font-weight: bold; border-radius: 6px;
            }
            QPushButton:hover { background-color: #e74c3c; }
        """)
        self.btn_shutdown.clicked.connect(self._confirm_shutdown)
        page_layout.addWidget(self.btn_shutdown)

        page_layout.addStretch()
        
        scroll = QScrollArea()
        scroll.setWidget(inner_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QWidget#scroll_content { background: transparent; }")
        
        scroll_layout.addWidget(scroll)
        return page

    def _confirm_shutdown(self):
        reply = QMessageBox.question(
            self, "Confirm Shutdown",
            "Are you sure you want to safely shut down the machine?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            import os
            os.system("sudo shutdown now")

    # =========================================================
    # ADMIN ACCESS
    # =========================================================

    def _admin_guard(self):
        """Called by protected TouchLineEdit fields before opening their keyboard.
        Returns True if admin is unlocked (proceed), False if still locked (abort).
        """
        if self._admin_unlocked:
            return True
        return self._prompt_admin_login()

    def _on_admin_toggle_clicked(self):
        """Lock button in settings header — toggles admin state."""
        if self._admin_unlocked:
            # Lock the session
            self._admin_unlocked = False
            self._update_admin_badge()
        else:
            self._prompt_admin_login()

    def _prompt_admin_login(self):
        """Show the Admin Login dialog. Returns True on success, False on cancel/fail.
        Fields are touchscreen-friendly: tap to open the text keyboard dialog.
        """
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit as _QLE

        # --- Touch-friendly field helpers ----------------------------------
        # We use readonly QLineEdits whose mousePressEvent opens TextInputDialog.
        # The password field stores the real value separately and shows bullets.

        class _TapField(_QLE):
            """Readonly field that opens TextInputDialog on tap."""
            def __init__(self, placeholder, parent_dlg, is_password=False):
                super().__init__()
                self.setReadOnly(True)
                self._parent_dlg = parent_dlg
                self._placeholder = placeholder
                self._is_password = is_password
                self._real_value = ""
                self.setPlaceholderText(placeholder)
                self.setStyleSheet(
                    "font-size: 18px; padding: 10px;"
                    " border: 2px solid #bdc3c7; border-radius: 6px;"
                    " background-color: white; color: #2c3e50;"
                )

            def mousePressEvent(self, event):
                dlg = TextInputDialog(
                    self._parent_dlg,
                    title=self._placeholder,
                    current_value=self._real_value
                )
                if dlg.exec() == TextInputDialog.Accepted:
                    val = dlg.get_value()
                    if val is not None:
                        self._real_value = val
                        self.setText(val)
                super().mousePressEvent(event)

            def get_real(self):
                return self._real_value
        # -------------------------------------------------------------------

        dlg = QDialog(self)
        dlg.setWindowTitle("Admin Login")
        dlg.setModal(True)
        dlg.setMinimumWidth(460)
        dlg.setStyleSheet("""
            QDialog { background-color: #f4f6f7; }
            QLabel  { font-size: 16px; color: #2c3e50; background-color: transparent; }
        """)

        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.setSpacing(14)
        dlg_layout.setContentsMargins(24, 20, 24, 20)

        header = QLabel("Administrator Login")
        header.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {PRIMARY_COLOR};"
            " background-color: transparent;"
        )
        header.setAlignment(Qt.AlignCenter)
        dlg_layout.addWidget(header)

        dlg_layout.addWidget(QLabel("User ID  (tap to enter):"))
        id_field = _TapField("Tap to enter User ID", dlg, is_password=False)
        dlg_layout.addWidget(id_field)

        dlg_layout.addWidget(QLabel("Password  (tap to enter):"))
        pw_field = _TapField("Tap to enter Password", dlg, is_password=True)
        dlg_layout.addWidget(pw_field)

        lbl_error = QLabel("")
        lbl_error.setStyleSheet(
            "font-size: 14px; color: #e74c3c; background-color: transparent;"
        )
        lbl_error.setAlignment(Qt.AlignCenter)
        dlg_layout.addWidget(lbl_error)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.setStyleSheet("""
            QPushButton {
                font-size: 16px; font-weight: bold;
                min-width: 110px; min-height: 44px;
                border-radius: 6px;
            }
        """)
        dlg_layout.addWidget(btn_box)

        def _try_login():
            if (id_field.get_real().strip() == _ADMIN_ID and
                    pw_field.get_real() == _ADMIN_PASS):
                self._admin_unlocked = True
                self._update_admin_badge()
                dlg.accept()
            else:
                lbl_error.setText("Incorrect ID or password. Try again.")
                pw_field._real_value = ""
                pw_field.clear()

        btn_box.accepted.connect(_try_login)
        btn_box.rejected.connect(dlg.reject)

        result = dlg.exec()
        return result == QDialog.Accepted

    def _update_admin_badge(self):
        """Refresh the admin status button in the Settings header."""
        if not hasattr(self, 'btn_admin_toggle'):
            return
        if self._admin_unlocked:
            self.btn_admin_toggle.setText("  ADMIN  ")
            self.btn_admin_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60; color: white;
                    font-size: 13px; font-weight: bold;
                    border-radius: 6px; padding: 0 12px;
                }
                QPushButton:hover { background-color: #2ecc71; }
            """)
        else:
            self.btn_admin_toggle.setText("  LOCKED  ")
            self.btn_admin_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #c0392b; color: white;
                    font-size: 13px; font-weight: bold;
                    border-radius: 6px; padding: 0 12px;
                }
                QPushButton:hover { background-color: #e74c3c; }
            """)

    def _on_disp_cal_changed(self, text):
        try:
            val = float(text)
            self.settings.set("disp_calibration_factor", val)
            QMessageBox.information(self, "Settings Saved", f"Displacement Calibration Factor saved successfully as {val}")
        except ValueError:
            pass

    def _on_jog_vel_changed(self, text):
        try:
            val = float(text)
            self.settings.set("motor_jog_velocity_rpm", val)
            QMessageBox.information(self, "Settings Saved", f"Motor Jog Velocity saved successfully as {val} RPM")
        except ValueError:
            pass

    def _on_pullback_speed_changed(self, text):
        try:
            val = float(text)
            if val > 0:
                self.settings.set("pullback_speed_rpm", val)
                QMessageBox.information(self, "Settings Saved", f"Pullback Speed saved as {val} RPM")
        except ValueError:
            pass

    def _on_break_action_changed(self, btn_id):
        """Toggle between Stop Only (0) and Stop + Pullback (1).
        Requires admin access. Reverts and prompts login if locked.
        """
        if not self._admin_unlocked:
            # Revert the button group to the currently saved state
            saved = int(self.settings.get("break_action_mode", 1))
            self._ba_btn_group.blockSignals(True)
            if saved == 1:
                self.btn_action_pullback.setChecked(True)
                self.btn_action_pullback.setStyleSheet(self._ba_btn_active_style)
                self.btn_action_stop_only.setStyleSheet(self._ba_btn_inactive_style)
            else:
                self.btn_action_stop_only.setChecked(True)
                self.btn_action_stop_only.setStyleSheet(self._ba_btn_active_style)
                self.btn_action_pullback.setStyleSheet(self._ba_btn_inactive_style)
            self._ba_btn_group.blockSignals(False)
            # Prompt login — if successful, apply the intended change
            if self._prompt_admin_login():
                self._apply_break_action(btn_id)
            return
        self._apply_break_action(btn_id)

    def _apply_break_action(self, btn_id):
        """Apply and persist the break action mode choice."""
        self.settings.set("break_action_mode", btn_id)
        is_pullback = (btn_id == 1)
        self.inp_pullback_dist.setEnabled(is_pullback)
        if is_pullback:
            self.btn_action_pullback.setStyleSheet(self._ba_btn_active_style)
            self.btn_action_stop_only.setStyleSheet(self._ba_btn_inactive_style)
        else:
            self.btn_action_stop_only.setStyleSheet(self._ba_btn_active_style)
            self.btn_action_pullback.setStyleSheet(self._ba_btn_inactive_style)

    def _on_pullback_dist_changed(self, text):
        try:
            val = float(text)
            if val > 0:
                self.settings.set("pullback_distance_mm", val)
        except ValueError:
            pass

    def _on_break_arm_changed(self, text):
        try:
            val = float(text)
            if val >= 0:
                self._BREAK_ARM_THRESHOLD = val
                self.settings.set("break_arm_threshold", val)
                QMessageBox.information(self, "Settings Saved", f"Arm Threshold saved successfully as {val} N")
        except ValueError:
            pass

    def _on_break_drop_changed(self, text):
        try:
            val = float(text)
            if 0 <= val <= 100:
                self._BREAK_DROP_FRACTION = val / 100.0
                self.settings.set("break_drop_fraction", val / 100.0)
                QMessageBox.information(self, "Settings Saved", f"Drop Percentage saved successfully as {val} %")
        except ValueError:
            pass

    # =========================================================
    # SIGNAL CONNECTIONS
    # =========================================================

    def setup_connections(self):
        self.sidebar.currentRowChanged.connect(self.change_page)
        self.serial_manager.new_data.connect(self.update_graph)
        self.serial_manager.connection_status_changed.connect(self._on_connection_changed)
        self.serial_manager.pullback_done.connect(self._on_pullback_done)
        self.btn_start_test.clicked.connect(self.start_test)
        self.btn_stop_test.clicked.connect(self.stop_test)

        # History page
        self.btn_browse_tests.clicked.connect(self.open_file_browser)
        self.btn_clear_overlay.clicked.connect(self.clear_overlay_graph)

    @Slot()
    def _on_pullback_done(self):
        """Called when STM32 sends PULLBACK_DONE — update status and notify user."""
        self.lbl_break_status.setText("PULLBACK DONE")
        self.lbl_break_status.setStyleSheet(
            "font-size: 13px; color: #27ae60; font-weight: bold; background-color: transparent;"
        )
        QMessageBox.information(
            self, "Auto-Pullback Complete",
            "Break detected — auto-pullback complete.\n"
            "The rod has been retracted to a safe position.\n\n"
            "Test data has been saved."
        )

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
    # =========================================================

    @Slot(float, float, float, int)
    def update_graph(self, time_val, disp_raw, temp_raw, enc_counts):
        # Apply calibration factors
        disp_raw = disp_raw * self.settings.get("disp_calibration_factor", 1.0)

        self._last_raw_disp = disp_raw
        self._last_raw_temp = temp_raw
        self._last_enc      = enc_counts

        disp_tared = disp_raw - self.disp_offset
        comp_disp  = disp_tared

        # Always update encoder label (faded, every packet)
        self.lbl_encoder_live.setText(f"Enc: {enc_counts:,}")

        # If a test is NOT running, just show live data on the screen but don't log/graph it.
        if not self._is_test_running:
            if not hasattr(self, '_gui_update_counter'):
                self._gui_update_counter = 0
            self._gui_update_counter += 1
            if self._gui_update_counter % 5 == 0:
                self.lbl_temp_tared.setText(f"{temp_raw:.1f} °C")
                self.lbl_disp_raw.setText(f"Raw: {disp_raw:.3f} mm")
                self.lbl_disp_tared.setText(f"{disp_tared:.3f} mm")
                
                # Update break peak
                if disp_tared > getattr(self, '_break_peak_disp', 0.0):
                    self._break_peak_disp = disp_tared
                    self.lbl_peak_disp.setText(f"{self._break_peak_disp:.3f} mm")
            return

        import time
        relative_time = time.time() - getattr(self, 'test_start_time', time.time())

        # Enforce 1 Hz sampling rate (1 sample/sec) for data plotting & data logging
        last_log = getattr(self, '_last_sample_time', -1.0)
        if (relative_time - last_log) >= 1.0:
            self._last_sample_time = relative_time

            # Feed GraphManager at 1 Hz
            self.graph_manager.append_data(relative_time, temp_raw, comp_disp)

            # Record to disk at 1 Hz
            if self._is_test_running:
                self.data_logger.log_data_point(relative_time, temp_raw, disp_tared, comp_disp)

            # Re-render plot at 1 Hz
            self.graph_manager.render()

        # Throttle live numerical text readouts
        if not hasattr(self, '_gui_update_counter'):
            self._gui_update_counter = 0
        self._gui_update_counter += 1
        
        if self._gui_update_counter % 5 == 0:
            self.lbl_temp_tared.setText(f"{temp_raw:.1f} °C")
            self.lbl_disp_raw.setText(f"Raw: {disp_raw:.3f} mm")
            self.lbl_disp_tared.setText(f"{disp_tared:.3f} mm")

            # ---- Break detection logic (Displacement drop) ----
            if self._break_detection_enabled:
                threshold = self.settings.get("break_disp_delta_threshold", 0.5)

                if not hasattr(self, '_break_peak_disp'):
                    self._break_peak_disp = comp_disp

                if comp_disp > self._break_peak_disp:
                    self._break_peak_disp = comp_disp
                    self.lbl_peak_disp.setText(f"{self._break_peak_disp:.3f} mm")

                # Trigger: displacement drops below threshold from peak
                if self._break_peak_disp - comp_disp >= threshold:
                    self.lbl_break_status.setText("BREAK DETECTED")
                    self.lbl_break_status.setStyleSheet(
                        "font-size: 13px; color: #e74c3c; font-weight: bold; background-color: transparent;"
                    )
                    # Stop recording data immediately
                    self.stop_test()

                    pullback_mode = int(self.settings.get("break_action_mode", 0))
                    if pullback_mode == 1:
                        # Send pullback speed first so firmware uses the right RPM
                        pb_speed  = self.settings.get("pullback_speed_rpm", 20.0)
                        pb_dist   = self.settings.get("pullback_distance_mm", 5.0)
                        # Stepper scaling: 4000 counts per revolution.
                        # Assuming a standard 5mm pitch leadscrew as placeholder (adjust MM_PER_REV as needed)
                        ENCODER_CPR = 4000.0
                        MM_PER_REV = 5.0
                        counts_per_mm = ENCODER_CPR / MM_PER_REV
                        pb_counts = int(pb_dist * counts_per_mm)
                        self.serial_manager.send_command(f"PullSpeed:{int(pb_speed)}")
                        self.serial_manager.send_command(f"Pullback:{pb_counts}")
                        self.lbl_break_status.setText("PULLING BACK...")
                        self.lbl_break_status.setStyleSheet(
                            "font-size: 13px; color: #e67e22; font-weight: bold; background-color: transparent;"
                        )
                        # Popup will appear when _on_pullback_done() fires via PULLBACK_DONE signal
                    else:
                        # Stop-only mode — show popup immediately
                        QMessageBox.information(
                            self, "Break Detected",
                            f"A material break was detected.\n"
                            f"Peak Disp: {self._break_peak_disp:.3f} mm\n"
                            f"Drop to: {comp_disp:.3f} mm\n\n"
                            "Test has been automatically stopped and saved."
                        )
                else:
                    self.lbl_break_status.setText("ARMED")
                    self.lbl_break_status.setStyleSheet(
                        "font-size: 13px; color: #e67e22; font-weight: bold; background-color: transparent;"
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

        is_calib = self.btn_mode_calib.isChecked()

        return {
            "test_mode": "CALIBRATION" if is_calib else "TEST",
            "sample_name": self.inp_sample_name.text().strip(),
            "test_number": self.inp_test_number.text().strip(),
            "business_type": "" if is_calib else self.inp_business_type.text().strip(),
            "calibration_name": self.inp_calib_name.text().strip() if is_calib else "",
            "length_mm": _safe_float(self.inp_length.text()),
            "width_mm": _safe_float(self.inp_width.text()),
            "thickness_mm": _safe_float(self.inp_thickness.text()),
            "constant_load_n": _safe_float(self.inp_constant_load.text()),
            "target_heat_rate": _safe_float(self.inp_heat_rate.text()),
            "calibration_file": "" if is_calib else (self.lbl_selected_calib.text() if self.lbl_selected_calib.text() != "None" else "")
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

            # If a test is running and we lose connection, stop gracefully without a blocking modal
            if self._is_test_running:
                self.stop_test()
                self.lbl_disconnect_warning.setText("CONTROLLER DISCONNECTED - TEST AUTO-SAVED & STOPPED")

    def start_test(self):
        """Begin a new test with sample parameters."""
        if getattr(self.serial_manager, 'serial_port', None) is None or not self.serial_manager.serial_port.is_open:
            QMessageBox.warning(self, "Controller Disconnected", "Cannot start test. Controller is not connected.")
            return

        sample_params = self._collect_sample_params()
        
        # Pre-flight Validation
        missing_fields = []
        if not sample_params["sample_name"]: missing_fields.append("Sample ID")
        if not sample_params["test_number"]: missing_fields.append("Test Number")
        
        if sample_params["test_mode"] == "TEST" and not sample_params["business_type"]:
            missing_fields.append("Business Type")
        if sample_params["test_mode"] == "CALIBRATION" and not sample_params["calibration_name"]:
            missing_fields.append("Calibration Name")

        if sample_params["length_mm"] is None: missing_fields.append("Span Length")
        if sample_params["width_mm"] is None: missing_fields.append("Width")
        if sample_params["thickness_mm"] is None: missing_fields.append("Height")
        if sample_params["constant_load_n"] is None: missing_fields.append("Constant Load")
        if sample_params["target_heat_rate"] is None: missing_fields.append("Target Heat Rate")

        if missing_fields:
            QMessageBox.warning(
                self, "Missing Parameters",
                "Please fill in the following required fields before starting:\n\n- " + "\n- ".join(missing_fields)
            )
            return

        import time
        self.test_start_time = time.time()
        self._last_sample_time = -1.0
        self.graph_manager.clear()
        
        self.graph_manager.set_dimensions(
            sample_params.get("length_mm"),
            sample_params.get("width_mm"),
            sample_params.get("thickness_mm")
        )

        # Reset break detection arm state for the new test
        self._break_peak_disp = 0.0
        self._break_armed = False
        self.lbl_peak_disp.setText("0.000 mm")
        if self._break_detection_enabled:
            self.lbl_break_status.setText("WAITING")
            self.lbl_break_status.setStyleSheet(
                "font-size: 13px; color: #7f8c8d; font-weight: bold; background-color: transparent;"
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

    def open_file_browser(self):
        dialog = FileBrowserDialog(self.data_logger, self)
        if dialog.exec():
            test_ids = dialog.selected_test_ids
            self.plot_selected_tests(test_ids)
            
    def plot_selected_tests(self, test_ids):
        """Load test data from DB, cache it, then render the current mode."""
        all_tests = self.data_logger.get_all_tests()
        test_map = {t["test_id"]: t for t in all_tests}

        self._loaded_tests_cache = []
        for test_id in test_ids:
            res = self.data_logger.get_test_data(test_id)
            if not res or not res[0]:
                continue
            
            timestamps, temps, raw_disps, comp_disps = res
            
            t_info = test_map.get(test_id, {})
            self._loaded_tests_cache.append({
                "test_id": test_id,
                "name": t_info.get("name", f"Test {test_id}"),
                "timestamps": timestamps,
                "temps": temps,
                "disps": comp_disps,
            })

        self._render_history_plot()

    def _render_history_plot(self):
        """Re-draw history_plot from cache using the current _history_mode."""
        colors = ['#005b7f', '#e74c3c', '#27ae60', '#f39c12', '#8e44ad',
                  '#00a8cc', '#d35400', '#2ecc71', '#c0392b', '#2980b9']

        self.history_plot.clear()

        # Update axis labels based on mode
        if self._history_mode == 0:
            xlabel, ylabel = "Time (s)", "Temperature (°C)"
            title = "Test Comparison: Temperature vs Time"
        else:
            xlabel, ylabel = "Time (s)", "Displacement (mm)"
            title = "Test Comparison: Displacement vs Time"

        self.history_plot.setTitle(title, color='#2c2f33', size='18pt')
        self.history_plot.setLabel('left', ylabel, color='#2c2f33', size='16pt')
        self.history_plot.setLabel('bottom', xlabel, color='#2c2f33', size='16pt')
        self.history_plot.addLegend(offset=(60, 10))
        self.history_plot.getPlotItem().getViewBox().enableAutoRange(x=True, y=True)

        for i, entry in enumerate(self._loaded_tests_cache):
            color = colors[i % len(colors)]
            pen = pg.mkPen(color=color, width=4)
            ts = entry["timestamps"]
            tp = entry["temps"]
            dp = entry["disps"]

            if self._history_mode == 0:
                x, y = ts, tp
            else:
                x, y = ts, dp

            # Downsample if very large
            if len(x) > 5000:
                step = len(x) // 5000
                x = x[::step]
                y = y[::step]

            self.history_plot.plot(x, y, pen=pen, name=entry["name"])

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
            "border-radius: 6px; border-top-left-radius: 0; border-bottom-left-radius: 0;",
        ]
        self._history_mode = mode
        for i, btn in enumerate(self._history_mode_btns):
            base = _HA_ACTIVE if i == mode else _HA_INACTIVE
            btn.setStyleSheet(base + f"QPushButton {{ {corners[i]} }}")

        self._render_history_plot()

    def clear_overlay_graph(self):
        self._loaded_tests_cache = []
        self.history_plot.clear()

    # =========================================================
    # CLEANUP
    # =========================================================

    def closeEvent(self, event):
        if self._is_test_running:
            self.serial_manager.is_logging = False
            self._is_test_running = False
            self.data_logger.stop_test()
        self.serial_manager.stop()
        self.data_logger.close()
        event.accept()
