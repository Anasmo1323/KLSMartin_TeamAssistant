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


def safe_read_csv(filepath_or_buffer, **kwargs):
    """
    Robust CSV reader that attempts multiple common encodings 
    (utf-8, utf-8-sig, cp1256, cp1252, latin1, iso-8859-1) to prevent UnicodeDecodeError.
    """
    import pandas as pd
    encodings = ['utf-8', 'utf-8-sig', 'cp1256', 'cp1252', 'latin1', 'iso-8859-1']
    last_err = None
    for enc in encodings:
        try:
            if not isinstance(filepath_or_buffer, (str, bytes)) and hasattr(filepath_or_buffer, 'seek'):
                filepath_or_buffer.seek(0)
            return pd.read_csv(filepath_or_buffer, encoding=enc, **kwargs)
        except (UnicodeDecodeError, UnicodeError) as e:
            last_err = e
            continue
    try:
        if not isinstance(filepath_or_buffer, (str, bytes)) and hasattr(filepath_or_buffer, 'seek'):
            filepath_or_buffer.seek(0)
        return pd.read_csv(filepath_or_buffer, encoding_errors='replace', **kwargs)
    except Exception:
        if last_err:
            raise last_err
        raise
