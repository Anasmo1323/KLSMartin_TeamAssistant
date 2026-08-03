import pandas as pd
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QWidget, QFormLayout, QComboBox, QLabel, QCheckBox, QPushButton, QMessageBox, QSpinBox

class MappingDialog(QDialog):
    """Dynamic window for mapping required logic fields and selecting additional columns."""
    def __init__(self, file_path, required_fields, optional_fields=None, allow_extras=True, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.required_fields = required_fields
        self.optional_fields = optional_fields or []
        self.allow_extras = allow_extras
        self.selected_sheet = None
        self.mappings = {}
        self.extras = [] 
        self.is_excel = file_path.endswith(('.xlsx', '.xls'))
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Map Columns")
        self.resize(450, 400)
        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        self.form_layout = QFormLayout(content_widget)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        self.header_spin = QSpinBox()
        self.header_spin.setRange(0, 100)
        self.header_spin.setValue(0)
        self.header_spin.valueChanged.connect(self.reload_columns)
        self.form_layout.addRow("Header Row Index (0 = first row):", self.header_spin)

        if self.is_excel:
            xl = pd.ExcelFile(self.file_path)
            self.sheet_combo = QComboBox()
            self.sheet_combo.addItems(xl.sheet_names)
            self.sheet_combo.currentTextChanged.connect(self.reload_columns)
            self.form_layout.addRow("Select Sheet:", self.sheet_combo)
            self.available_columns = xl.parse(xl.sheet_names[0], nrows=0, header=0).columns.tolist()
        else:
            df = pd.read_csv(self.file_path, nrows=0, header=0)
            self.available_columns = df.columns.tolist()

        self.form_layout.addRow(QLabel("<b>Required System Fields:</b>"))
        self.combos = {}
        for field in self.required_fields:
            combo = QComboBox()
            self.combos[field] = combo
            self.form_layout.addRow(f"Map to '{field}':", combo)
            
        if self.optional_fields:
            self.form_layout.addRow(QLabel("<b>Optional Fields:</b>"))
            for field in self.optional_fields:
                combo = QComboBox()
                self.combos[field] = combo
                self.form_layout.addRow(f"Map to '{field}':", combo)

        if self.allow_extras:
            self.form_layout.addRow(QLabel("<b>Additional Columns to Import:</b>"))
            self.extra_checkboxes = {}

        self.populate_combos()

        self.btn_submit = QPushButton("Confirm Mapping")
        self.btn_submit.setObjectName("primaryButton")
        self.btn_submit.clicked.connect(self.validate_and_accept)
        layout.addWidget(self.btn_submit)

    def populate_combos(self):
        for field, combo in self.combos.items():
            combo.clear()
            combo.addItems(["-- Select Column --"] + [str(c) for c in self.available_columns])
            for col in self.available_columns:
                if field.lower() in str(col).lower() or str(col).lower() in field.lower():
                    combo.setCurrentText(str(col))
                    break

        if self.allow_extras:
            for chk in getattr(self, 'extra_checkboxes', {}).values():
                chk.setParent(None)
            self.extra_checkboxes = {}
            for col in self.available_columns:
                chk = QCheckBox(str(col))
                chk.setChecked(True)
                self.extra_checkboxes[str(col)] = chk
                self.form_layout.addRow(chk)

    def reload_columns(self):
        header_idx = self.header_spin.value()
        if self.is_excel:
            sheet_name = self.sheet_combo.currentText() if hasattr(self, 'sheet_combo') else 0
            try:
                xl = pd.ExcelFile(self.file_path)
                self.available_columns = xl.parse(sheet_name, nrows=0, header=header_idx).columns.tolist()
            except Exception:
                self.available_columns = []
        else:
            try:
                df = pd.read_csv(self.file_path, nrows=0, header=header_idx)
                self.available_columns = df.columns.tolist()
            except Exception:
                self.available_columns = []
        self.populate_combos()

    def validate_and_accept(self):
        self.header_row = self.header_spin.value()
        self.mappings = {}
        if self.is_excel:
            self.selected_sheet = self.sheet_combo.currentText()
        
        for field, combo in self.combos.items():
            val = combo.currentText()
            if val == "-- Select Column --":
                if field in self.required_fields:
                    QMessageBox.warning(self, "Mapping Error", f"Please select a mapping for: {field}")
                    return
                else:
                    self.mappings[field] = None
            else:
                self.mappings[field] = val

        if self.allow_extras:
            used_cols = set(self.mappings.values())
            self.extras = [col for col, chk in self.extra_checkboxes.items() 
                           if chk.isChecked() and col not in used_cols]
            
        self.accept()
