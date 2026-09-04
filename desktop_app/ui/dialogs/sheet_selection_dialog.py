from PyQt6.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QWidget, QCheckBox, QPushButton, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt

class SheetSelectionDialog(QDialog):
    def __init__(self, sheet_names, parent=None):
        super().__init__(parent)
        self.sheet_names = sheet_names
        self.checkboxes = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Select Sheets to Export")
        self.resize(400, 500)
        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        self.list_layout = QVBoxLayout(content_widget)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        for sheet in self.sheet_names:
            chk = QCheckBox(sheet)
            chk.setChecked(True)
            self.checkboxes.append(chk)
            self.list_layout.addWidget(chk)

        btn_layout = QHBoxLayout()
        btn_select_all = QPushButton("Select All")
        btn_select_all.clicked.connect(lambda: self.set_all(True))
        btn_deselect_all = QPushButton("Deselect All")
        btn_deselect_all.clicked.connect(lambda: self.set_all(False))
        btn_layout.addWidget(btn_select_all)
        btn_layout.addWidget(btn_deselect_all)
        layout.addLayout(btn_layout)

        action_layout = QHBoxLayout()
        btn_ok = QPushButton("Export Selected")
        btn_ok.setObjectName("primaryButton")
        btn_ok.clicked.connect(self.validate_and_accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        action_layout.addWidget(btn_cancel)
        action_layout.addWidget(btn_ok)
        layout.addLayout(action_layout)

    def set_all(self, state):
        for chk in self.checkboxes:
            chk.setChecked(state)

    def validate_and_accept(self):
        selected = self.get_selected_sheets()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select at least one sheet to export.")
            return
        self.accept()

    def get_selected_sheets(self):
        return [chk.text() for chk in self.checkboxes if chk.isChecked()]
