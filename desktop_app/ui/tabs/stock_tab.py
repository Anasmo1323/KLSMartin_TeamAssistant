import pandas as pd
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QHeaderView, QFileDialog, 
                             QMessageBox, QDialog, QTableWidgetItem, QComboBox)
from PyQt6.QtCore import Qt, QTimer

from ui.widgets.segmented_edit import SegmentedCodeEdit
from ui.widgets.dynamic_table import DynamicTableWidget
from ui.dialogs.mapping_dialog import MappingDialog
from core.utils import show_loading

class StockTab(QWidget):
    def __init__(self, master_tab):
        super().__init__()
        self.master_tab = master_tab
        self.df = None
        self.extras = []
        self.display_cols = []
        self.current_file_path = None
        self.default_path = "stock_data.csv"
        self.is_modified = False
        self.init_ui()
        QTimer.singleShot(100, self.load_default_stock)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(8)
        
        # TOP CONTROLS (Upload & Saving)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)
        self.btn_upload = QPushButton("Upload Stock File")
        self.btn_upload.clicked.connect(self.upload_stock)
        top_layout.addWidget(self.btn_upload)
        
        self.btn_save = QPushButton("Save Overwrite")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.clicked.connect(self.save_file)
        self.btn_save.setEnabled(False)
        top_layout.addWidget(self.btn_save)

        self.btn_save_as = QPushButton("Save As...")
        self.btn_save_as.clicked.connect(self.save_as_file)
        self.btn_save_as.setEnabled(False)
        top_layout.addWidget(self.btn_save_as)
        
        main_layout.addLayout(top_layout)
        
        # SEARCH CONTROLS
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Global Search:"))
        self.txt_global_search = QLineEdit()
        self.txt_global_search.returnPressed.connect(self.apply_filter)
        search_layout.addWidget(self.txt_global_search)

        search_layout.addWidget(QLabel("Code Search:"))
        self.code_search = SegmentedCodeEdit()
        self.code_search.returnPressed.connect(self.apply_filter)
        search_layout.addWidget(self.code_search)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All Items", None)
        self.filter_combo.addItem("Code Not Found", "not_found")
        self.filter_combo.addItem("No Image", "no_image")
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)
        search_layout.addWidget(self.filter_combo)
        
        self.btn_search = QPushButton("🔍")
        self.btn_search.setFixedWidth(50)
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.clicked.connect(self.apply_filter)
        search_layout.addWidget(self.btn_search)

        main_layout.addLayout(search_layout)

        # MAIN WORKSPACE (Table + Side Panel)
        workspace_layout = QHBoxLayout()
        
        # Grid
        self.table = DynamicTableWidget()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(150)
        self.table.itemChanged.connect(self.on_item_changed)
        workspace_layout.addWidget(self.table)

        main_layout.addLayout(workspace_layout)

    def load_default_stock(self):
        import os
        import pandas as pd
        if os.path.exists(self.default_path):
            with show_loading(self, "Loading Stock Data..."):
                try:
                    self.df = pd.read_csv(self.default_path)
                    self.df.columns = [c.lower().strip() for c in self.df.columns]
                    self.populate_table(self.df)
                except Exception as e:
                    print(f"Could not load default stock: {e}")

    def upload_stock(self):
        if self.is_modified:
            reply = QMessageBox.question(self, 'Unsaved Changes', 
                "You have unsaved changes. Discard and upload new?", 
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return

        file_path, _ = QFileDialog.getOpenFileName(self, "Open Stock File", "", "Data Files (*.csv *.xlsx *.xls)")
        if not file_path: return

        dlg = MappingDialog(file_path, ['code', 'quantity'], allow_extras=True, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            with show_loading(self, "Processing Stock Data..."):
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
                    self.set_modified(False)
                    
                    self.btn_save.setEnabled(True)
                    self.btn_save_as.setEnabled(True)
                    self.populate_table(self.df)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed processing file: {e}")

    def populate_table(self, dataframe):
        self.table.blockSignals(True) # Prevent filling from triggering 'modified'
        self.table.setRowCount(0)
        if dataframe is None or dataframe.empty:
            self.table.blockSignals(False)
            return

        self.display_cols = ['code', 'quantity'] + self.extras
        self.table.setColumnCount(len(self.display_cols))
        self.table.setHorizontalHeaderLabels([c.upper() for c in self.display_cols])

        self.table.setRowCount(len(dataframe))
        for ui_row_idx, (orig_idx, row) in enumerate(dataframe.iterrows()):
            for c_idx, col_name in enumerate(self.display_cols):
                val = str(row.get(col_name, ''))
                item = QTableWidgetItem(val)
                # Store original dataframe index safely hidden in the UI element
                item.setData(Qt.ItemDataRole.UserRole, orig_idx)
                # Ensure items are editable (default) and selectable
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled)
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
        c_parts = [p.strip().lower() for p in self.code_search.get_segments()]

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
            
        if any(c_parts):
            splits = filtered['code'].astype(str).str.lower().str.split('-', expand=True)
            for i, search_part in enumerate(c_parts):
                if search_part:
                    if i in splits.columns:
                        filtered = filtered[splits[i].str.startswith(search_part, na=False)]
                    else:
                        filtered = filtered.iloc[0:0]

        self.populate_table(filtered)
