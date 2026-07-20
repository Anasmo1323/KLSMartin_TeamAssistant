import sys
import os

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

import contextlib
from PyQt6.QtWidgets import QProgressDialog, QApplication
from PyQt6.QtCore import Qt

@contextlib.contextmanager
def show_loading(parent, message="Processing, please wait..."):
    progress = QProgressDialog(message, None, 0, 0, parent)
    progress.setWindowTitle("Please Wait")
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.setCancelButton(None)
    progress.setMinimumDuration(0)
    progress.show()
    QApplication.processEvents()
    try:
        yield progress
    finally:
        progress.close()
