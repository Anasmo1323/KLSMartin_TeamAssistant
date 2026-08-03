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
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QImageReader, QPixmap

def safe_load_pixmap(image_path, max_dim=2000):
    """Safely loads an image, downscaling it if it exceeds max_dim to prevent memory errors."""
    if not os.path.exists(image_path):
        return QPixmap()
    
    reader = QImageReader(image_path)
    if not reader.canRead():
        return QPixmap(image_path)  # Fallback to standard loading
        
    size = reader.size()
    if size.width() > max_dim or size.height() > max_dim:
        scaled_size = size.scaled(max_dim, max_dim, Qt.AspectRatioMode.KeepAspectRatio)
        reader.setScaledSize(scaled_size)
        
    img = reader.read()
    if not img.isNull():
        return QPixmap.fromImage(img)
    return QPixmap()

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
