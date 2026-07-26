from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QLineEdit
from PyQt6.QtCore import Qt, pyqtSignal

class CheckableListWidget(QWidget):
    selectionChanged = pyqtSignal()
    
    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self.list_widget = QListWidget()
        self.list_widget.itemChanged.connect(self._on_item_changed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self.filter_list)
        layout.addWidget(self.search_bar)
        
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
        
    def filter_list(self, text):
        search_text = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(search_text not in item.text().lower())

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

class CheckableTreeWidget(QWidget):
    selectionChanged = pyqtSignal()
    
    def __init__(self, hierarchy=None, items=None, parent=None):
        super().__init__(parent)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setIndentation(14)
        self.tree_widget.itemChanged.connect(self._on_item_changed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self.filter_tree)
        layout.addWidget(self.search_bar)
        
        btn_layout = QHBoxLayout()
        self.btn_all = QPushButton("Select All")
        self.btn_all.clicked.connect(self.select_all)
        self.btn_none = QPushButton("Clear")
        self.btn_none.clicked.connect(self.clear_selection)
        
        btn_layout.addWidget(self.btn_all)
        btn_layout.addWidget(self.btn_none)
        
        layout.addLayout(btn_layout)
        layout.addWidget(self.tree_widget)
        
        self.hierarchy = hierarchy or {}
        
        if items:
            self.set_items(items)
            
    def set_items(self, items):
        self.tree_widget.blockSignals(True)
        self.tree_widget.clear()
        
        mapped_items = set()
        
        for main_category in sorted(self.hierarchy.keys()):
            sub_items = self.hierarchy[main_category]
            matching_subs = sorted([s for s in sub_items if s in items])
            
            if matching_subs or main_category in items:
                parent_item = QTreeWidgetItem(self.tree_widget, [main_category])
                parent_item.setFlags(parent_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
                parent_item.setCheckState(0, Qt.CheckState.Unchecked)
                
                if main_category in items:
                    mapped_items.add(main_category)
                    
                for sub in matching_subs:
                    child = QTreeWidgetItem(parent_item, [sub])
                    child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    child.setCheckState(0, Qt.CheckState.Unchecked)
                    mapped_items.add(sub)
                    
                parent_item.setExpanded(False)
                
        unmapped = [i for i in items if i not in mapped_items]
        if unmapped:
            other_parent = QTreeWidgetItem(self.tree_widget, ["Other Brochures"])
            other_parent.setFlags(other_parent.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            other_parent.setCheckState(0, Qt.CheckState.Unchecked)
            
            for um in sorted(unmapped):
                child = QTreeWidgetItem(other_parent, [um])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Unchecked)
                
            other_parent.setExpanded(False)

        self.tree_widget.blockSignals(False)
        
    def filter_tree(self, text):
        search_text = text.lower()
        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            parent = root.child(i)
            parent_match = search_text in parent.text(0).lower()
            any_child_match = False
            for j in range(parent.childCount()):
                child = parent.child(j)
                child_match = search_text in child.text(0).lower()
                child.setHidden(not (parent_match or child_match))
                if child_match:
                    any_child_match = True
            
            parent.setHidden(not (parent_match or any_child_match))
            if text and any_child_match:
                parent.setExpanded(True)

    def _on_item_changed(self, item, column):
        self.selectionChanged.emit()
        
    def get_checked_items(self):
        checked = []
        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            parent = root.child(i)
            if parent.checkState(0) in (Qt.CheckState.Checked, Qt.CheckState.PartiallyChecked):
                if parent.text(0) != "Other Brochures" and parent.checkState(0) == Qt.CheckState.Checked:
                    checked.append(parent.text(0))
                for j in range(parent.childCount()):
                    child = parent.child(j)
                    if child.checkState(0) == Qt.CheckState.Checked:
                        checked.append(child.text(0))
        return list(set(checked))

    def select_all(self):
        self.tree_widget.blockSignals(True)
        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            root.child(i).setCheckState(0, Qt.CheckState.Checked)
        self.tree_widget.blockSignals(False)
        self.selectionChanged.emit()

    def clear_selection(self):
        self.tree_widget.blockSignals(True)
        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            root.child(i).setCheckState(0, Qt.CheckState.Unchecked)
        self.tree_widget.blockSignals(False)
        self.selectionChanged.emit()
