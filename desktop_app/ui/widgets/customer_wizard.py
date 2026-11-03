import os
import json
import re
import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QFrame,
    QApplication, QCheckBox, QTreeWidget, QTreeWidgetItem,
    QRadioButton, QButtonGroup, QInputDialog, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from ui.dialogs.mapping_dialog import MappingDialog


class CustomerWizardPanel(QWidget):
    """
    Revamped Set Wizard Panel (docked in left tab):
    - Preserves file order for specialties and set names (no alphabetical sort).
    - No distracting floating window: embedded active-item card right in the panel.
    - Explicit item progression: User CANNOT proceed to the next item unless:
        1. A catalogue item is assigned (via '+' button or Enter key).
        2. OR the user clicks 'No Match Found' which assigns code '99-999-99-99' and desc 'NO BID'.
    - Auto vs Manual Quantity modes:
        * Auto: keeps Qty/Set and Sets from the original file, Total Qty = (Qty/Set * Sets).
        * Manual: prompts for Qty/Set and Sets, Total Qty = (Qty/Set * Sets).
    - Autosaves continuously to local JSON for crash resilience.
    - Exports to {Specialty}_{SetName}.xlsx only when all items are mapped/handled.
    """
    def __init__(self, master_tab, parent=None):
        super().__init__(parent)
        self.master_tab = master_tab
        self.full_df = None            # Complete dataframe
        self.current_specialty = None
        self.current_set_name = None
        self.active_item_idx = -1      # Current item index within active set
        self.is_mapping_active = False

        # Determine autosave path
        base_dir = getattr(self.master_tab, 'base_dir', None)
        if not base_dir:
            import sys
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.autosave_path = os.path.join(base_dir, "customer_wizard_autosave.json")

        self.init_ui()
        self.load_autosaved_state()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)

        # Header toolbar
        top_bar = QHBoxLayout()
        lbl_title = QLabel("🪄 Customer Request Wizard")
        lbl_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        top_bar.addWidget(lbl_title)
        top_bar.addStretch()

        self.btn_upload = QPushButton("📂 Upload Excel")
        self.btn_upload.setToolTip("Upload customer request file (.xlsx)")
        self.btn_upload.setStyleSheet("""
            QPushButton {
                padding: 4px 10px; font-weight: bold; background-color: #2563EB; color: white; border-radius: 4px;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        self.btn_upload.clicked.connect(self.upload_excel)
        top_bar.addWidget(self.btn_upload)
        main_layout.addLayout(top_bar)

        # Quantity mode selection
        qty_box = QFrame()
        qty_box.setStyleSheet("QFrame { background-color: #F1F5F9; border-radius: 4px; padding: 2px; }")
        qty_layout = QHBoxLayout(qty_box)
        qty_layout.setContentsMargins(6, 4, 6, 4)
        qty_label = QLabel("<b>Qty Mode:</b>")
        qty_label.setStyleSheet("color: #334155; font-size: 11px;")
        qty_layout.addWidget(qty_label)

        self.rb_auto_qty = QRadioButton("Auto (File Qty)")
        self.rb_auto_qty.setChecked(True)
        self.rb_auto_qty.setToolTip("Uses Qty/Set and Sets from the original Excel file; Total Qty = (Qty/Set * Sets)")
        self.rb_manual_qty = QRadioButton("Manual Entry")
        self.rb_manual_qty.setToolTip("Prompt for Qty/Set and Sets manually when adding an item; Total Qty = product")

        self.qty_group = QButtonGroup(self)
        self.qty_group.addButton(self.rb_auto_qty)
        self.qty_group.addButton(self.rb_manual_qty)
        qty_layout.addWidget(self.rb_auto_qty)
        qty_layout.addWidget(self.rb_manual_qty)
        qty_layout.addStretch()
        main_layout.addWidget(qty_box)

        # Vertical Splitter between Specialties/Sets Tree and Items Section
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(6)
        self.splitter.setStyleSheet("QSplitter::handle:vertical { background-color: #CBD5E1; margin: 1px; border-radius: 2px; }")

        # Section 1: Specialties & Sets Tree
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(2)

        lbl_tree = QLabel("<b>Specialties & Sets (In File Order):</b>")
        lbl_tree.setStyleSheet("color: #475569; font-size: 11px;")
        tree_layout.addWidget(lbl_tree)

        self.tree_sets = QTreeWidget()
        self.tree_sets.setHeaderHidden(True)
        self.tree_sets.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                background-color: white;
            }
            QTreeWidget::item {
                padding: 3px 2px;
            }
            QTreeWidget::item:selected {
                background-color: #DBEAFE;
                color: #1E3A8A;
                font-weight: bold;
            }
        """)
        self.tree_sets.itemClicked.connect(self.on_set_selected)
        tree_layout.addWidget(self.tree_sets)
        self.splitter.addWidget(tree_container)

        # Section 2: Items To-Do List & Active Item Card
        items_container = QWidget()
        items_layout = QVBoxLayout(items_container)
        items_layout.setContentsMargins(0, 0, 0, 0)
        items_layout.setSpacing(4)

        # Toolbar above table
        items_header = QHBoxLayout()
        self.lbl_current_set = QLabel("Select a Set to begin")
        self.lbl_current_set.setStyleSheet("font-weight: bold; color: #1E293B; font-size: 11px;")
        items_header.addWidget(self.lbl_current_set)
        items_header.addStretch()

        self.btn_start = QPushButton("▶ Start")
        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet("""
            QPushButton {
                padding: 3px 10px; font-weight: bold; background-color: #10B981; color: white; border-radius: 3px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        self.btn_start.clicked.connect(self.toggle_start_resume)
        items_header.addWidget(self.btn_start)

        self.btn_export = QPushButton("💾 Export Excel")
        self.btn_export.setEnabled(False)
        self.btn_export.setToolTip("Export set once all items are completed")
        self.btn_export.setStyleSheet("padding: 3px 8px; font-weight: bold; background-color: #64748B; color: white; border-radius: 3px;")
        self.btn_export.clicked.connect(self.export_set_excel)
        items_header.addWidget(self.btn_export)

        items_layout.addLayout(items_header)

        # Embedded Active Item Card (replaces floating window)
        self.active_card = QFrame()
        self.active_card.setStyleSheet("""
            QFrame#ActiveCard {
                background-color: #1E293B;
                border-radius: 6px;
                border: 1px solid #334155;
            }
        """)
        self.active_card.setObjectName("ActiveCard")
        card_layout = QVBoxLayout(self.active_card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(4)

        card_top = QHBoxLayout()
        self.lbl_active_status = QLabel("Active Item: None")
        self.lbl_active_status.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_active_status.setStyleSheet("color: #60A5FA; background: transparent;")
        card_top.addWidget(self.lbl_active_status)
        card_top.addStretch()

        self.btn_no_match = QPushButton("⚠️ No Match Found (NO BID)")
        self.btn_no_match.setToolTip("Assign special code 99-999-99-99 / NO BID and advance")
        self.btn_no_match.setStyleSheet("""
            QPushButton {
                background-color: #DC2626; color: white; font-weight: bold; font-size: 11px;
                padding: 3px 8px; border-radius: 3px;
            }
            QPushButton:hover { background-color: #B91C1C; }
        """)
        self.btn_no_match.clicked.connect(self.assign_no_match)
        card_top.addWidget(self.btn_no_match)
        card_layout.addLayout(card_top)

        self.lbl_active_desc = QLabel("Click 'Start' to begin matching customer items with the catalogue.")
        self.lbl_active_desc.setWordWrap(True)
        self.lbl_active_desc.setStyleSheet("color: #F8FAFC; font-size: 11px; font-weight: 500; background: transparent;")
        card_layout.addWidget(self.lbl_active_desc)

        card_bottom = QHBoxLayout()
        self.lbl_active_qty = QLabel("")
        self.lbl_active_qty.setStyleSheet("color: #94A3B8; font-size: 11px; background: transparent;")
        card_bottom.addWidget(self.lbl_active_qty)
        card_bottom.addStretch()

        self.lbl_active_matched = QLabel("")
        self.lbl_active_matched.setStyleSheet("color: #34D399; font-size: 11px; font-weight: bold; background: transparent;")
        card_bottom.addWidget(self.lbl_active_matched)
        card_layout.addLayout(card_bottom)

        self.active_card.hide()
        items_layout.addWidget(self.active_card)

        # To-Do Items Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["#", "Description", "Matched KLS Code", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 34)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 70)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                gridline-color: #F1F5F9;
            }
            QTableWidget::item:selected {
                background-color: #EFF6FF;
                color: #1E3A8A;
            }
        """)
        self.table.cellDoubleClicked.connect(self.on_table_row_double_clicked)
        items_layout.addWidget(self.table)

        self.splitter.addWidget(items_container)
        self.splitter.setSizes([160, 360])
        main_layout.addWidget(self.splitter)

    # -------------------------------------------------------------
    # Upload & Parsing
    # -------------------------------------------------------------
    def upload_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Customer Set Request File", "", "Excel Files (*.xlsx *.xls)"
        )
        if not file_path:
            return

        try:
            xl = pd.ExcelFile(file_path)
            sheet_name = xl.sheet_names[0]
            raw_df = pd.read_excel(file_path, sheet_name=sheet_name)

            col_map = {
                'item_id': 'Item ID',
                'specialty': 'Specialty',
                'set_name': 'Set Name',
                'item_num': 'Item #',
                'desc': 'Source Instrument Description / Specification',
                'qty_set': 'Qty / Set',
                'sets': 'Sets',
                'total_qty': 'Total Qty'
            }

            raw_cols_lower = {str(c).strip().lower(): c for c in raw_df.columns}
            missing = []
            matched_mapping = {}

            for key, target_name in col_map.items():
                t_low = target_name.strip().lower()
                if t_low in raw_cols_lower:
                    matched_mapping[key] = raw_cols_lower[t_low]
                else:
                    found = None
                    for c_low, orig in raw_cols_lower.items():
                        if t_low in c_low or c_low in t_low:
                            found = orig
                            break
                    if found:
                        matched_mapping[key] = found
                    else:
                        missing.append(target_name)

            if missing:
                required = list(col_map.values())
                mapping_dialog = MappingDialog(file_path, required, allow_extras=False, parent=self)
                if not mapping_dialog.exec():
                    return
                sheet_name = mapping_dialog.selected_sheet or sheet_name
                raw_df = pd.read_excel(file_path, sheet_name=sheet_name, header=mapping_dialog.header_row)
                inverted = {v: k for k, v in mapping_dialog.mappings.items() if v}
                std_rename = {}
                for file_col, sys_col in inverted.items():
                    for k, v in col_map.items():
                        if v.lower() == sys_col.lower():
                            std_rename[file_col] = k
                self.full_df = raw_df[list(inverted.keys())].rename(columns=std_rename)
            else:
                inverted = {v: k for k, v in matched_mapping.items()}
                self.full_df = raw_df[list(inverted.keys())].rename(columns=inverted)

            self._clean_and_initialize_dataframe()
            self.populate_tree()
            self.save_autosave_state()
            QMessageBox.information(self, "Success", f"Successfully loaded {len(self.full_df)} items in original file order.")

        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to load file: {e}")

    def _clean_and_initialize_dataframe(self):
        if self.full_df is None:
            return

        for col in ['item_id', 'item_num']:
            if col in self.full_df.columns:
                self.full_df[col] = self.full_df[col].fillna('').astype(str).str.strip()
            else:
                self.full_df[col] = ''

        self.full_df['specialty'] = self.full_df['specialty'].fillna('General').astype(str).str.strip()
        self.full_df['set_name'] = self.full_df['set_name'].fillna('Unnamed Set').astype(str).str.strip()
        self.full_df['desc'] = self.full_df['desc'].fillna('').astype(str).str.strip()

        self.full_df['qty_set'] = pd.to_numeric(self.full_df['qty_set'], errors='coerce').fillna(1).astype(int)
        self.full_df['sets'] = pd.to_numeric(self.full_df['sets'], errors='coerce').fillna(1).astype(int)
        self.full_df['total_qty'] = self.full_df['qty_set'] * self.full_df['sets']

        if 'is_done' not in self.full_df.columns:
            self.full_df['is_done'] = False
        if 'kls_code' not in self.full_df.columns:
            self.full_df['kls_code'] = ''
        if 'kls_desc' not in self.full_df.columns:
            self.full_df['kls_desc'] = ''

    # -------------------------------------------------------------
    # Specialties & Sets Tree (FILE ORDER PRESERVED)
    # -------------------------------------------------------------
    def populate_tree(self):
        self.tree_sets.clear()
        if self.full_df is None or self.full_df.empty:
            return

        # Maintain exact file order: use dict.fromkeys on appearance
        specialties_order = list(dict.fromkeys(self.full_df['specialty']))

        for spec in specialties_order:
            spec_item = QTreeWidgetItem(self.tree_sets)
            spec_item.setText(0, f"📁 {spec}")
            spec_item.setFont(0, QFont("Segoe UI", 9, QFont.Weight.Bold))
            spec_item.setFlags(spec_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)

            # Preserve file order for sets within each specialty
            spec_df = self.full_df[self.full_df['specialty'] == spec]
            sets_order = list(dict.fromkeys(spec_df['set_name']))

            for sname in sets_order:
                sub_df = spec_df[spec_df['set_name'] == sname]
                done_count = int(sub_df['is_done'].sum())
                total_count = len(sub_df)
                
                is_complete = (done_count == total_count and total_count > 0)
                status_icon = "✓ " if is_complete else "○ "
                set_item = QTreeWidgetItem(spec_item)
                set_item.setText(0, f"{status_icon}{sname} ({done_count}/{total_count})")
                set_item.setData(0, Qt.ItemDataRole.UserRole, (spec, sname))
                if is_complete:
                    set_item.setForeground(0, QColor("#059669"))

            spec_item.setExpanded(True)

    def on_set_selected(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        spec, sname = data
        self.select_set(spec, sname)

    def select_set(self, spec, sname):
        self.current_specialty = spec
        self.current_set_name = sname
        self.lbl_current_set.setText(f"{spec} → {sname}")
        self.btn_start.setEnabled(True)
        self.btn_start.setText("▶ Start")
        self.is_mapping_active = False
        self.active_item_idx = -1
        self.active_card.hide()
        self.populate_items_table()
        self.check_export_readiness()

    def get_current_set_rows(self):
        if self.full_df is None or not self.current_specialty or not self.current_set_name:
            return pd.DataFrame()
        return self.full_df[
            (self.full_df['specialty'] == self.current_specialty) & 
            (self.full_df['set_name'] == self.current_set_name)
        ]

    # -------------------------------------------------------------
    # To-Do Items Table
    # -------------------------------------------------------------
    def populate_items_table(self):
        self.table.setRowCount(0)
        sub_df = self.get_current_set_rows()
        if sub_df.empty:
            return

        for idx, (real_idx, row) in enumerate(sub_df.iterrows()):
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)

            item_num = str(row.get('item_num', '') or (idx + 1))
            t_num = QTableWidgetItem(item_num)
            t_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            desc = str(row.get('desc', ''))
            t_desc = QTableWidgetItem(desc)
            t_desc.setToolTip(desc)

            matched_code = str(row.get('kls_code', ''))
            t_matched = QTableWidgetItem(matched_code)
            t_matched.setToolTip(str(row.get('kls_desc', '')))

            is_done = bool(row.get('is_done', False))
            t_status = QTableWidgetItem("✓ Done" if is_done else "Pending")
            t_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if is_done:
                if matched_code == "99-999-99-99":
                    t_matched.setForeground(QColor("#DC2626"))
                    t_matched.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                    t_status.setForeground(QColor("#DC2626"))
                else:
                    t_matched.setForeground(QColor("#059669"))
                    t_matched.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                    t_status.setForeground(QColor("#059669"))
            else:
                t_status.setForeground(QColor("#94A3B8"))

            for it in (t_num, t_desc, t_matched, t_status):
                it.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                it.setData(Qt.ItemDataRole.UserRole, real_idx)

            self.table.setItem(row_idx, 0, t_num)
            self.table.setItem(row_idx, 1, t_desc)
            self.table.setItem(row_idx, 2, t_matched)
            self.table.setItem(row_idx, 3, t_status)

        self.check_export_readiness()

    # -------------------------------------------------------------
    # Explicit Matching Workflow
    # -------------------------------------------------------------
    def toggle_start_resume(self):
        sub_df = self.get_current_set_rows()
        if sub_df.empty:
            return

        if not self.is_mapping_active:
            # Find first incomplete item
            first_incomplete = 0
            for i, (_, row) in enumerate(sub_df.iterrows()):
                if not row.get('is_done', False):
                    first_incomplete = i
                    break

            self.active_item_idx = first_incomplete
            self.is_mapping_active = True
            self.btn_start.setText("⏸ Pause")
            self.active_card.show()
            self.update_active_item()
        else:
            # Pause
            self.is_mapping_active = False
            self.btn_start.setText("▶ Resume")
            self.active_card.hide()

    def update_active_item(self):
        sub_df = self.get_current_set_rows()
        if sub_df.empty:
            self.active_card.hide()
            self.is_mapping_active = False
            return

        if self.active_item_idx < 0 or self.active_item_idx >= len(sub_df):
            self.active_card.hide()
            self.is_mapping_active = False
            self.btn_start.setText("▶ Start")
            self.check_export_readiness()
            QMessageBox.information(self, "Set Complete", f"All items in '{self.current_set_name}' are completed!")
            return

        real_idx = sub_df.index[self.active_item_idx]
        row = self.full_df.loc[real_idx]

        desc = str(row.get('desc', ''))
        qty_set = row.get('qty_set', 1)
        sets = row.get('sets', 1)
        tot_qty = row.get('total_qty', qty_set * sets)

        self.lbl_active_status.setText(f"Active Item {self.active_item_idx + 1} of {len(sub_df)}")
        self.lbl_active_desc.setText(desc)
        self.lbl_active_qty.setText(f"Qty/Set: {qty_set} | Sets: {sets} | Total: {tot_qty}")

        matched_code = str(row.get('kls_code', ''))
        if matched_code:
            self.lbl_active_matched.setText(f"Matched: {matched_code}")
        else:
            self.lbl_active_matched.setText("Awaiting catalogue match (+ or Enter)...")

        # Highlight row in wizard table
        self.table.selectRow(self.active_item_idx)

        # Trigger smart search in catalogue
        words = [w for w in re.split(r'\s+', desc) if len(w) > 2][:2]
        search_query = " ".join(words)
        if hasattr(self.master_tab, 'txt_global_search'):
            self.master_tab.txt_global_search.setText(search_query)
            self.master_tab.queue_filter()

    def assign_catalogue_item(self, code, desc):
        """
        Called when user presses Enter or clicks '+' on a catalogue item
        while the set wizard is actively mapping.
        """
        if not self.is_mapping_active:
            return False

        sub_df = self.get_current_set_rows()
        if sub_df.empty or self.active_item_idx < 0 or self.active_item_idx >= len(sub_df):
            return False

        real_idx = sub_df.index[self.active_item_idx]
        
        # Check quantity mode
        if self.rb_manual_qty.isChecked():
            cur_qty_set = int(self.full_df.at[real_idx, 'qty_set'] or 1)
            cur_sets = int(self.full_df.at[real_idx, 'sets'] or 1)

            qs, ok1 = QInputDialog.getInt(self, "Manual Quantity", f"Enter Qty/Set for {code}:", cur_qty_set, 1, 9999)
            if not ok1:
                return False
            s_count, ok2 = QInputDialog.getInt(self, "Manual Sets", f"Enter Number of Sets for {code}:", cur_sets, 1, 9999)
            if not ok2:
                return False

            self.full_df.at[real_idx, 'qty_set'] = qs
            self.full_df.at[real_idx, 'sets'] = s_count
            self.full_df.at[real_idx, 'total_qty'] = qs * s_count
        else:
            qs = int(self.full_df.at[real_idx, 'qty_set'] or 1)
            s_count = int(self.full_df.at[real_idx, 'sets'] or 1)
            self.full_df.at[real_idx, 'total_qty'] = qs * s_count

        # Assign strictly 1-to-1
        self.full_df.at[real_idx, 'kls_code'] = str(code)
        self.full_df.at[real_idx, 'kls_desc'] = str(desc)
        self.full_df.at[real_idx, 'is_done'] = True

        self._update_table_row_ui(self.active_item_idx, str(code), str(desc), is_no_bid=False)
        self.save_autosave_state()
        self.populate_tree()
        self.check_export_readiness()

        # Advance to next item
        self.active_item_idx += 1
        self.update_active_item()
        return True

    def assign_no_match(self):
        """
        User explicitly clicks 'No Match Found':
        Assigns KLS Code '99-999-99-99' and description 'NO BID', marks Done, and advances.
        """
        if not self.is_mapping_active:
            return

        sub_df = self.get_current_set_rows()
        if sub_df.empty or self.active_item_idx < 0 or self.active_item_idx >= len(sub_df):
            return

        real_idx = sub_df.index[self.active_item_idx]

        # Preserve quantities, assign NO BID
        qs = int(self.full_df.at[real_idx, 'qty_set'] or 1)
        s_count = int(self.full_df.at[real_idx, 'sets'] or 1)
        self.full_df.at[real_idx, 'total_qty'] = qs * s_count

        self.full_df.at[real_idx, 'kls_code'] = "99-999-99-99"
        self.full_df.at[real_idx, 'kls_desc'] = "NO BID"
        self.full_df.at[real_idx, 'is_done'] = True

        self._update_table_row_ui(self.active_item_idx, "99-999-99-99", "NO BID", is_no_bid=True)
        self.save_autosave_state()
        self.populate_tree()
        self.check_export_readiness()

        # Advance to next item
        self.active_item_idx += 1
        self.update_active_item()

    def _update_table_row_ui(self, row_idx, code, desc, is_no_bid=False):
        t_matched = self.table.item(row_idx, 2)
        if t_matched:
            t_matched.setText(code)
            t_matched.setToolTip(desc)
            color = "#DC2626" if is_no_bid else "#059669"
            t_matched.setForeground(QColor(color))
            t_matched.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))

        t_status = self.table.item(row_idx, 3)
        if t_status:
            t_status.setText("NO BID" if is_no_bid else "✓ Done")
            color = "#DC2626" if is_no_bid else "#059669"
            t_status.setForeground(QColor(color))

    def on_table_row_double_clicked(self, row, col):
        sub_df = self.get_current_set_rows()
        if sub_df.empty or row < 0 or row >= len(sub_df):
            return

        real_idx = sub_df.index[row]
        item_desc = self.full_df.at[real_idx, 'desc']

        msg = QMessageBox(self)
        msg.setWindowTitle("Item Action")
        msg.setText(f"Item {row + 1}: {item_desc}\nChoose an action:")
        btn_jump = msg.addButton("Set as Active Item", QMessageBox.ButtonRole.ActionRole)
        btn_clear = msg.addButton("Clear Mapping", QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)
        msg.exec()

        if msg.clickedButton() == btn_jump:
            self.active_item_idx = row
            self.is_mapping_active = True
            self.btn_start.setText("⏸ Pause")
            self.active_card.show()
            self.update_active_item()
            self.check_export_readiness()
        elif msg.clickedButton() == btn_clear:
            self.full_df.at[real_idx, 'kls_code'] = ''
            self.full_df.at[real_idx, 'kls_desc'] = ''
            self.full_df.at[real_idx, 'is_done'] = False
            self.populate_items_table()
            self.populate_tree()
            self.save_autosave_state()
            self.check_export_readiness()
            if self.is_mapping_active and self.active_item_idx == row:
                self.update_active_item()

    # -------------------------------------------------------------
    # Export & Completion
    # -------------------------------------------------------------
    def check_export_readiness(self):
        sub_df = self.get_current_set_rows()
        if sub_df.empty:
            self.btn_export.setEnabled(False)
            self.btn_export.setStyleSheet("padding: 3px 8px; font-weight: bold; background-color: #64748B; color: white; border-radius: 3px;")
            return False

        all_finished = bool(sub_df['is_done'].all())
        if all_finished:
            self.btn_export.setEnabled(True)
            self.btn_export.setStyleSheet("""
                QPushButton {
                    padding: 3px 8px; font-weight: bold; background-color: #2563EB; color: white; border-radius: 3px;
                }
                QPushButton:hover { background-color: #1D4ED8; }
            """)
            return True
        else:
            self.btn_export.setEnabled(False)
            self.btn_export.setStyleSheet("padding: 3px 8px; font-weight: bold; background-color: #64748B; color: white; border-radius: 3px;")
            return False

    def export_set_excel(self):
        if not self.check_export_readiness():
            QMessageBox.warning(self, "Set Incomplete", "Please complete all items in the set before exporting.")
            return

        sub_df = self.get_current_set_rows()
        if sub_df.empty:
            return

        export_df = pd.DataFrame()
        export_df['Item ID'] = sub_df['item_id']
        export_df['Specialty'] = sub_df['specialty']
        export_df['Set Name'] = sub_df['set_name']
        export_df['Item #'] = sub_df['item_num']
        export_df['Source Instrument Description / Specification'] = sub_df['desc']
        export_df['Qty / Set'] = sub_df['qty_set']
        export_df['Sets'] = sub_df['sets']
        export_df['Total Qty'] = sub_df['total_qty']
        export_df['KLS CODE'] = sub_df['kls_code']
        export_df['KLS DESCRIPTION'] = sub_df['kls_desc']

        safe_spec = re.sub(r'[^\w\-_]', '_', str(self.current_specialty).strip())
        safe_set = re.sub(r'[^\w\-_]', '_', str(self.current_set_name).strip())
        suggested_name = f"{safe_spec}_{safe_set}.xlsx"
        sheet_name = f"{safe_spec}_{safe_set}"[:31]

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Set Excel", suggested_name, "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                export_df.to_excel(writer, sheet_name=sheet_name, index=False)
            QMessageBox.information(self, "Export Successful", f"Set exported successfully to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to save Excel file: {e}")

    # -------------------------------------------------------------
    # Autosave & Crash Recovery
    # -------------------------------------------------------------
    def save_autosave_state(self):
        if self.full_df is None or self.full_df.empty:
            return
        try:
            state = {
                "current_specialty": self.current_specialty,
                "current_set_name": self.current_set_name,
                "active_item_idx": self.active_item_idx,
                "data": self.full_df.to_dict(orient='records')
            }
            with open(self.autosave_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to autosave wizard state: {e}")

    def load_autosaved_state(self):
        if not os.path.exists(self.autosave_path):
            return
        try:
            with open(self.autosave_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            records = state.get("data", [])
            if records:
                self.full_df = pd.DataFrame(records)
                self._clean_and_initialize_dataframe()
                self.populate_tree()

                spec = state.get("current_specialty")
                sname = state.get("current_set_name")
                if spec and sname:
                    self.select_set(spec, sname)
                    self.active_item_idx = state.get("active_item_idx", -1)
        except Exception as e:
            print(f"Failed to load autosaved wizard state: {e}")
