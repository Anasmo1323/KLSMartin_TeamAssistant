from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal

class CheckableListWidget(QWidget):
    selectionChanged = pyqtSignal()
    
    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self.list_widget = QListWidget()
        self.list_widget.itemChanged.connect(self._on_item_changed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        btn_layout = QHBoxLayout()
        self.btn_all = QPushButton("Select All")
        self.btn_all.clicked.connect(self.select_all)
        self.btn_none = QPushButton("Clear")
        self.btn_none.clicked.connect(self.clear_selection)
        
        btn_layout.addWidget(self.btn_all)
        btn_layout.addWidget(self.btn_none)
        
        layout.addLayout(btn_layout)
        layout.addWidget(self.list_widget)
        
        if items:
            self.set_items(items)
            
    def set_items(self, items):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for item_text in items:
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)
        
    def _on_item_changed(self, item):
        self.selectionChanged.emit()
        
    def get_checked_items(self):
        checked = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked.append(item.text())
        return checked

    def select_all(self):
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Checked)
        self.list_widget.blockSignals(False)
        self.selectionChanged.emit()

    def clear_selection(self):
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)
        self.list_widget.blockSignals(False)
        self.selectionChanged.emit()
