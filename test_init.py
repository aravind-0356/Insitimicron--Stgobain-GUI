import sys
from PySide6.QtWidgets import QApplication
from ui_layout import MainWindow
import traceback
app = QApplication(sys.argv)
try:
    window = MainWindow()
    print('Success!')
except Exception as e:
    traceback.print_exc()
