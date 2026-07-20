import os
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter

class ClickableImageLabel(QLabel):
    """Custom label that natively scales and centers images using QPainter."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image_path = None
        self.current_pixmap = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Double-click to expand image")
        self.setMinimumSize(100, 100) # Allows shrinking when panel is resized
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_image(self, pixmap, path):
        self.current_pixmap = pixmap
        self.current_image_path = path
        self.setText("") # Clear fallback text
        self.update() # Trigger a repaint
        
    def clear_image(self, text):
        self.current_pixmap = None
        self.current_image_path = None
        self.setText(text)
        self.update()

    def paintEvent(self, event):
        """Draws the image natively centered while preserving aspect ratio."""
        # 1. Allow the base QLabel to paint the background and borders first
        super().paintEvent(event)
        
        # 2. Open our custom painter only if there is an image to draw
        if self.current_pixmap and not self.current_pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            
            scaled = self.current_pixmap.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            
            # Calculate precise center coordinates
            x = int((self.width() - scaled.width()) / 2)
            y = int((self.height() - scaled.height()) / 2)
            
            # Draw the image in the calculated center
            painter.drawPixmap(x, y, scaled)
            
            # 3. Explicitly close the painter to free the memory and avoid engine conflicts
            painter.end()

    def mouseDoubleClickEvent(self, event):
        # We need to import FullscreenImageDialog here or absolute import it. 
        # The prompt requires absolute imports and minimizing footprint.
        from ui.dialogs.image_dialog import FullscreenImageDialog
        if event.button() == Qt.MouseButton.LeftButton and self.current_image_path:
            if os.path.exists(self.current_image_path):
                dialog = FullscreenImageDialog(self.current_image_path, self)
                dialog.exec()
