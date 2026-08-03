import os
import re
import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidgetItem, QHeaderView, QSplitter,
    QStackedWidget, QComboBox, QMessageBox, QFileDialog, QListWidgetItem, QApplication, QInputDialog, QDialog
)
from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QPixmap, QIcon

import math

from core.utils import resource_path, show_loading
from ui.widgets.segmented_edit import SegmentedCodeEdit
from ui.widgets.dynamic_table import DynamicTableWidget
from ui.dialogs.mapping_dialog import MappingDialog
from ui.dialogs.offer_dialog import OfferListDialog
from ui.widgets.customer_wizard import CustomerWizardPanel
from ui.widgets.checkable_list import CheckableListWidget, CheckableTreeWidget
from ui.widgets.collapsible_box import CollapsibleBox
from core.constants import CATEGORY_MAPPING, BROCHURE_HIERARCHY
from PyQt6.QtGui import QPixmap, QColor, QKeySequence

class MultiLineSearchEdit(QLineEdit):
    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Paste):
            text = QApplication.clipboard().text()
            if '\n' in text or '\r' in text:
                clean_text = ' // '.join([line.strip() for line in text.splitlines() if line.strip()])
                self.insert(clean_text)
                return
        super().keyPressEvent(event)

class KlsMasterTab(QWidget):
    def __init__(self):
        super().__init__()
        self.df = None
        self.offer_data = []
        self.default_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "KLS_Product_Families.json")
        self.autosave_path = "offer_list_autosave.json"
        self.required_fields = ['code', 'description', 'brochures', 'state', 'family', 'inventor', 'shape', 'length', 'tip_type', 'modifiers']
        
        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self.apply_filter)
        
        self.init_ui()
        self.load_offer_list()
        QTimer.singleShot(100, self.load_default_master)

    def queue_filter(self):
        self.filter_timer.start(300)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(8)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        left_panel_widget = QWidget()
        left_panel_widget.setMinimumWidth(50)
        left_layout = QVBoxLayout(left_panel_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        
        # Categories Box
        self.cat_box = CollapsibleBox("Categories")
        cat_inner = QVBoxLayout()
        cat_inner.setContentsMargins(4, 4, 4, 4)
        self.category_list = CheckableListWidget(items=list(CATEGORY_MAPPING.values()))
        self.category_list.selectionChanged.connect(self.queue_filter)
        self.category_list.selectionChanged.connect(self._update_cat_highlight)
        cat_inner.addWidget(self.category_list)
        self.cat_box.setContentLayout(cat_inner)
        left_layout.addWidget(self.cat_box)
        
        # Brochures Box
        self.bro_box = CollapsibleBox("Brochures")
        bro_inner = QVBoxLayout()
        bro_inner.setContentsMargins(4, 4, 4, 4)
        self.brochure_list = CheckableTreeWidget(hierarchy=BROCHURE_HIERARCHY)
        self.brochure_list.selectionChanged.connect(self.queue_filter)
        self.brochure_list.selectionChanged.connect(self._update_bro_highlight)
        bro_inner.addWidget(self.brochure_list)
        self.bro_box.setContentLayout(bro_inner)
        left_layout.addWidget(self.bro_box)

        # Sets Box
        self.set_box = CollapsibleBox("Instrument Sets")
        set_inner = QVBoxLayout()
        set_inner.setContentsMargins(4, 4, 4, 4)
        self.sets_list = CheckableListWidget(items=[])
        self.sets_list.selectionChanged.connect(self.queue_filter)
        self.sets_list.selectionChanged.connect(self._update_set_highlight)
        set_inner.addWidget(self.sets_list)
        self.set_box.setContentLayout(set_inner)
        left_layout.addWidget(self.set_box)
        
        left_layout.addStretch()
        main_splitter.addWidget(left_panel_widget)

        # Right Panel (Search & Content)
        right_widget = QWidget()
        right_panel = QVBoxLayout(right_widget)
        right_panel.setContentsMargins(0, 0, 0, 0)
        
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        
        self.txt_global_search = MultiLineSearchEdit()
        self.txt_global_search.setPlaceholderText("Global Search...")
        self.txt_global_search.setMinimumWidth(150)
        self.txt_global_search.setMaximumWidth(300)
        self.txt_global_search.returnPressed.connect(self.queue_filter)
        search_layout.addWidget(self.txt_global_search)
        
        self.state_filter = QComboBox()
        self.state_filter.addItems(["All", "Active", "Inactive"])
        self.state_filter.currentIndexChanged.connect(self.queue_filter)
        search_layout.addWidget(self.state_filter)

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
        
        self.btn_wizard = QPushButton("🪄")
        self.btn_wizard.setToolTip("Customer Request Wizard")
        self.btn_wizard.setMinimumWidth(50)
        self.btn_wizard.setMaximumWidth(80)
        self.btn_wizard.clicked.connect(self.toggle_customer_wizard)
        search_layout.addWidget(self.btn_wizard)
        
        search_layout.addStretch()
        right_panel.addLayout(search_layout)
        # Right Splitter (Table top, Wizard bottom)
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.setHandleWidth(8)
        self.right_splitter.setStyleSheet("QSplitter::handle:vertical { background-color: #E2E8F0; margin: 2px; border-radius: 2px; }")
        
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
        headers = ["#", "Code", "Description", "Shape", "Dimensions", "Length", "Tip", "Modifiers", "Brochures", "State"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(120)
        self.table.setColumnWidth(0, 54)
        self.table.setColumnWidth(2, 350)
        self.table.installEventFilter(self)
        
        self.stacked_widget.addWidget(self.table)
        self.stacked_widget.setCurrentWidget(self.placeholder_label)

        self.right_splitter.addWidget(self.stacked_widget)
        
        self.wizard_panel = CustomerWizardPanel(self)
        self.wizard_panel.hide()
        self.wizard_panel.btn_close.clicked.connect(lambda: self.wizard_panel.hide())
        self.right_splitter.addWidget(self.wizard_panel)
        
        right_panel.addWidget(self.right_splitter)
        main_splitter.addWidget(right_widget)
        
        # Set standard initial ratios for Master Tab
        main_splitter.setSizes([300, 900])
        self.right_splitter.setSizes([700, 200])

    def toggle_customer_wizard(self):
        if self.wizard_panel.isVisible():
            self.wizard_panel.hide()
        else:
            self.wizard_panel.show()

    def eventFilter(self, source, event):
        if source == self.table and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                selected_rows = sorted(list(set(item.row() for item in self.table.selectedItems())))
                if not selected_rows:
                    current_row = self.table.currentRow()
                    if current_row >= 0:
                        selected_rows = [current_row]
                
                is_multi = len(selected_rows) > 1
                for row in selected_rows:
                    code_item = self.table.item(row, 1)
                    desc_item = self.table.item(row, 2)
                    if code_item and desc_item:
                        # Skip family header rows which don't have descriptions
                        if desc_item.text().strip():
                            self.add_to_offer(code_item.text(), desc_item.text(), skip_prompt=is_multi)
                
                if is_multi:
                    QMessageBox.information(self, "Added", f"Added {len(selected_rows)} items to Offer List.")
                return True
        return super().eventFilter(source, event)

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

    def _format_brochures(self, text):
        if pd.isna(text): return ""
        text = str(text)
        text = re.sub(r'\s*\([^)]*http[^)]*\)', '', text)
        text = re.sub(r'https?://\S+', '', text)
        parts = [p.strip() for p in text.split(';') if p.strip()] 
        return "\n• ".join([""] + parts) if parts else ""

    def _update_cat_highlight(self):
        self.cat_box.set_highlight(bool(self.category_list.get_checked_items()))
        
    def _update_bro_highlight(self):
        self.bro_box.set_highlight(bool(self.brochure_list.get_checked_items()))
        
    def _update_set_highlight(self):
        self.set_box.set_highlight(bool(self.sets_list.get_checked_items()))

    def load_default_master(self):
        if os.path.exists(self.default_path):
            with show_loading(self, "Loading Master Database..."):
                try:
                    import json
                    if self.default_path.endswith('.json'):
                        with open(self.default_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        flat_data = []
                        for family, f_data in data.items():
                            schema = f_data.get("schema")
                            for item in f_data.get("items", []):
                                item["family"] = family
                                item["schema"] = schema
                                flat_data.append(item)
                        self.df = pd.DataFrame(flat_data)
                        if 'code' in self.df.columns:
                            self.df['local_image_path'] = 'images\\' + self.df['code'].astype(str) + '.png'
                    else:
                        self.df = pd.read_excel(self.default_path)
                        self.df.columns = [c.lower().strip() for c in self.df.columns]
                        
                    self._update_brochures_list()
                    
                    # Load Sets
                    self.sets_df = None
                    self.set_skus_map = {}
                    if os.path.exists("ALMA_Sets_Export.xlsx"):
                        self.sets_df = pd.read_excel("ALMA_Sets_Export.xlsx")
                        unique_sets = self.sets_df['Set_Name'].dropna().unique().tolist()
                        self.sets_list.list_widget.clear()
                        for s in sorted(unique_sets):
                            item = QListWidgetItem(str(s))
                            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                            item.setCheckState(Qt.CheckState.Unchecked)
                            self.sets_list.list_widget.addItem(item)
                            
                        # Pre-build sku map
                        for s in unique_sets:
                            skus = self.sets_df[self.sets_df['Set_Name'] == s]['Item_SKU'].dropna().astype(str).str.replace('-', '').str.lower().tolist()
                            self.set_skus_map[s] = skus
                            
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
                        
                    self.df.to_excel(self.default_path.replace('.json', '.xlsx'), index=False)
                    self._update_brochures_list()
                    self.apply_filter()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed processing file: {e}")

    def populate_table(self, dataframe):
        self.table.setRowCount(0)
        if dataframe is None or dataframe.empty:
            return
            
        # Group by family
        dataframe = dataframe.copy()
        dataframe['family'] = dataframe['family'].fillna('(Unclassified)')
        grouped = dataframe.groupby('family')
        
        # Calculate total rows needed (headers + items)
        total_rows = len(dataframe) + len(grouped)
        self.table.setRowCount(total_rows)
        
        ui_row_idx = 0
        for family, group_df in sorted(grouped, key=lambda g: g[0]):
            # Insert Family Header Row
            header_item = QTableWidgetItem(f"   {family} ({len(group_df)} variations)")
            header_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            header_item.setBackground(QColor("#E2E8F0"))
            header_item.setForeground(QColor("#282829"))
            font = header_item.font()
            font.setBold(True)
            font.setPointSize(11)
            header_item.setFont(font)
            
            self.table.setItem(ui_row_idx, 0, header_item)
            self.table.setSpan(ui_row_idx, 0, 1, self.table.columnCount())
            self.table.setRowHeight(ui_row_idx, 30)
            ui_row_idx += 1
            
            # Insert Variations
            for orig_idx, row in group_df.iterrows():
                code = str(row.get('code', ''))
                desc = str(row.get('description', ''))
                shape = str(row.get('shape', '')) if pd.notna(row.get('shape')) else ""
                dimensions = str(row.get('dimensions', '')) if pd.notna(row.get('dimensions')) else ""
                length = str(row.get('length', '')) if pd.notna(row.get('length')) else ""
                tip = str(row.get('tip_type', '')) if pd.notna(row.get('tip_type')) else ""
                modifiers = str(row.get('modifiers', '')) if pd.notna(row.get('modifiers')) else ""
                state_val = str(row.get('state', 'Active'))
                brochures_text = self._format_brochures(str(row.get('brochures', '')))
                
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
                
                col_data = [code, desc, shape, dimensions, length, tip, modifiers, brochures_text, state_val]
                for c_idx, val in enumerate(col_data):
                    item = QTableWidgetItem(val)
                    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                    
                    if c_idx == len(col_data) - 1: # State column
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        if val.lower() == 'active':
                            item.setForeground(QColor("green"))
                        elif val.lower() == 'inactive':
                            item.setForeground(QColor("red"))
                            
                    self.table.setItem(ui_row_idx, c_idx + 1, item)
                    
                ui_row_idx += 1
                
        self.table.resizeRowsToContents()
        
        if self.table.rowCount() > 0:
            # Select first real row, not the header
            self.table.selectRow(1)
            self.table.setCurrentCell(1, 0)

    def apply_filter(self):
        if self.df is None or self.df.empty:
            self.stacked_widget.setCurrentIndex(0)
            return

        glob_text = self.txt_global_search.text().lower()
        code_segs = self.code_search.get_segments()
        active_code = any(s != "" for s in code_segs)
        active_cats = self.category_list.get_checked_items()
        active_bros = self.brochure_list.get_checked_items()
        active_sets = self.sets_list.get_checked_items()
        state_val = self.state_filter.currentText()

        if not glob_text and not active_code and not active_cats and not active_bros and not active_sets and state_val == "All":
            self.stacked_widget.setCurrentIndex(0)
            return
            
        self.stacked_widget.setCurrentIndex(1)
        filtered = self.df
        
        if state_val != "All":
            filtered = filtered[filtered['state'].astype(str).str.strip().str.lower() == state_val.lower()]

        if active_sets and hasattr(self, 'set_skus_map'):
            valid_skus = set()
            for s in active_sets:
                valid_skus.update(self.set_skus_map.get(s, []))
            filtered = filtered[filtered['code'].astype(str).str.replace('-', '').str.lower().isin(valid_skus)]

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
        for existing in reversed(self.offer_data):
            if existing.get("is_section", False):
                break
            if str(existing.get("code", "")).replace('-', '').strip().lower() == clean_code:
                existing["qty"] += qty
                self.save_offer_list()
                return
        # Check if insert_mode_index is set from the customer wizard
        insert_idx = getattr(self, 'insert_mode_index', None)
        
        if insert_idx is not None:
            self.offer_data.insert(insert_idx, {"code": code, "desc": desc, "qty": qty})
            self.insert_mode_index += 1
        else:
            self.offer_data.append({"code": code, "desc": desc, "qty": qty})
            
        self.save_offer_list()

    def add_to_offer(self, code, desc, skip_prompt=False, default_qty=1):
        if skip_prompt:
            qty, ok = default_qty, True
        else:
            qty, ok = QInputDialog.getInt(self, "Quantity", f"Enter quantity for {code}:", 1, 1, 9999)
            
        if ok:
            self._add_or_merge_offer_item(code, desc, qty)
            if hasattr(self, 'offer_dialog') and self.offer_dialog.isVisible():
                self.offer_dialog.refresh_offer_table()
            
            if not skip_prompt:
                QMessageBox.information(self, "Added", f"Added {qty}x {code} to Offer List.")

    def load_offer_list(self):
        import json
        if os.path.exists(self.autosave_path):
            try:
                with open(self.autosave_path, 'r', encoding='utf-8') as f:
                    self.offer_data = json.load(f)
            except Exception as e:
                print(f"Failed to load autosaved offer list: {e}")
                self.offer_data = []

    def save_offer_list(self):
        import json
        try:
            with open(self.autosave_path, 'w', encoding='utf-8') as f:
                json.dump(self.offer_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to autosave offer list: {e}")
