import os
import re
import pandas as pd
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QHeaderView, QFileDialog, QDialog, QMessageBox, QTableWidgetItem, QInputDialog, QSplitter
from PyQt6.QtCore import Qt, QTimer

from ui.widgets.segmented_edit import SegmentedCodeEdit
from ui.widgets.dynamic_table import DynamicTableWidget
from ui.dialogs.mapping_dialog import MappingDialog
from ui.dialogs.offer_dialog import OfferListDialog
from ui.widgets.checkable_list import CheckableListWidget, CheckableTreeWidget
from core.constants import CATEGORY_MAPPING, BROCHURE_HIERARCHY
from core.utils import show_loading, resource_path
from PyQt6.QtWidgets import QStackedWidget
from PyQt6.QtGui import QPixmap

class KlsMasterTab(QWidget):
    def __init__(self):
        super().__init__()
        self.df = None
        self.offer_data = []
        self.default_path = "KLS_All_Products.xlsx"
        self.required_fields = ['code', 'description', 'brochures', 'product_url']
        
        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self.apply_filter)
        
        self.init_ui()
        QTimer.singleShot(100, self.load_default_master)
        
    def queue_filter(self):
        self.filter_timer.start(300)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(8)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        # Left Panel (Filters - Vertical Splitter)
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        
        cat_widget = QWidget()
        cat_layout = QVBoxLayout(cat_widget)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        cat_layout.setSpacing(8)
        cat_layout.addWidget(QLabel("<b>Categories</b>"))
        self.category_list = CheckableListWidget(items=list(CATEGORY_MAPPING.values()))
        self.category_list.selectionChanged.connect(self.queue_filter)
        self.category_list.setMinimumWidth(250)
        cat_layout.addWidget(self.category_list)
        left_splitter.addWidget(cat_widget)
        
        bro_widget = QWidget()
        bro_layout = QVBoxLayout(bro_widget)
        bro_layout.setContentsMargins(0, 0, 0, 0)
        bro_layout.setSpacing(8)
        bro_layout.addWidget(QLabel("<b>Brochures</b>"))
        # self.brochure_list = CheckableListWidget()
        self.brochure_list = CheckableTreeWidget(hierarchy=BROCHURE_HIERARCHY)
        self.brochure_list.selectionChanged.connect(self.queue_filter)
        self.brochure_list.setMinimumWidth(250)
        bro_layout.addWidget(self.brochure_list)
        left_splitter.addWidget(bro_widget)
        
        main_splitter.addWidget(left_splitter)

        # Right Panel (Search & Content)
        right_widget = QWidget()
        right_panel = QVBoxLayout(right_widget)
        right_panel.setContentsMargins(0, 0, 0, 0)
        
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        
        self.txt_global_search = QLineEdit()
        self.txt_global_search.setPlaceholderText("Global Search...")
        self.txt_global_search.setMinimumWidth(150)
        self.txt_global_search.setMaximumWidth(300)
        self.txt_global_search.returnPressed.connect(self.queue_filter)
        search_layout.addWidget(self.txt_global_search)

        self.code_search = SegmentedCodeEdit()
        self.code_search.returnPressed.connect(self.queue_filter)
        search_layout.addWidget(self.code_search)

        self.btn_search = QPushButton("🔍")
        self.btn_search.setMinimumWidth(50)
        self.btn_search.setMaximumWidth(70)
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.clicked.connect(self.queue_filter)
        search_layout.addWidget(self.btn_search)

        self.btn_manage_offer = QPushButton("📝")
        self.btn_manage_offer.setToolTip("Manage Offer List")
        self.btn_manage_offer.setMinimumWidth(50)
        self.btn_manage_offer.setMaximumWidth(80)
        self.btn_manage_offer.setObjectName("primaryButton")
        self.btn_manage_offer.clicked.connect(self.open_offer_list)
        search_layout.addWidget(self.btn_manage_offer)

        self.btn_upload = QPushButton("📂")
        self.btn_upload.setToolTip("Upload Master File (Overwrite)")
        self.btn_upload.setMinimumWidth(50)
        self.btn_upload.setMaximumWidth(80)
        self.btn_upload.clicked.connect(self.upload_new_master)
        search_layout.addWidget(self.btn_upload)
        
        search_layout.addStretch()
        right_panel.addLayout(search_layout)

        self.stacked_widget = QStackedWidget()
        
        # Placeholder Image
        self.placeholder_label = QLabel()
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(resource_path("icon.ico"))
        if not pixmap.isNull():
            self.placeholder_label.setPixmap(pixmap.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.placeholder_label.setText("No search active.")
        self.stacked_widget.addWidget(self.placeholder_label)

        # Table
        self.table = DynamicTableWidget()
        headers = ["ADD"] + [f.upper() for f in self.required_fields]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(200)
        self.table.setColumnWidth(0, 54)
        
        self.stacked_widget.addWidget(self.placeholder_label)
        self.stacked_widget.addWidget(self.table)
        self.stacked_widget.setCurrentWidget(self.placeholder_label)

        right_panel.addWidget(self.stacked_widget)
        main_splitter.addWidget(right_widget)
        
        # Set standard initial ratios for Master Tab
        main_splitter.setSizes([300, 900])

    def _update_brochures_list(self):
        if self.df is None or self.df.empty or 'brochures' not in self.df.columns:
            return
        unique_brochures = set()
        for b_str in self.df['brochures'].dropna():
            # strip URLs and parentheses
            b_str = re.sub(r'\s*\([^)]*http[^)]*\)', '', str(b_str))
            b_str = re.sub(r'https?://\S+', '', b_str)
            parts = [p.strip() for p in b_str.split(';') if p.strip()]
            unique_brochures.update(parts)
        self.brochure_list.set_items(sorted(list(unique_brochures)))

    def process_brochures(self, text):
        if pd.isna(text): return ""
        text = str(text)
        text = re.sub(r'\s*\([^)]*http[^)]*\)', '', text)
        text = re.sub(r'https?://\S+', '', text)
        # CHANGED: Replaced the regex split with a strict semicolon split
        parts = [p.strip() for p in text.split(';') if p.strip()] 
        return "<br>• ".join([""] + parts) if parts else "" # Formatted as HTML bullets

    def load_default_master(self):
        if os.path.exists(self.default_path):
            with show_loading(self, "Loading Master Database..."):
                try:
                    self.df = pd.read_excel(self.default_path)
                    self.df.columns = [c.lower().strip() for c in self.df.columns]
                    self._update_brochures_list()
                    self.apply_filter()
                except Exception as e:
                    print(f"Could not load master reference: {e}")

    def upload_new_master(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Master File", "", "Excel Files (*.xlsx);;CSV Files (*.csv)")
        if not file_path:
            return

        dlg = MappingDialog(file_path, self.required_fields, allow_extras=True, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            with show_loading(self, "Processing Master File..."):
                try:
                    if file_path.lower().endswith('.csv'):
                        raw_df = pd.read_csv(file_path, header=dlg.header_row)
                    else:
                        raw_df = pd.read_excel(file_path, header=dlg.header_row)
                        
                    inverted_map = {v: k for k, v in dlg.mappings.items()}
                    
                    cols_to_keep = list(dlg.mappings.values()) + getattr(dlg, 'extras', [])
                    self.df = raw_df[cols_to_keep].rename(columns=inverted_map)
                    
                    # Auto-regenerate image paths if missing
                    if 'local_image_path' not in self.df.columns and 'code' in self.df.columns:
                        self.df['local_image_path'] = 'images\\' + self.df['code'].astype(str) + '.png'
                        
                    self.df.to_excel(self.default_path, index=False)
                    self._update_brochures_list()
                    self.apply_filter()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed processing file: {e}")

    def populate_table(self, dataframe):
        self.table.setRowCount(0)
        if dataframe is None or dataframe.empty:
            return
        
        self.table.setRowCount(len(dataframe))
        for ui_row_idx, (orig_idx, row) in enumerate(dataframe.iterrows()):
            code = str(row.get('code', ''))
            desc = str(row.get('description', ''))
            
            # ADD button column
            btn = QPushButton("+")
            btn.setObjectName("addButton")
            btn.setFixedSize(24, 24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(f"Add {code} to offer list")
            btn.clicked.connect(lambda _, c=code, d=desc: self.add_to_offer(c, d))

            btn_container = QWidget()
            btn_container.setObjectName("addButtonCell")
            btn_container.setStyleSheet("QWidget { background: transparent; }")
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            self.table.setRowHeight(ui_row_idx, 36)
            self.table.setCellWidget(ui_row_idx, 0, btn_container)
            
            raw_brochures = str(row.get('brochures', ''))
            brochures_text = re.sub(r'\s*\([^)]*http[^)]*\)', '', raw_brochures)
            brochures_text = re.sub(r'https?://\S+', '', brochures_text).replace(';', '\n')
            
            for c_idx, val in enumerate([code, desc, brochures_text]):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(ui_row_idx, c_idx + 1, item)

            raw_url = str(row.get('product_url', ''))
            if not pd.isna(raw_url) and raw_url.strip().startswith('http'):
                url_label = QLabel(f'<a href="{raw_url}">Open Link</a>')
                url_label.setOpenExternalLinks(True)
                url_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setCellWidget(ui_row_idx, 4, url_label)
            else:
                empty_item = QTableWidgetItem("N/A")
                empty_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(ui_row_idx, 4, empty_item)
        self.table.resizeRowsToContents()
        
        if self.table.rowCount() > 0:
            self.table.selectRow(0)
            self.table.setCurrentCell(0, 0)

    def apply_filter(self):
        if self.df is None or self.df.empty:
            self.stacked_widget.setCurrentIndex(0)
            return

        glob_text = self.txt_global_search.text().lower()
        code_segs = self.code_search.get_segments()
        active_code = any(s != "" for s in code_segs)
        active_cats = self.category_list.get_checked_items()
        active_bros = self.brochure_list.get_checked_items()

        if not glob_text and not active_code and not active_cats and not active_bros:
            self.stacked_widget.setCurrentIndex(0)
            return
            
        self.stacked_widget.setCurrentIndex(1)
        filtered = self.df

        if glob_text:
            or_groups = [g.strip() for g in glob_text.split('//') if g.strip()]
            if or_groups:
                final_mask = pd.Series(False, index=filtered.index)
                for or_group in or_groups:
                    and_terms = [t.strip() for t in or_group.split('&&') if t.strip()]
                    if and_terms:
                        group_mask = pd.Series(True, index=filtered.index)
                        for term in and_terms:
                            term_mask = pd.Series(False, index=filtered.index)
                            for c in filtered.columns:
                                term_mask |= filtered[c].astype(str).str.lower().str.contains(term, regex=False)
                            group_mask &= term_mask
                        final_mask |= group_mask
                filtered = filtered[final_mask]

        if active_code:
            code_col = filtered['code'].astype(str).fillna('')
            split_codes = code_col.str.split('-', expand=True)
            for i, seg in enumerate(code_segs):
                if seg:
                    if i < split_codes.shape[1]:
                        filtered = filtered[split_codes[i].str.startswith(seg, na=False)]
                    else:
                        filtered = filtered.iloc[0:0]

        if active_cats:
            cat_prefixes = [c[:2] for c in active_cats]
            mask = pd.Series(False, index=filtered.index)
            for prefix in cat_prefixes:
                mask |= filtered['code'].astype(str).str.startswith(prefix)
            filtered = filtered[mask]

        if active_bros:
            mask = pd.Series(False, index=filtered.index)
            for bro in active_bros:
                mask |= filtered['brochures'].astype(str).str.contains(bro, case=False, regex=False, na=False)
            filtered = filtered[mask]

        self.populate_table(filtered)

    def open_offer_list(self):
        if not hasattr(self, 'offer_dialog') or not self.offer_dialog.isVisible():
            self.offer_dialog = OfferListDialog(master_tab=self, offer_data=self.offer_data, parent=self)
            self.offer_dialog.show()
        else:
            self.offer_dialog.raise_()
            self.offer_dialog.activateWindow()

    def _add_or_merge_offer_item(self, code, desc, qty):
        clean_code = str(code).replace('-', '').strip().lower()
        for existing in self.offer_data:
            if str(existing["code"]).replace('-', '').strip().lower() == clean_code:
                existing["qty"] += qty
                return
        self.offer_data.append({"code": code, "desc": desc, "qty": qty})

    def add_to_offer(self, code, desc):
        qty, ok = QInputDialog.getInt(self, "Quantity", f"Enter quantity for {code}:", 1, 1, 9999)
        if ok:
            self._add_or_merge_offer_item(code, desc, qty)
            if hasattr(self, 'offer_dialog') and self.offer_dialog.isVisible():
                self.offer_dialog.refresh_offer_table()
            QMessageBox.information(self, "Added", f"Added {qty}x {code} to Offer List.")
