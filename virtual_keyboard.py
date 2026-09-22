# virtual_keyboard.py
"""
On-screen virtual keyboards for touchscreen HMI.
Provides:
  - NumpadDialog: A popup numpad for entering numeric values
  - TextInputDialog: A popup QWERTY keyboard for entering text

Design:
  - All buttons sized for finger operation (min 48x48 px).
  - Modal dialogs that block interaction with the main window.
  - Google Keyboard-style layout with ABC / symbols toggle.
  - Uses standard ASCII characters only (no Unicode font issues).
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QSizePolicy, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from constants import PRIMARY_COLOR, ACCENT_COLOR


# =========================================================
# Shared button factory
# =========================================================

def _make_key_button(text, width=None, height=48, bg="white", fg="#2c3e50",
                     font_size=16, bold=False, border=True):
    """Create a consistently styled key button with proper text rendering."""
    btn = QPushButton(text)
    btn.setMinimumHeight(height)
    if width:
        btn.setFixedWidth(width)
    btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    font_obj = QFont("Segoe UI", font_size)
    if bold:
        font_obj.setBold(True)
    btn.setFont(font_obj)

    border_css = "border: 1px solid #bdc3c7;" if border else "border: none;"
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {bg}; color: {fg};
            {border_css}
            border-radius: 5px;
            padding: 0px;
        }}
        QPushButton:pressed {{ background-color: #d5dbdb; }}
    """)
    return btn


# =========================================================
# NUMPAD DIALOG
# =========================================================

class NumpadDialog(QDialog):
    """Touchscreen-friendly numpad for entering numeric values."""

    def __init__(self, parent=None, title="Enter Value", unit="", current_value=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(380, 480)
        self.setModal(True)
        self.setStyleSheet("background-color: #f0f0f0;")
        self._value = None
        self._build_ui(title, unit, current_value)

    def _build_ui(self, title, unit, current_value):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # Title
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        lbl_title.setStyleSheet(f"color: {PRIMARY_COLOR}; background: transparent;")
        layout.addWidget(lbl_title)

        # Display field
        display_row = QHBoxLayout()
        self.display = QLineEdit(str(current_value))
        self.display.setAlignment(Qt.AlignRight)
        self.display.setReadOnly(True)
        self.display.setFont(QFont("Segoe UI", 24))
        self.display.setStyleSheet(
            "padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px; "
            "background-color: white; color: #2c3e50;"
        )
        self.display.setMinimumHeight(50)
        display_row.addWidget(self.display)

        if unit:
            lbl_unit = QLabel(unit)
            lbl_unit.setFont(QFont("Segoe UI", 16, QFont.Bold))
            lbl_unit.setStyleSheet("color: #7f8c8d; background: transparent; padding-left: 4px;")
            display_row.addWidget(lbl_unit)
        layout.addLayout(display_row)

        # Numpad grid
        grid = QGridLayout()
        grid.setSpacing(5)

        keys = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2),
            ('0', 3, 0), ('.', 3, 1), ('+/-', 3, 2),
        ]

        for text, row, col in keys:
            btn = _make_key_button(text, height=55, font_size=20, bold=True)
            btn.clicked.connect(lambda checked, t=text: self._on_key(t))
            grid.addWidget(btn, row, col)

        # Right column: Backspace, Clear
        btn_back = _make_key_button("<-", height=55, bg="#e74c3c", fg="white",
                                    font_size=18, bold=True, border=False)
        btn_back.clicked.connect(self._on_backspace)
        grid.addWidget(btn_back, 0, 3)

        btn_clear = _make_key_button("Clear", height=55, bg="#f39c12", fg="white",
                                     font_size=14, bold=True, border=False)
        btn_clear.clicked.connect(lambda: self.display.setText(""))
        grid.addWidget(btn_clear, 1, 3)

        layout.addLayout(grid)

        # OK / Cancel
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        btn_cancel = _make_key_button("Cancel", height=50, bg="#95a5a6", fg="white",
                                      font_size=16, bold=True, border=False)
        btn_cancel.clicked.connect(self.reject)
        action_row.addWidget(btn_cancel)

        btn_ok = _make_key_button("OK", height=50, bg=PRIMARY_COLOR, fg="white",
                                  font_size=16, bold=True, border=False)
        btn_ok.clicked.connect(self._on_ok)
        action_row.addWidget(btn_ok)

        layout.addLayout(action_row)

    def _on_key(self, key):
        current = self.display.text()
        if key == '+/-':
            if current.startswith('-'):
                self.display.setText(current[1:])
            elif current:
                self.display.setText('-' + current)
        elif key == '.':
            if '.' not in current:
                self.display.setText(current + '.')
        else:
            self.display.setText(current + key)

    def _on_backspace(self):
        current = self.display.text()
        if current:
            self.display.setText(current[:-1])

    def _on_ok(self):
        text = self.display.text().strip()
        if text:
            try:
                self._value = float(text)
            except ValueError:
                self._value = None
        else:
            self._value = None
        self.accept()

    def get_value(self):
        return self._value


# =========================================================
# TEXT INPUT DIALOG (Google Keyboard-style)
# =========================================================

class TextInputDialog(QDialog):
    """
    Touchscreen QWERTY keyboard with ABC / Symbols toggle.
    Layout inspired by Google Keyboard: 3 letter rows + bottom utility row.
    """

    # Key layouts
    _ALPHA_ROWS = [
        list("QWERTYUIOP"),
        list("ASDFGHJKL"),
        list("ZXCVBNM"),
    ]

    _SYMBOL_ROWS = [
        list("1234567890"),
        ['@', '#', '$', '%', '&', '-', '+', '(', ')'],
        [' ', ' ', "'", ' ', ';', '!', ' ', ' '],
    ]

    _SYMBOL_ROWS_2 = [
        ['~', '`', ' ', '{', '}', '[', ']', '^', '_'],
        [' ', ' ', '=', ' ', ',', '.', ' ', ' ', ' '],
        [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '],
    ]

    def __init__(self, parent=None, title="Enter Text", current_value=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(750, 420)
        self.setModal(True)
        self.setStyleSheet("background-color: #e8e8e8;")

        self._value = None
        self._shift = False
        self._mode = "alpha"  # "alpha", "sym1", "sym2"
        self._key_buttons = []  # list of (btn, row_idx, col_idx) for relabeling

        self._build_ui(title, current_value)

    def _build_ui(self, title, current_value):
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(8, 8, 8, 8)

        # Title
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_title.setStyleSheet(f"color: {PRIMARY_COLOR}; background: transparent;")
        layout.addWidget(lbl_title)

        # Display
        self.display = QLineEdit(current_value)
        self.display.setFont(QFont("Segoe UI", 20))
        self.display.setStyleSheet(
            "padding: 8px 12px; border: 2px solid #bdc3c7; border-radius: 6px; "
            "background-color: white; color: #2c3e50;"
        )
        self.display.setMinimumHeight(45)
        layout.addWidget(self.display)

        # Keyboard area (will be rebuilt on mode switch)
        self.keyboard_container = QWidget()
        self.keyboard_layout = QVBoxLayout(self.keyboard_container)
        self.keyboard_layout.setSpacing(4)
        self.keyboard_layout.setContentsMargins(0, 4, 0, 0)
        layout.addWidget(self.keyboard_container)

        # Build the initial keyboard
        self._rebuild_keys()

        # Bottom utility row (always visible)
        bottom = QHBoxLayout()
        bottom.setSpacing(5)

        self.btn_mode = _make_key_button("?123", width=70, height=44,
                                         bg="#95a5a6", fg="white",
                                         font_size=13, bold=True, border=False)
        self.btn_mode.clicked.connect(self._toggle_mode)
        bottom.addWidget(self.btn_mode)

        btn_space = _make_key_button("Space", height=44, font_size=14)
        btn_space.clicked.connect(lambda: self.display.insert(" "))
        bottom.addWidget(btn_space, stretch=4)

        btn_backspace = _make_key_button("<--", width=80, height=44,
                                         bg="#e74c3c", fg="white",
                                         font_size=14, bold=True, border=False)
        btn_backspace.clicked.connect(lambda: self.display.backspace())
        bottom.addWidget(btn_backspace)

        layout.addLayout(bottom)

        # OK / Cancel row
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        btn_cancel = _make_key_button("Cancel", height=46, bg="#95a5a6", fg="white",
                                      font_size=15, bold=True, border=False)
        btn_cancel.clicked.connect(self.reject)
        action_row.addWidget(btn_cancel)

        btn_ok = _make_key_button("OK", height=46, bg=PRIMARY_COLOR, fg="white",
                                  font_size=15, bold=True, border=False)
        btn_ok.clicked.connect(self._on_ok)
        action_row.addWidget(btn_ok)

        layout.addLayout(action_row)

    def _rebuild_keys(self):
        """Rebuild the 3 key rows based on the current mode."""
        # Clear existing keys
        self._key_buttons.clear()
        while self.keyboard_layout.count():
            child = self.keyboard_layout.takeAt(0)
            if child.layout():
                # Remove all widgets from the sub-layout
                while child.layout().count():
                    w = child.layout().takeAt(0).widget()
                    if w:
                        w.deleteLater()
            elif child.widget():
                child.widget().deleteLater()

        # Pick the right key set
        if self._mode == "alpha":
            rows = self._ALPHA_ROWS
        elif self._mode == "sym1":
            rows = self._SYMBOL_ROWS
        else:
            rows = self._SYMBOL_ROWS_2

        for row_idx, row_chars in enumerate(rows):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)

            # Add shift button on the left of the last alpha row
            if self._mode == "alpha" and row_idx == 2:
                btn_shift = _make_key_button("Shift", width=65, height=44,
                                             bg="#78909c", fg="white",
                                             font_size=12, bold=True, border=False)
                btn_shift.clicked.connect(self._toggle_shift)
                row_layout.addWidget(btn_shift)

            for col_idx, ch in enumerate(row_chars):
                if ch == ' ':
                    continue  # skip empty placeholders in symbol rows

                display_ch = ch
                if self._mode == "alpha":
                    display_ch = ch.upper() if self._shift else ch.lower()

                btn_text = display_ch
                if btn_text == '&':
                    btn_text = '&&'

                btn = _make_key_button(btn_text, height=44, font_size=16, bold=False)
                btn.clicked.connect(lambda checked, c=ch: self._on_char(c))
                row_layout.addWidget(btn)
                self._key_buttons.append((btn, row_idx, col_idx, ch))

            self.keyboard_layout.addLayout(row_layout)

    def _on_char(self, ch):
        if self._mode == "alpha":
            ch = ch.upper() if self._shift else ch.lower()
        self.display.insert(ch)

    def _toggle_shift(self):
        self._shift = not self._shift
        # Update button labels without full rebuild
        for btn, row_idx, col_idx, original_ch in self._key_buttons:
            if original_ch.isalpha():
                btn.setText(original_ch.upper() if self._shift else original_ch.lower())

    def _toggle_mode(self):
        if self._mode == "alpha":
            self._mode = "sym1"
            self.btn_mode.setText("ABC")
        elif self._mode == "sym1":
            self._mode = "sym2"
            self.btn_mode.setText("ABC")
        else:
            self._mode = "alpha"
            self.btn_mode.setText("?123")
        self._rebuild_keys()

    def _on_ok(self):
        self._value = self.display.text().strip()
        self.accept()

    def get_value(self):
        return self._value
