from PyQt6.QtWidgets import QDialog, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from ui.widgets.custom_labels import ClickableImageLabel

class FullscreenImageDialog(QDialog):
    """Dialog window to display the full-resolution image safely."""
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Full Screen Image Viewer")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Reuse our smart painting label for the full screen to prevent growth loops
        self.img_label = ClickableImageLabel()
        self.img_label.setToolTip("") 
        self.img_label.setCursor(Qt.CursorShape.ArrowCursor)
        self.img_label.setStyleSheet("background-color: #000000;") # Optional: dark background for viewer
        
        from core.utils import safe_load_pixmap
        pixmap = safe_load_pixmap(image_path)
        self.img_label.set_image(pixmap, None)
        
        layout.addWidget(self.img_label)
