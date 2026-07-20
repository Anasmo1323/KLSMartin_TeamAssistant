import pandas as pd
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QHeaderView, QFileDialog, 
                             QMessageBox, QDialog, QTableWidgetItem, QComboBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIntValidator

from ui.widgets.segmented_edit import SegmentedCodeEdit
from ui.widgets.dynamic_table import DynamicTableWidget
from ui.dialogs.mapping_dialog import MappingDialog
from core.utils import show_loading

class InspectionTab(QWidget):
    def __init__(self, master_tab):
        super().__init__()
        self.master_tab = master_tab
        self.df = None 
        self.extras = []
        self.display_cols = []
        self.current_file_path = None
        self.is_modified = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)
        self.btn_upload = QPushButton("Upload Verification Manifest")
        self.btn_upload.clicked.connect(self.upload_manifest)
        top_layout.addWidget(self.btn_upload)
        
        self.btn_save = QPushButton("Save Overwrite")
        self.btn_save.clicked.connect(self.save_file)
        self.btn_save.setEnabled(False)
        top_layout.addWidget(self.btn_save)

        self.btn_save_as = QPushButton("Save As...")
        self.btn_save_as.clicked.connect(self.save_as_file)
        self.btn_save_as.setEnabled(False)
        top_layout.addWidget(self.btn_save_as)
        layout.addLayout(top_layout)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("<b>Global Filter:</b>"))
        self.txt_global_search = QLineEdit()
        self.txt_global_search.returnPressed.connect(self.apply_filter)
        filter_layout.addWidget(self.txt_global_search)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All Items", None)
        self.filter_combo.addItem("Code Not Found", "not_found")
        self.filter_combo.addItem("No Image", "no_image")
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_combo)
        
        self.btn_search = QPushButton("🔍")
        self.btn_search.setFixedWidth(50)
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.clicked.connect(self.apply_filter)
        filter_layout.addWidget(self.btn_search)
        
        layout.addLayout(filter_layout)

        # Enhanced Verification Input Row (Includes Quantity Flow)
        verify_layout = QHBoxLayout()
        verify_layout.addWidget(QLabel("<b>Code Found:</b>"))
        self.code_verify_input = SegmentedCodeEdit()
        
        # When code is entered, shift focus to the Quantity box
        self.code_verify_input.returnPressed.connect(self.focus_qty_box)
        verify_layout.addWidget(self.code_verify_input)

        verify_layout.addWidget(QLabel("<b>Qty:</b>"))
        self.qty_input = QLineEdit("1")
        self.qty_input.setValidator(QIntValidator(1, 9999))
        self.qty_input.setFixedWidth(60)
        self.qty_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # When Enter is pressed on Qty, execute the batch verification
        self.qty_input.returnPressed.connect(self.process_verification)
        verify_layout.addWidget(self.qty_input)

        self.btn_verify = QPushButton("Confirm Batch")
        self.btn_verify.setObjectName("primaryButton")
        self.btn_verify.clicked.connect(self.process_verification)
        verify_layout.addWidget(self.btn_verify)
        layout.addLayout(verify_layout)

        self.table = DynamicTableWidget()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(130)
        self.table.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.table)

    def upload_manifest(self):
        if self.is_modified:
            reply = QMessageBox.question(self, 'Unsaved Changes', 
                "You have unsaved changes. Discard and upload new?", 
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No: return

        file_path, _ = QFileDialog.getOpenFileName(self, "Open Manifest File", "", "Data Files (*.csv *.xlsx *.xls)")
        if not file_path: return

        dlg = MappingDialog(file_path, ['code', 'quantity'], allow_extras=True, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            with show_loading(self, "Processing Manifest File..."):
                try:
                    if dlg.is_excel:
                        raw_df = pd.read_excel(file_path, sheet_name=dlg.selected_sheet, header=dlg.header_row)
                    else:
                        raw_df = pd.read_csv(file_path, header=dlg.header_row)

                    inverted_map = {v: k for k, v in dlg.mappings.items()}
                    cols_to_keep = list(dlg.mappings.values()) + getattr(dlg, 'extras', [])
                    self.df = raw_df[cols_to_keep].rename(columns=inverted_map)
                    self.extras = getattr(dlg, 'extras', [])
                    self.current_file_path = file_path
                    
                    self.df['quantity'] = pd.to_numeric(self.df['quantity'], errors='coerce').fillna(0).astype(int)
                    if 'inspected' not in self.df.columns:
                        self.df['inspected'] = 0 
                    if 'status' not in self.df.columns:
                        self.df['status'] = "PENDING"
                    
                    self.set_modified(False)
                    self.btn_save.setEnabled(True)
                    self.btn_save_as.setEnabled(True)
                    self.populate_table(self.df)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed processing manifest: {e}")

    def populate_table(self, dataframe):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        if dataframe is None or dataframe.empty:
            self.table.blockSignals(False)
            return

        self.display_cols = ['code', 'quantity'] + self.extras + ['inspected', 'status']
        self.table.setColumnCount(len(self.display_cols))
        self.table.setHorizontalHeaderLabels([c.upper() for c in self.display_cols])

        self.table.setRowCount(len(dataframe))
        for ui_row_idx, (orig_idx, row) in enumerate(dataframe.iterrows()):
            status = str(row.get('status', 'PENDING'))
            
            for c_idx, col_name in enumerate(self.display_cols):
                val = str(row.get(col_name, ''))
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, orig_idx)
                
                # Make status strictly read-only, others are double-click editable
                if col_name == 'status':
                    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                else:
                    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled)
                
                if status == "CLEARED":
                    item.setBackground(QColor("#D4EDDA")) 
                    item.setForeground(QColor("#155724"))
                
                self.table.setItem(ui_row_idx, c_idx, item)
        self.table.blockSignals(False)
        
        if self.table.rowCount() > 0:
            self.table.selectRow(0)
            self.table.setCurrentCell(0, 0)

    def on_item_changed(self, item):
        orig_idx = item.data(Qt.ItemDataRole.UserRole)
        if orig_idx is not None and self.df is not None:
            col_name = self.display_cols[item.column()]
            self.df.at[orig_idx, col_name] = item.text()
            self.set_modified(True)

            # Auto-update status if manual qty/inspected edits occurred
            if col_name in ['quantity', 'inspected']:
                try:
                    q = int(self.df.at[orig_idx, 'quantity'])
                    i = int(self.df.at[orig_idx, 'inspected'])
                    new_status = "CLEARED" if i >= q else "PENDING"
                    if self.df.at[orig_idx, 'status'] != new_status:
                        self.df.at[orig_idx, 'status'] = new_status
                        self.apply_filter() # Refresh table colors
                except: pass

    def focus_qty_box(self):
        """Moves cursor to quantity box and highlights text for quick typing"""
        self.qty_input.setFocus()
        self.qty_input.selectAll()

    def process_verification(self):
        if self.df is None or self.df.empty: return

        target_code = self.code_verify_input.get_code().strip().replace('-', '').lower()
        if not target_code: return

        mask = self.df['code'].astype(str).str.replace('-', '').str.strip().str.lower() == target_code
        indices = self.df[mask].index

        if len(indices) == 0:
            QMessageBox.critical(self, "Invalid Match", "Code not found in client manifest.")
            self.code_verify_input.clear()
            self.code_verify_input.edits[0].setFocus()
            return

        idx = indices[0]
        try:
            qty_to_add = int(self.qty_input.text())
        except:
            qty_to_add = 1

        current_inspected = int(self.df.at[idx, 'inspected'])
        target_max = int(self.df.at[idx, 'quantity'])

        if current_inspected < target_max:
            new_inspected = min(current_inspected + qty_to_add, target_max) # Prevent exceeding target via batch
            self.df.at[idx, 'inspected'] = new_inspected
            if new_inspected == target_max:
                self.df.at[idx, 'status'] = "CLEARED"
            
            self.set_modified(True)
            self.apply_filter()
            
            # Workflow Reset
            self.code_verify_input.clear()
            self.qty_input.setText("1")
            self.code_verify_input.edits[0].setFocus()
        else:
            QMessageBox.warning(self, "Limit Reached", f"Item already hit maximum target limit ({target_max}).")
            self.code_verify_input.clear()
            self.code_verify_input.edits[0].setFocus()

    def set_modified(self, state):
        self.is_modified = state
        indicator = " *(Unsaved)*" if state else ""
        self.btn_save.setText(f"Save Overwrite{indicator}")

    def save_file(self):
        if self.current_file_path:
            self._execute_save(self.current_file_path)
        else:
            self.save_as_file()

    def save_as_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save File As", "", "Excel Files (*.xlsx);;CSV Files (*.csv)")
        if path:
            self._execute_save(path)

    def _execute_save(self, path):
        try:
            if path.endswith('.csv'):
                self.df.to_csv(path, index=False)
            else:
                self.df.to_excel(path, index=False)
            self.current_file_path = path
            self.set_modified(False)
            QMessageBox.information(self, "Saved", f"File saved successfully:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")

    def apply_filter(self):
        if self.df is None or self.df.empty: return
        g_search = self.txt_global_search.text().strip().lower()
        filtered = self.df.copy()
        
        filter_type = self.filter_combo.currentData()
        if filter_type in ["not_found", "no_image"]:
            master_df = self.master_tab.df
            if master_df is None or master_df.empty:
                self.filter_combo.blockSignals(True)
                self.filter_combo.setCurrentIndex(0)
                self.filter_combo.blockSignals(False)
                QMessageBox.warning(self, "Warning", "Please upload Master CSV first.")
            else:
                clean_codes = filtered['code'].astype(str).str.replace('-', '').str.strip().str.lower()
                master_codes = master_df['code'].astype(str).str.replace('-', '').str.strip().str.lower()
                
                if filter_type == "not_found":
                    mask = ~clean_codes.isin(master_codes)
                    filtered = filtered[mask]
                elif filter_type == "no_image":
                    import os
                    def check_exists(path):
                        if pd.isna(path): return False
                        path = str(path).strip()
                        if path in {"", "No Image", "Download Failed", "HTTP Error", "nan"}: return False
                        return os.path.exists(path)
                        
                    valid_img_mask = master_df['local_image_path'].apply(check_exists)
                    valid_codes_with_img = master_df.loc[valid_img_mask, 'code'].astype(str).str.replace('-', '').str.strip().str.lower()
                    mask = clean_codes.isin(master_codes) & ~clean_codes.isin(valid_codes_with_img)
                    filtered = filtered[mask]
        
        if g_search:
            mask = filtered.astype(str).apply(lambda x: x.str.lower().str.contains(g_search)).any(axis=1)
            filtered = filtered[mask]
        self.populate_table(filtered)
