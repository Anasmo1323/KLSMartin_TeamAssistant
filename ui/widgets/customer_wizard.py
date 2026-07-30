import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QFrame,
    QGraphicsDropShadowEffect, QApplication, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QFont

from ui.dialogs.mapping_dialog import MappingDialog

class ActiveItemWidget(QWidget):
    """A floating, semi-transparent widget to show the current item and actions."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Main styled container
        self.container = QFrame(self)
        self.container.setObjectName("WizardContainer")
        self.container.setStyleSheet("""
            QFrame#WizardContainer {
                background-color: rgba(30, 30, 40, 220);
                border-radius: 8px;
                border: 1px solid #444;
            }
            QLabel {
                color: white;
                font-size: 14px;
                background-color: transparent;
                border: none;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.container)
        
        inner_layout = QVBoxLayout(self.container)
        
        top_layout = QHBoxLayout()
        self.lbl_status = QLabel("Customer Wizard: Idle")
        self.lbl_status.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        top_layout.addWidget(self.lbl_status)
        top_layout.addStretch()
        
        self.btn_close_widget = QPushButton("X")
        self.btn_close_widget.setFixedSize(24, 24)
        self.btn_close_widget.setStyleSheet("""
            QPushButton { 
                background-color: #EF4444; 
                color: white; 
                border-radius: 12px; 
                font-weight: bold; 
                font-size: 12px; 
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        self.btn_close_widget.clicked.connect(self.hide)
        top_layout.addWidget(self.btn_close_widget)
        
        inner_layout.addLayout(top_layout)
        
        self.lbl_desc = QLabel("")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("color: #E2E8F0; font-size: 13px;")
        inner_layout.addWidget(self.lbl_desc)
        
        self.lbl_qty = QLabel("")
        self.lbl_qty.setStyleSheet("color: #94A3B8; font-size: 12px;")
        inner_layout.addWidget(self.lbl_qty)
        
        # Actions
        btn_layout = QHBoxLayout()
        
        self.btn_add_header = QPushButton("Add Section Header")
        self.btn_add_header.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2563EB; }
        """)
        
        self.btn_done = QPushButton("Done")
        self.btn_done.setStyleSheet("""
            QPushButton {
                background-color: #10B981; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        
        self.btn_skip = QPushButton("Skip")
        self.btn_skip.setStyleSheet("""
            QPushButton {
                background-color: #EF4444; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        
        btn_layout.addWidget(self.btn_add_header)
        btn_layout.addWidget(self.btn_done)
        btn_layout.addWidget(self.btn_skip)
        
        inner_layout.addLayout(btn_layout)
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)
        
        # Position offset tracking for dragging
        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def update_item(self, index, total, desc, qty):
        self.lbl_status.setText(f"Item {index} of {total}")
        self.lbl_desc.setText(f"Description: {desc}")
        self.lbl_qty.setText(f"Requested Qty: {qty}")

class CustomerWizardPanel(QWidget):
    """The bottom terminal-style panel that holds the loaded customer list."""
    def __init__(self, master_tab, parent=None):
        super().__init__(parent)
        self.master_tab = master_tab
        self.df = None
        self.current_index = -1
        self._initial_offer_len = 0
        self._header_offer_index = None
        
        self.setStyleSheet("""
            CustomerWizardPanel {
                background-color: #F8FAFC;
                border-top: 1px solid #CBD5E1;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.lbl_title = QLabel("Customer Request Wizard")
        self.lbl_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet("border: none; background: transparent;")
        
        self.btn_upload = QPushButton("Upload List (Excel/CSV)")
        self.btn_upload.setStyleSheet("padding: 4px 10px; background-color: white; border: 1px solid #CBD5E1; border-radius: 4px;")
        self.btn_upload.clicked.connect(self.upload_list)
        
        self.btn_expand = QPushButton("↕ Expand")
        self.btn_expand.setStyleSheet("padding: 4px 10px; background-color: white; border: 1px solid #CBD5E1; border-radius: 4px;")
        self.btn_expand.setCheckable(True)
        self.btn_expand.toggled.connect(self.toggle_expand)
        
        self.btn_start = QPushButton("Start Mapping")
        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet("padding: 4px 10px; background-color: white; border: 1px solid #CBD5E1; border-radius: 4px;")
        self.btn_start.clicked.connect(self.start_mapping)
        
        self.btn_close = QPushButton("X")
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; font-weight: bold; color: #64748B; font-size: 16px; }
            QPushButton:hover { color: #EF4444; }
        """)
        
        toolbar.addWidget(self.lbl_title)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_upload)
        toolbar.addWidget(self.btn_expand)
        toolbar.addWidget(self.btn_start)
        toolbar.addWidget(self.btn_close)
        
        layout.addLayout(toolbar)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["No", "Description", "Qty", "Header", "Done", "Skip"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in range(3, 6):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, 60)
        self.table.setStyleSheet("background-color: white;")
        layout.addWidget(self.table)
        
        # Floating window setup
        self.floating_widget = ActiveItemWidget()
        self.floating_widget.btn_add_header.clicked.connect(self.add_section_header)
        self.floating_widget.btn_done.clicked.connect(self.done_item)
        self.floating_widget.btn_skip.clicked.connect(self.skip_item)

    def toggle_expand(self, checked):
        if hasattr(self, 'master_tab') and hasattr(self.master_tab, 'right_splitter'):
            if checked:
                self.btn_expand.setText("Collapse")
                self.master_tab.right_splitter.setSizes([200, 700])
            else:
                self.btn_expand.setText("↕ Expand")
                self.master_tab.right_splitter.setSizes([700, 200])

    def upload_list(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Customer List", "", "Excel/CSV Files (*.xlsx *.xls *.csv)"
        )
        if not file_path:
            return
            
        try:
            mapping_dialog = MappingDialog(file_path, ['desc', 'qty'], allow_extras=False, parent=self)
            
            if mapping_dialog.exec():
                if mapping_dialog.is_excel:
                    raw_df = pd.read_excel(file_path, sheet_name=mapping_dialog.selected_sheet, header=mapping_dialog.header_row)
                else:
                    raw_df = pd.read_csv(file_path, header=mapping_dialog.header_row)

                mapping = mapping_dialog.mappings
                # Invert mapping to map file_column -> our_column
                inverted_map = {v: k for k, v in mapping.items() if v}
                
                cols_to_keep = [v for k, v in mapping.items() if v]
                self.df = raw_df[cols_to_keep].rename(columns=inverted_map)
                
                # Convert to string and clean
                self.df['desc'] = self.df['desc'].astype(str).str.strip()
                if 'qty' in self.df.columns:
                    self.df['qty'] = pd.to_numeric(self.df['qty'], errors='coerce').fillna(1).astype(int)
                else:
                    self.df['qty'] = 1
                    
                # Initialize state columns
                self.df['has_header'] = False
                self.df['is_done'] = False
                self.df['is_skipped'] = False
                
                self.populate_table()
                self.btn_start.setEnabled(True)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

    def populate_table(self):
        if self.df is None:
            return
            
        self.table.setRowCount(0)
        for i, row in self.df.iterrows():
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            
            item_no = QTableWidgetItem(str(i + 1))
            item_desc = QTableWidgetItem(str(row.get('desc', '')))
            item_qty = QTableWidgetItem(str(row.get('qty', '1')))
            
            for item in (item_no, item_desc, item_qty):
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                
            self.table.setItem(row_idx, 0, item_no)
            self.table.setItem(row_idx, 1, item_desc)
            self.table.setItem(row_idx, 2, item_qty)
            
            # Create checkbox widgets
            self._add_checkbox_to_cell(row_idx, 3, "#3B82F6", row.get('has_header', False)) # Blue for Header
            self._add_checkbox_to_cell(row_idx, 4, "#10B981", row.get('is_done', False))    # Green for Done
            self._add_checkbox_to_cell(row_idx, 5, "#EF4444", row.get('is_skipped', False)) # Red for Skip

    def _add_checkbox_to_cell(self, row, col, color, checked):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cb = QCheckBox()
        cb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        cb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        cb.setChecked(checked)
        cb.setStyleSheet(f"""
            QCheckBox::indicator {{ width: 16px; height: 16px; }}
            QCheckBox::indicator:checked {{ background-color: {color}; border: 1px solid {color}; border-radius: 3px; }}
            QCheckBox::indicator:unchecked {{ background-color: white; border: 1px solid #CBD5E1; border-radius: 3px; }}
        """)
        layout.addWidget(cb)
        self.table.setCellWidget(row, col, widget)


    def start_mapping(self):
        if self.df is None or self.df.empty:
            return
            
        if self.current_index < 0:
            self.current_index = 0
            
        self.btn_start.setText("Resume Mapping")
        self.show_floating_widget()
        self.update_active_item()

    def reset_mapping(self):
        if self.df is not None and not self.df.empty:
            self.df['has_header'] = False
            self.df['is_done'] = False
            self.df['is_skipped'] = False
            self.populate_table()
            
            self.floating_widget.hide()
            self.btn_start.setText("Start Mapping")
            self.current_index = -1

    def show_floating_widget(self):
        # Center it on the screen initially
        screen_geometry = QApplication.primaryScreen().geometry()
        x = (screen_geometry.width() - self.floating_widget.width()) // 2
        y = screen_geometry.height() - self.floating_widget.height() - 200
        self.floating_widget.move(x, y)
        self.floating_widget.show()

    def update_active_item(self):
        if self.current_index < 0 or self.current_index >= len(self.df):
            self.floating_widget.hide()
            self.btn_start.setText("Start Mapping")
            self.current_index = -1
            QMessageBox.information(self, "Wizard Complete", "All items have been mapped!")
            return
            
        # Store state to detect if items are added to the offer list during this step
        if hasattr(self.master_tab, 'offer_data'):
            self._initial_offer_len = len(self.master_tab.offer_data)
        else:
            self._initial_offer_len = 0
            
        self._header_offer_index = None
            
        row = self.df.iloc[self.current_index]
        desc = str(row.get('desc', ''))
        qty = str(row.get('qty', '1'))
        
        self.floating_widget.update_item(self.current_index + 1, len(self.df), desc, qty)
        
        # Highlight in table
        self.table.selectRow(self.current_index)
        
        # Auto-search (Idea 3 implementation)
        # Search the first few words of the description to avoid zero results
        words = desc.split()[:2]
        search_term = " ".join(words)
        if hasattr(self.master_tab, 'txt_global_search'):
            self.master_tab.txt_global_search.setText(search_term)
            self.master_tab.queue_filter()
            
        # Reset the add header button state
        self.floating_widget.btn_add_header.setText("Add Section Header")
        self.floating_widget.btn_add_header.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2563EB; }
        """)
        self.floating_widget.btn_add_header.setEnabled(True)

    def add_section_header(self):
        if self.current_index < 0 or self.current_index >= len(self.df):
            return
            
        row = self.df.iloc[self.current_index]
        desc = str(row.get('desc', ''))
        
        # Add a section header to the offer data
        if hasattr(self.master_tab, 'offer_data'):
            self.master_tab.offer_data.append({
                "is_section": True,
                "desc": desc,
                "qty": ""
            })
            
            # Record state
            self.df.at[self.current_index, 'has_header'] = True
            self._header_offer_index = len(self.master_tab.offer_data) - 1
            
            # Update Checkbox
            self._add_checkbox_to_cell(self.current_index, 3, "#3B82F6", True)
            
            if hasattr(self.master_tab, 'save_offer_list'):
                self.master_tab.save_offer_list()
            
            # If the dialog is open, refresh it
            if hasattr(self.master_tab, 'offer_dialog') and self.master_tab.offer_dialog and self.master_tab.offer_dialog.isVisible():
                self.master_tab.offer_dialog.refresh_offer_table()
                self.master_tab.offer_dialog.offer_table.scrollToBottom()
                
        # Visual indication of success
        self.floating_widget.btn_add_header.setText("Header Added ✓")
        self.floating_widget.btn_add_header.setStyleSheet("""
            QPushButton {
                background-color: #94A3B8; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold;
            }
        """)
        self.floating_widget.btn_add_header.setEnabled(False)

    def skip_item(self):
        if self.current_index < 0 or self.current_index >= len(self.df):
            return
            
        # If a header was added but they skipped, delete the header
        if self.df.at[self.current_index, 'has_header'] and self._header_offer_index is not None:
            if hasattr(self.master_tab, 'offer_data') and len(self.master_tab.offer_data) > self._header_offer_index:
                # Remove the header
                del self.master_tab.offer_data[self._header_offer_index]
                self.df.at[self.current_index, 'has_header'] = False
                self._add_checkbox_to_cell(self.current_index, 3, "#3B82F6", False)
                
                if hasattr(self.master_tab, 'save_offer_list'):
                    self.master_tab.save_offer_list()
                    
                if hasattr(self.master_tab, 'offer_dialog') and self.master_tab.offer_dialog and self.master_tab.offer_dialog.isVisible():
                    self.master_tab.offer_dialog.refresh_offer_table()
        
        # Mark as skipped
        self.df.at[self.current_index, 'is_skipped'] = True
        self._add_checkbox_to_cell(self.current_index, 5, "#EF4444", True)
        
        self.current_index += 1
        self.update_active_item()
        
    def done_item(self):
        if self.current_index < 0 or self.current_index >= len(self.df):
            return
            
        if hasattr(self.master_tab, 'offer_data'):
            current_offer_len = len(self.master_tab.offer_data)
            added_items = current_offer_len - self._initial_offer_len
            
            # If the user clicked Add Header, that accounts for 1 item. 
            # Anything more means they added sub-items.
            header_offset = 1 if self.df.at[self.current_index, 'has_header'] else 0
            
            if added_items > header_offset:
                # They added items to the list
                self.df.at[self.current_index, 'is_done'] = True
                self._add_checkbox_to_cell(self.current_index, 4, "#10B981", True)
            else:
                # No items added. (It's just "Header Only" or they did literally nothing)
                self.df.at[self.current_index, 'is_done'] = False
        
        self.current_index += 1
        self.update_active_item()
