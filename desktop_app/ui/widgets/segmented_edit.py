import re
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QLabel, QApplication
from PyQt6.QtCore import Qt, QEvent, pyqtSignal

class SegmentedCodeEdit(QWidget):
    """Custom composite text field for XX-XXX-XX-XX format."""
    
    # Custom signal emitted when Enter is pressed in any of the boxes
    returnPressed = pyqtSignal()
    textChanged = pyqtSignal() 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.edits = [QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()]
        lengths = [2, 3, 2, 2]
        
        for i, edit in enumerate(self.edits):
            edit.setMaxLength(lengths[i])
            edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit.setPlaceholderText('x' * lengths[i])
            
            # Set generous relative minimum widths to handle extreme scaling
            # Minimums are chosen to comfortably fit characters + padding at up to 200% scale
            min_w = lengths[i] * 16 + 24
            max_w = lengths[i] * 24 + 40
            edit.setMinimumWidth(min_w)
            edit.setMaximumWidth(max_w)
            
            edit.textChanged.connect(lambda text, idx=i: self.on_text_changed(text, idx))
            edit.textChanged.connect(self.textChanged.emit)
            edit.installEventFilter(self)
            # Route individual enter presses to the widget's global signal
            edit.returnPressed.connect(self.returnPressed.emit)
            layout.addWidget(edit)
            if i < 3:
                layout.addWidget(QLabel("-"))
                
        layout.addStretch()

    def on_text_changed(self, text, idx):
        if len(text) == self.edits[idx].maxLength() and idx < 3:
            self.edits[idx + 1].setFocus()
            self.edits[idx + 1].selectAll()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and obj in self.edits:
            # 1. Intercept Paste (Ctrl+V) before the text box chops it
            if event.key() == Qt.Key.Key_V and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                clipboard_text = QApplication.clipboard().text()
                self.set_code(clipboard_text)
                return True 
            
            # 2. Handle Backspace jumping
            if event.key() == Qt.Key.Key_Backspace and obj.text() == "":
                idx = self.edits.index(obj)
                if idx > 0:
                    self.edits[idx - 1].setFocus()
                    return False
        return super().eventFilter(obj, event)

    def get_code(self):
        parts = [edit.text().strip() for edit in self.edits]
        return "".join(parts)
        
    def get_segments(self):
        """Returns a list of the text in each segment, including empty ones."""
        return [edit.text().strip() for edit in self.edits]

    def set_code(self, code_str):
        clean = re.sub(r'[^a-zA-Z0-9]', '', code_str)
        self.clear()
        
        for edit in self.edits:
            max_l = edit.maxLength()
            chunk = clean[:max_l]
            clean = clean[max_l:]
            edit.setText(chunk)
            if not clean:
                break
                
        # Auto-fire enter when full string pasted (if it looks like a complete code)
        if len(re.sub(r'[^a-zA-Z0-9]', '', code_str)) >= 7:
            self.returnPressed.emit()

    def clear(self):
        for edit in self.edits:
            edit.clear()
