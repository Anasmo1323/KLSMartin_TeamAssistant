import os
import pandas as pd
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt
from core.utils import show_loading

class SetSelectionDialog(QDialog):
    def __init__(self, master_tab, parent=None):
        super().__init__(parent)
        self.master_tab = master_tab
        self.sets_df = None
        self.unique_sets_df = None
        self.selected_set_code = None
        self.setWindowTitle("Select Instrument Set")
        self.resize(700, 500)
        self.init_ui()
        self.load_sets_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Source selection
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Set Source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(["ALMA Sets", "Technowave Sets"])
        self.source_combo.currentIndexChanged.connect(self.load_sets_data)
        source_layout.addWidget(self.source_combo)
        layout.addLayout(source_layout)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search Sets:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type Set Name or Code...")
        self.search_input.textChanged.connect(self.filter_sets)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Set Code", "Set Name", "Discipline"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self.accept_selection)
        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("Load Selected Set")
        self.btn_load.clicked.connect(self.accept_selection)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_load)
        layout.addLayout(btn_layout)

    def load_sets_data(self):
        source = self.source_combo.currentText()
        if source == "ALMA Sets":
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            file_path = os.path.join(base_dir, "data", "ALMA_Sets_Export.xlsx")
            if not os.path.exists(file_path):
                self.populate_table(None)
                return
            with show_loading(self, "Loading ALMA Sets..."):
                try:
                    self.sets_df = pd.read_excel(file_path)
                    self.unique_sets_df = self.sets_df[['Set_Code', 'Set_Name', 'Discipline']].drop_duplicates()
                    self.unique_sets_df = self.unique_sets_df.dropna(subset=['Set_Code'])
                    self.populate_table(self.unique_sets_df)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Could not load ALMA sets: {e}")
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            file_path = os.path.join(base_dir, "data", "master_surgical_sets.xlsx")
            if not os.path.exists(file_path):
                self.populate_table(None)
                return
            with show_loading(self, "Loading Technowave Sets..."):
                try:
                    xls = pd.ExcelFile(file_path)
                    rows = []
                    for sheet_name in xls.sheet_names:
                        rows.append({
                            'Set_Code': sheet_name,
                            'Set_Name': sheet_name,
                            'Discipline': 'Technowave'
                        })
                    self.unique_sets_df = pd.DataFrame(rows)
                    self.populate_table(self.unique_sets_df)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Could not load Technowave sets: {e}")

    def populate_table(self, df):
        self.table.setRowCount(0)
        if df is None or df.empty:
            return
            
        self.table.setRowCount(len(df))
        for row_idx, (_, row) in enumerate(df.iterrows()):
            code_item = QTableWidgetItem(str(row.get('Set_Code', '')))
            name_item = QTableWidgetItem(str(row.get('Set_Name', '')))
            disc_item = QTableWidgetItem(str(row.get('Discipline', '')))
            
            self.table.setItem(row_idx, 0, code_item)
            self.table.setItem(row_idx, 1, name_item)
            self.table.setItem(row_idx, 2, disc_item)

    def filter_sets(self, text):
        if self.unique_sets_df is None or self.unique_sets_df.empty:
            return
        if not text.strip():
            self.populate_table(self.unique_sets_df)
            return
            
        text = text.lower()
        mask = (
            self.unique_sets_df['Set_Code'].astype(str).str.lower().str.contains(text, na=False) |
            self.unique_sets_df['Set_Name'].astype(str).str.lower().str.contains(text, na=False)
        )
        filtered = self.unique_sets_df[mask]
        self.populate_table(filtered)

    def accept_selection(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Select Set", "Please select a set from the list.")
            return
            
        code_item = self.table.item(current_row, 0)
        if code_item:
            self.selected_set_code = code_item.text()
            self.accept()
            
    def get_selected_items(self):
        if not self.selected_set_code:
            return None
            
        source = self.source_combo.currentText()
        if source == "ALMA Sets":
            if self.sets_df is None: return None
            return self.sets_df[self.sets_df['Set_Code'].astype(str) == self.selected_set_code]
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            file_path = os.path.join(base_dir, "data", "master_surgical_sets.xlsx")

            if not os.path.exists(file_path): return None
            try:
                df = pd.read_excel(file_path, sheet_name=self.selected_set_code, header=1)
                mapped = pd.DataFrame()
                mapped['Item_SKU'] = df.get('Article No', df.iloc[:, 0] if not df.empty else [])
                mapped['Item_Name'] = df.get('Description', df.iloc[:, 1] if df.shape[1] > 1 else [])
                mapped['Quantity'] = df.get('Qty', df.iloc[:, 2] if df.shape[1] > 2 else [])
                mapped['Set_Code'] = self.selected_set_code
                return mapped
            except Exception as e:
                print(f"Error parsing Technowave set: {e}")
                return None
