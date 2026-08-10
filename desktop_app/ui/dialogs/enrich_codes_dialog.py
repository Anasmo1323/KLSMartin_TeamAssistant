import pandas as pd
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QTextEdit, QCheckBox, QScrollArea, QWidget, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt
from ui.dialogs.mapping_dialog import MappingDialog
from core.utils import show_loading

class EnrichCodesDialog(QDialog):
    def __init__(self, master_df, parent=None):
        super().__init__(parent)
        self.master_df = master_df
        self.selected_columns = []
        self.enriched_data = []
        
        self.setWindowTitle('Bulk Code Enrichment')
        self.resize(600, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 1. Code Input Area
        layout.addWidget(QLabel('<b>1. Input Codes</b>'))
        
        input_layout = QHBoxLayout()
        self.txt_codes = QTextEdit()
        self.txt_codes.setPlaceholderText('Paste a list of codes here (one per line)...')
        input_layout.addWidget(self.txt_codes)
        
        btn_layout = QVBoxLayout()
        self.btn_load_excel = QPushButton('Load from Excel')
        self.btn_load_excel.clicked.connect(self.load_from_excel)
        btn_layout.addWidget(self.btn_load_excel)
        btn_layout.addStretch()
        input_layout.addLayout(btn_layout)
        
        layout.addLayout(input_layout, stretch=1)

        # 2. Column Selection Area
        layout.addWidget(QLabel('<b>2. Select Columns to Enrich</b>'))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        
        exclude_cols = ['code']
        self.checkboxes = {}
        
        for col in self.master_df.columns:
            if col.lower() not in exclude_cols:
                chk = QCheckBox(col)
                self.checkboxes[col] = chk
                self.scroll_layout.addWidget(chk)
                
        self.scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, stretch=1)

        # 3. Process Buttons
        action_layout = QHBoxLayout()
        self.btn_process = QPushButton('Process && Add to Offer List')
        self.btn_process.setObjectName('primaryButton')
        self.btn_process.clicked.connect(self.process_codes)
        
        self.btn_cancel = QPushButton('Cancel')
        self.btn_cancel.clicked.connect(self.reject)
        
        action_layout.addStretch()
        action_layout.addWidget(self.btn_cancel)
        action_layout.addWidget(self.btn_process)
        layout.addLayout(action_layout)

    def load_from_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Select Data File', '', 'Data Files (*.csv *.xlsx *.xls)')
        if not file_path: return
        
        dlg = MappingDialog(file_path, ['code'], allow_extras=False, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                with show_loading(self, 'Loading codes...'):
                    if dlg.is_excel:
                        df = pd.read_excel(file_path, sheet_name=dlg.selected_sheet, header=dlg.header_row)
                    else:
                        df = pd.read_csv(file_path, header=dlg.header_row)
                        
                    code_col = dlg.mappings['code']
                    codes = df[code_col].dropna().astype(str).tolist()
                    self.txt_codes.setText('\n'.join(codes))
                QMessageBox.information(self, 'Loaded', f'Loaded {len(codes)} codes.')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to load file:\n{e}')

    def process_codes(self):
        raw_text = self.txt_codes.toPlainText()
        codes = [c.strip() for c in raw_text.split('\n') if c.strip()]
        if not codes:
            QMessageBox.warning(self, 'No Codes', 'Please input or load at least one code.')
            return

        self.selected_columns = [col for col, chk in self.checkboxes.items() if chk.isChecked()]
        
        if not self.selected_columns:
            reply = QMessageBox.question(self, "No Columns", "You haven't selected any columns to enrich. Add codes anyway?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return

        self.enriched_data = []
        not_found = []
        
        clean_master = self.master_df.copy()
        clean_master['clean_code'] = clean_master['code'].astype(str).str.replace('-', '').str.strip().str.lower()
        
        for code in codes:
            clean_input = str(code).replace('-', '').strip().lower()
            match = clean_master[clean_master['clean_code'] == clean_input]
            
            if match.empty:
                not_found.append(code)
                continue
                
            row = match.iloc[0]
            
            item = {
                'code': str(row.get('code', code)),
                'desc': str(row.get('description', 'N/A')),
                'qty': 1,
                'is_section': False
            }
            
            for col in self.selected_columns:
                item[col] = str(row.get(col, ''))
                
            self.enriched_data.append(item)
            
        if not_found:
            msg = f'Processed {len(self.enriched_data)} items.\n\n{len(not_found)} codes were not found:\n'
            msg += ', '.join(not_found[:10])
            if len(not_found) > 10:
                msg += '...'
            QMessageBox.warning(self, 'Result', msg)
        else:
            QMessageBox.information(self, 'Success', f'Successfully processed all {len(self.enriched_data)} items.')
            
        self.accept()
